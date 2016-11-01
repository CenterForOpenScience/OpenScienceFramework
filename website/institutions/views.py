import httplib as http

from .model import Institution
from framework.exceptions import HTTPError

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from website.project.tasks import institution_dashboard_display


def view_institution(inst_id, **kwargs):
    try:
        inst = Institution.find_one(Q('_id', 'eq', inst_id) & Q('is_deleted', 'ne', True))
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)

    if not inst.dashboard_display:
        institution_dashboard_display(inst)

    return {
        'id': inst._id,
        'name': inst.name,
        'logo_path': inst.logo_path,
        'logo_path_rounded_corners': inst.logo_path_rounded_corners,
        'description': inst.description or '',
        'banner_path': inst.banner_path
    }
