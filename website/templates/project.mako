<%inherit file="base.mako"/>

<%def name="title()">Project</%def>

<%def name="content()">

    <div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

    <div class="row">

        <div class="col-md-7" id="containment">

            <%
                extra_addon_widgets = [
                    addon_name
                    for addon_name, addon_config in addons.iteritems()
                    if addon_name not in ['wiki', 'files']
                        and addon_config['has_widget']
                ]
            %>

            % if extra_addon_widgets:

                <!-- Show widgets in left column if present -->
                % for addon in addons_enabled:
                    % if addons[addon]['has_widget']:
                        <div class="addon-widget-container" mod-meta='{
                                "tpl": "../addons/${addon}/templates/${addon}_widget.mako",
                                "uri": "${node['api_url']}${addon}/widget/",
                                "kwargs": {
                                    "name": "${addons[addon]['short_name']}",
                                    "title": "${addons[addon]['full_name']}",
                                    "page": "${addons[addon]['has_page']}",
                                    "help": "${addons[addon]['help']}"
                                }
                            }'></div>
                    % endif
                % endfor

            % else:

                % if 'wiki' in addons and addons['wiki']['has_widget']:
                    <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/wiki/templates/wiki_widget.mako",
                            "uri": "${node['api_url']}wiki/widget/",
                            "kwargs": {
                                "name": "${addons['wiki']['short_name']}",
                                "title": "${addons['wiki']['full_name']}",
                                "page": "${addons['wiki']['has_page']}",
                                "help": "${addons['wiki']['help']}"
                            }
                        }'></div>
                % endif

                <!-- If no widgets, show components -->
                ${children()}

                % if 'files' in addons and addons['files']['has_widget']:
                    <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/files/templates/files_widget.mako",
                            "uri": "${node['api_url']}files/widget/",
                            "kwargs": {
                                "name": "${addons['files']['short_name']}",
                                "title": "${addons['files']['full_name']}",
                                "page": "${addons['files']['has_page']}",
                                "help": "${addons['files']['help']}"
                            }
                        }'></div>
                % endif

            % endif

        </div>

        <div class="col-md-5">

            <!-- Citations -->
            <div class="citations">
                <span class="citation-label">Citation:</span>
                <span>${node['display_absolute_url']}</span>
                <a href="#" class="citation-toggle" style="padding-left: 10px;">more</a>
                <dl class="citation-list">
                    <dt>APA</dt>
                        <dd class="citation-text">${node['citations']['apa']}</dd>
                    <dt>MLA</dt>
                        <dd class="citation-text">${node['citations']['mla']}</dd>
                    <dt>Chicago</dt>
                        <dd class="citation-text">${node['citations']['chicago']}</dd>
                </dl>
            </div>

            <hr />

            <!-- Show child on right if widgets -->
            % if extra_addon_widgets:
                ${children()}
            % endif

            <div class="tags">
                <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node['tags']]) if node['tags'] else ''}" />
            </div>

            <hr />

            <div class="logs">
                <div id='logScope'>
                    <%include file="log_list.mako"/>
                </div><!-- end #logScope -->
                ## Hide More widget until paging for logs is implemented
                ##<div class="paginate pull-right">more</div>
            </div>

        </div>

      </div>


##<!-- Include Knockout and view model -->
##<div mod-meta='{
##        "tpl": "metadata/knockout.mako",
##        "replace": true
##    }'></div>
##
##<!-- Render comments -->
##<div mod-meta='{
##        "tpl": "metadata/comment_group.mako",
##        "kwargs": {
##            "guid": "${node['id']}",
##            "top": true
##        },
##        "replace": true
##    }'></div>
##
##<!-- Boilerplate comment JS -->
##<div mod-meta='{
##        "tpl": "metadata/comment_js.mako",
##        "replace": true
##    }'></div>

</%def>

<%def name="children()">

<div class="page-header">
    % if node['category'] == 'project':
        <div class="pull-right">
            % if user['can_edit']:
                <a class="btn btn-default" data-toggle="modal" data-target="#newComponent">
            % else:
                <a class="btn btn-default disabled">
            % endif
                Add Component
        </a>
        </div>
        <%include file="modal_add_component.mako"/>
    % endif
    <h2>Components</h2>
</div>

% if node['children']:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_children/",
            "replace": true,
            "kwargs": {"sortable" : true}
        }'></div>
% else:
    <p>No components have been added to this project.</p>
% endif

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    % for style in addon_widget_css:
        <link rel="stylesheet" href="${style}" />
    % endfor
</%def>

<%def name="javascript_bottom()">

% for script in addon_widget_js:
    <script type="text/javascript" src="${script}"></script>
% endfor

## Todo: Move to project.js
<script>

    $(document).ready(function() {

        // Tooltips
        $('[data-toggle="tooltip"]').tooltip();

        // Tag input
        $('#node-tags').tagsInput({
            width: "100%",
            interactive:${'true' if user["can_edit"] else 'false'},
            onAddTag:function(tag){
                $.ajax({
                    url:"${node['api_url']}" + "addtag/" + tag + "/",
                    type:"POST",
                    contentType: "application/json"
                });
            },
            onRemoveTag:function(tag){
                $.ajax({
                    url:"${node['api_url']}" + "removetag/" + tag + "/",
                    type:"POST",
                    contentType: "application/json"
                });
            }
        });

        // Remove delete UI if not contributor
        % if not user['can_edit']:
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif

    });

</script>

</%def>
