"""Minimal HTML helpers still used outside the removed template backend."""

from html import entities
from html.parser import HTMLParser


class stripHtml(HTMLParser):
    """Remove markup while keeping character/entity text content."""

    def __init__(self, data):
        super().__init__(convert_charrefs=False)
        self.result = []
        if isinstance(data, str):
            self.feed(data)
        else:
            self.feed(data.decode('utf-8'))
        self.close()

    def __str__(self):
        return ''.join(self.result)

    def handle_entityref(self, ref):
        if ref in entities.entitydefs:
            value = entities.entitydefs[ref]
            if len(value) == 1:
                self.result.append(chr(ord(value)))
            elif value.startswith('&#') and value.endswith(';'):
                self.handle_charref(value[2:-1])
            else:
                self.result.append('&%s;' % ref)
        else:
            self.result.append('&%s;' % ref)

    def handle_charref(self, ref):
        try:
            if ref.startswith('x'):
                self.result.append(chr(int(ref[1:], 16)))
            else:
                self.result.append(chr(int(ref)))
        except Exception:
            self.result.append('&#%s;' % ref)

    def handle_data(self, data):
        if data:
            self.result.append(data)
