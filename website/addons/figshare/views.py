"""

"""

from framework import request
from website.project import decorators

from . import settings as figshare_settings


@decorators.must_be_contributor
@decorators.must_have_addon('figshare', 'node')
def figshare_set_config(*args, **kwargs):
    figshare = kwargs['node_addon']
    figshare.figshare_id = request.json.get('figshare_id', '')
    figshare.save()


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
def figshare_widget(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')

    rv = {
        'complete': True,
        'figshare_id': figshare.figshare_id,
        'src': figshare.embed_url,
        'width': figshare_settings.IFRAME_WIDTH,
        'height': figshare_settings.IFRAME_HEIGHT,
    }
    rv.update(figshare.config.to_json())
    return rv
