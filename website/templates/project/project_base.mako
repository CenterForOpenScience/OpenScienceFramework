<%inherit file="../base.mako"/>

<%def name="og_description()">

    %if node['description']:
        ${sanitize.strip_html(node['description']) + ' | '}
    %endif
    Hosted on the Open Science Framework


</%def>

<%def name="content()">

<%include file="project_header.mako"/>

<%include file="modal_show_links.mako"/>

% if node['is_retracted'] == True:
    <%include file="retracted_registration.mako" args="node='${node}'"/>
% else:
    ${next.body()}
##  % if node['node_type'] == 'project':
        <%include file="modal_duplicate.mako"/>
##  % endif
% endif

</%def>

<%def name="javascript_bottom()">

<script src="/static/vendor/citeproc-js/xmldom.js"></script>
<script src="/static/vendor/citeproc-js/citeproc.js"></script>

<script>

    ## TODO: Move this logic into badges add-on
    % if 'badges' in addons_enabled and badges and badges['can_award']:
    ## TODO: port to commonjs
    ## $script(['/static/addons/badges/badge-awarder.js'], function() {
    ##     attachDropDown('${'{}badges/json/'.format(user_api_url)}');
    ## });
    % endif

    var nodeId = ${ node['id'] |sjson, n };
    var userApiUrl = ${ user_api_url | sjson, n };
    var nodeApiUrl = ${ node['api_url'] | sjson, n };
    var absoluteUrl = ${ node['display_absolute_url'] | sjson, n };
    <%
       parent_exists = parent_node['exists']
       parent_title = ''
       parent_registration_url = ''
       if parent_exists:
           parent_title = "Private {0}".format(parent_node['category'])
           parent_registration_url = ''
       if parent_node['can_view'] or parent_node['is_contributor']:
           parent_title = parent_node['title']
           parent_registration_url = parent_node['registrations_url']
    %>

    // Mako variables accessible globally
    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            ## TODO: Abstract me
            username: ${ user['username'] | sjson, n },
            id: ${ user_id | sjson, n },
            urls: {api: userApiUrl},
            isContributor: ${ user.get('is_contributor', False) | sjson, n },
            fullname: ${ user['fullname'] | sjson, n }
        },
        node: {
            ## TODO: Abstract me
            id: nodeId,
            title: ${ node['title'] | sjson, n },
            urls: {
                api: nodeApiUrl,
                web: ${ node['url'] | sjson, n },
                update: ${ node['update_url'] | sjson, n }
            },
            isPublic: ${json.dumps(node.get('is_public', False))},
            isRetracted: ${json.dumps(node.get('is_retracted', False))},
            piwikSiteID: ${json.dumps(node.get('piwik_site_id', None))},
            piwikHost: ${json.dumps(piwik_host)},
            anonymous: ${json.dumps(node['anonymous'])},
            category: '${node['category_short']}',
            parentTitle: ${json.dumps(parent_title) | n},
            parentRegisterUrl: '${parent_registration_url}',
            parentExists: ${json.dumps(parent_exists)},
            registrationMetaSchema: ${json.dumps(node['registered_schema'])},
            registrationMetaData: ${json.dumps(node['registered_meta'])}
        }
    });

</script>
<script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']], processEscapes: true},
        // Don't automatically typeset the whole page. Must explicitly use MathJax.Hub.Typeset
        skipStartupTypeset: true
    });
</script>
<script type="text/javascript"
    src="/static/vendor/bower_components/MathJax/unpacked/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>


<script src=${"/static/public/js/project-base-page.js" | webpack_asset}> </script>
</%def>
