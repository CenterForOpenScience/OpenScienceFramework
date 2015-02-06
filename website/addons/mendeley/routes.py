from framework.routing import Rule, json_renderer

from website.addons.mendeley import views

api_routes = {
    'rules': [
        Rule(
            [
                '/settings/mendeley/accounts/',
            ],
            'get',
            views.list_mendeley_accounts_user,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/mendeley/accounts/',
                '/project/<pid>/node/<nid>/mendeley/accounts/',
            ],
            'get',
            views.list_mendeley_accounts_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/mendeley/<account_id>/lists/',
                '/project/<pid>/node/<nid>/mendeley/<account_id>/lists/',
            ],
            'get',
            views.list_citationlists_node,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/mendeley/settings/',
                '/project/<pid>/node/<nid>/mendeley/settings/',
            ],
            'post',
            views.mendeley_set_config,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/mendeley/widget/',
                '/project/<pid>/node/<nid>/mendeley/widget/',
            ],
            'get',
            views.mendeley_widget,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/mendeley/citations/',
                '/project/<pid>/node/<nid>/mendeley/citations/',
            ],
            'get',
            views.mendeley_citation_list,
            json_renderer,

        ),

    ],
    'prefix': '/api/v1'
}