from glob import glob
import os, sys

if __name__ == '__main__':
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, rootdir)

from planet.spider import filename
from planet import config

class TextDbm:
    """Small text facade over Python 3 dbm byte stores."""

    def __init__(self, db):
        self.db = db

    def __len__(self):
        return len(self.db)

    def __getitem__(self, key):
        value = self.db[self._key(key)]
        return value.decode('utf-8')

    def __setitem__(self, key, value):
        self.db[self._key(key)] = self._value(value)

    def __contains__(self, key):
        return self._key(key) in self.db

    def keys(self):
        return [key.decode('utf-8') for key in self.db.keys()]

    def close(self):
        self.db.close()

    def _key(self, key):
        return key.encode('utf-8') if isinstance(key, str) else key

    def _value(self, value):
        return value.encode('utf-8') if isinstance(value, str) else value

def _open_db(path, flag):
    """Open the id index with the best available stdlib dbm backend."""
    import dbm.dumb
    return TextDbm(dbm.dumb.open(path, flag))

def open():
    try:
        cache = config.cache_directory()
        index=os.path.join(cache,'index')
        if not os.path.exists(index): return None
        return _open_db(filename(index, 'id'),'w')
    except Exception as e:
        if e.__class__.__name__ == 'DBError': e = e.args[-1]
        from planet import logger as log
        log.error(str(e))

def destroy():
    from planet import logger as log
    cache = config.cache_directory()
    index=os.path.join(cache,'index')
    if not os.path.exists(index): return None
    idindex = filename(index, 'id')
    for file in glob(idindex + '*'):
        os.unlink(file)
    os.removedirs(index)
    log.info(idindex + " deleted")

def create():
    from planet import logger as log
    cache = config.cache_directory()
    index=os.path.join(cache,'index')
    if not os.path.exists(index): os.makedirs(index)
    index = _open_db(filename(index, 'id'),'c')

    try:
        import libxml2
    except:
        libxml2 = False
        from xml.dom import minidom

    for file in glob(cache+"/*"):
        if os.path.isdir(file):
            continue
        elif libxml2:
            try:
                doc = libxml2.parseFile(file)
                ctxt = doc.xpathNewContext()
                ctxt.xpathRegisterNs('atom','http://www.w3.org/2005/Atom')
                entry = ctxt.xpathEval('/atom:entry/atom:id')
                source = ctxt.xpathEval('/atom:entry/atom:source/atom:id')
                if entry and source:
                    index[filename('',entry[0].content)] = source[0].content
                doc.freeDoc()
            except:
                log.error(file)
        else:
            try:
                doc = minidom.parse(file)
                doc.normalize()
                ids = doc.getElementsByTagName('id')
                entry = [e for e in ids if e.parentNode.nodeName == 'entry']
                source = [e for e in ids if e.parentNode.nodeName == 'source']
                if entry and source:
                    index[filename('',entry[0].childNodes[0].nodeValue)] = \
                        source[0].childNodes[0].nodeValue
                doc.freeDoc()
            except:
                log.error(file)

    log.info(str(len(index.keys())) + " entries indexed")
    index.close()

    return open()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s [-c|-d]' % sys.argv[0])
        sys.exit(1)

    config.load(sys.argv[1])

    if len(sys.argv) > 2 and sys.argv[2] == '-c':
        create()
    elif len(sys.argv) > 2 and sys.argv[2] == '-d':
        destroy()
    else:
        from planet import logger as log
        index = open()
        if index:
            log.info(str(len(index.keys())) + " entries indexed")
            index.close()
        else:
            log.info("no entries indexed")
