import logging
from modularodm import Q

from website.settings import ADDONS_AVAILABLE
from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_events():
    counts = []
    addons_available = {k: v for k, v in [(addon.short_name, addon) for addon in ADDONS_AVAILABLE]}
    for short_name, addon in addons_available.iteritems():
        user_count = addon.settings_models['user'].find().count() if addon.settings_models.get('user') else 0
        node_count = addon.settings_models['node'].find().count() if addon.settings_models.get('node') else 0
        deleted_count = addon.settings_models['node'].find(Q('deleted', 'eq', True)).count() if addon.settings_models.get('node') else 0
        disconnected_count = addon.settings_models['node'].find(Q('external_account', 'eq', None) & Q('deleted', 'ne', True)).count() if addon.settings_models.get('node') else 0

        counts.append({
            'provider': {
                'name': short_name
            },
            'users': {
                'total': user_count
            },
            'nodes': {
                'total': node_count,
                'connected': node_count,
                'deleted': deleted_count,
                'disconnected': disconnected_count
            }
        })

        logger.info('{} counted. Users: {}, Nodes: {}'.format(addon.short_name, user_count, node_count))

    return counts

def main():
    addon_count = get_events()
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_event('addon_count_analytics', addon_count)
    else:
        print(addon_count)


if __name__ == '__main__':
    init_app()
    main()
