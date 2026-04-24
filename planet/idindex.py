from glob import glob
import os
import sys
from xml.dom import minidom

if __name__ == "__main__":
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, rootdir)

from planet import config
from planet import storage
from planet.spider import filename


def _node_text(node):
    """Return concatenated node text content."""
    return "".join(child.nodeValue for child in node.childNodes if child.nodeValue)


def _extract_entry_and_source_id(path):
    """Read a cached entry file and return `(entry_id, source_id)`."""
    doc = minidom.parse(path)
    doc.normalize()
    entry_id = None
    source_id = None

    for node in doc.getElementsByTagName("id"):
        parent = getattr(node.parentNode, "localName", None) or node.parentNode.nodeName
        if parent == "entry" and not entry_id:
            entry_id = _node_text(node)
        elif parent == "source" and not source_id:
            source_id = _node_text(node)
        if entry_id and source_id:
            break

    doc.unlink()
    return entry_id, source_id


def open():
    """Open the id index if it has already been initialized."""
    try:
        return storage.open_id_index(create=False)
    except Exception as error:
        from planet import logger as log

        log.error(str(error))
        return None


def destroy():
    """Remove id-index rows while keeping the shared cache database."""
    from planet import logger as log

    storage.clear_id_index()
    log.info("id index deleted")


def create():
    """Create (or rebuild) the id index by scanning cached entry files."""
    from planet import logger as log

    index = storage.open_id_index(create=True)
    index.clear()
    cache = config.cache_directory()

    for path in glob(cache + "/*"):
        if os.path.isdir(path):
            continue
        try:
            entry_id, source_id = _extract_entry_and_source_id(path)
            if entry_id and source_id:
                index[filename("", entry_id)] = source_id
        except Exception:
            log.error(path)

    log.info(str(len(index.keys())) + " entries indexed")
    index.close()
    return open()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s [-c|-d]" % sys.argv[0])
        sys.exit(1)

    config.load(sys.argv[1])

    if len(sys.argv) > 2 and sys.argv[2] == "-c":
        create()
    elif len(sys.argv) > 2 and sys.argv[2] == "-d":
        destroy()
    else:
        from planet import logger as log

        index = open()
        if index:
            log.info(str(len(index.keys())) + " entries indexed")
            index.close()
        else:
            log.info("no entries indexed")
