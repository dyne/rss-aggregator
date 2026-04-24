import os.path
import urllib.parse
import datetime

from . import tmpl
from planet import config

def DjangoPlanetDate(value):
    return datetime.datetime(*value[:6])

# remap PlanetDate to be a datetime, so Django template authors can use 
# the "date" filter on these values
tmpl.PlanetDate = DjangoPlanetDate

def run(script, doc, output_file=None, options={}):
    """process a Django template file"""
    from django.template import Context, Engine

    # set up the Django context by using the default htmltmpl 
    # datatype converters
    context = Context(autoescape=(config.django_autoescape()=='on'))
    context.update(tmpl.template_info(doc))
    context['Config'] = config.planet_options()
    engine = Engine(dirs=[os.path.dirname(script)])
    t = engine.get_template(os.path.basename(script))

    if output_file:
        reluri = os.path.splitext(os.path.basename(output_file))[0]
        context['url'] = urllib.parse.urljoin(config.link(),reluri)
        f = open(output_file, 'w', encoding='utf-8')
        f.write(t.render(context))
        f.close()
    else:
        # @@this is useful for testing purposes, but does it 
        # belong here?
        return t.render(context)
