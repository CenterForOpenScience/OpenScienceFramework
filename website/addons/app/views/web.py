from website.project.views.node import _view_project
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)

@must_be_contributor_or_public
@must_have_addon('app', 'node')
def application_page(auth, node_addon, **kwargs):
    node = kwargs.get('node') or kwargs['project']
    rv = _view_project(node, auth)
    return rv
