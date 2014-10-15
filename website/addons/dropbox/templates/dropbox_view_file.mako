<%inherit file="project/addon/view_file.mako" />


<%def name="file_versions()">
<div class="scripted" id="revisionScope">
    <div id="deletingAlert" class="alert alert-warning fade">
        Deleting your file…
    </div>

    <ol class="breadcrumb">
        <li><a data-bind="attr: {href: filesUrl()}">{{nodeTitle}}</a></li>
        <li>Dropbox</li>
        <li class="active overflow" >{{path}}</li>
    </ol>

    <p>
        <!-- Download button -->
        <a
                data-bind="attr.href: downloadUrl"
                class="btn btn-success btn-lg"
            >Download <i class="icon-download-alt" ></i>
        </a>
        % if user['can_edit'] and 'write' in user['permissions']:
            <!--Delete button -->
            <button
                    data-bind="visible: deleteUrl() && !registered(), click: deleteFile"
                    class="btn btn-danger btn-lg"
                >Delete <i class="icon-trash"></i>
            </button>
        % endif
    </p>

    <table class="table dropbox-revision-table ">
        <thead>
            <tr>
                <th>Revision</th>
                <th>Date</th>
                <th></th>
            </tr>
        </thead>

        <!-- Highlight current revision in grey, or yellow if modified post-registration -->
        <!--
            Note: Registering Dropbox content is disabled for now; leaving
            this code here in case we enable registrations later on.
            @jmcarp
        -->
        <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
            <tr data-bind="css: {
                    warning: $root.registered() && revision.modified.date > $root.registered(),
                    active: revision.rev === $root.currentRevision
                }">
                <td>
                    <a data-bind="attr: {href: revision.view}">{{ revision.rev }}</a>
                </td>
                <td>{{ revision.modified.local }}</td>
                <td>
                    <a data-bind="attr: {href: revision.download}" class="btn btn-primary btn-sm">
                        Download <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>
    <div class="help-block">
        <p data-bind="if: registered">Revisions marked in
            <span class="text-warning">yellow</span> were made after this
            project was registered.</p>
    </div>
</div>

<script>
    $script(["/static/addons/dropbox/revisions.js"], function() {
        var url = '${revisions_url}';
        var revisionTable = new RevisionTable('#revisionScope', url);
    });
</script>
</%def>
