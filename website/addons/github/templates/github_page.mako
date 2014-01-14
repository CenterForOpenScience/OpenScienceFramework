<%inherit file="project/addon/page.mako" />

<div class="row">

    <div class="col-md-6">

        <div>

            Viewing ${gh_user} / ${repo} :

            % if len(branches) == 1:

                ${branches[0]['name']}

            % elif len(branches) > 1:

                <form role="form" style="display: inline;">
                    <select id="gitBranchSelect" name="branch">
                        % for _branch in branches:
                            <option
                                value=${_branch['name']}
                                ${'selected' if branch == _branch['name'] else ''}
                            >${_branch['name']}</option>
                        % endfor
                    </select>
                </form>

            % endif

        </div>

        % if sha:
            <p>Commit: ${sha}</p>
        % endif

    </div>

    <div class="col-md-6">

        <div>
            Download:
            <a href="${api_url}github/tarball/?ref=${ref}">Tarball</a>
            <span>|</span>
            <a href="${api_url}github/zipball/?ref=${ref}">Zip</a>
        </div>

    </div>

</div>

% if user['can_edit']:

    % if has_auth:

        <div class="container" style="position: relative;">
            <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="gitFormUpload">click here</a>) to upload files</h3>
            <div id="fallback"></div>
            <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
                <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
            </div>
        </div>

    % else:

        <p>
            This GitHub add-on has not been authenticated. To enable file uploads and deletion,
            browse to the <a href="${node['url']}settings/">settings</a> page and authenticate this add-on.
        <p>

    % endif

% endif

<div id="grid">
    <div id="gitCrumb"></div>
    <div id="gitGrid"></div>
</div>

<script type="text/javascript">

    // Import JS variables
    var gridData = ${grid_data},
        branch = '${branch}',
        sha = '${sha}',
        canEdit = ${int(user['can_edit'])},
        hasAuth = ${int(has_auth)},
        isHead = ${int(is_head)};

    // Submit branch form on change
    % if len(branches) > 1:
        $('#gitBranchSelect').on('change', function() {
            $(this).closest('form').submit();
        });
    % endif

</script>
