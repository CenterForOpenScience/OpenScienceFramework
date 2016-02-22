<div class="modal fade" id="discussionsContributorsModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
              <h3>Project Mailing List Email:</h3>
            </div>

            <div class="modal-body">
                <h4 class="text-center">
                <div class="btn-group">
                    <button data-clipboard-text="${node['id']}@osf.io" title="Copy to clipboard" class="btn btn-default btn-sm m-r-xs copy-button zeroclipboard-is-hover">
                        <i class="fa fa-copy"></i>
                    </button>
                    <input readonly="readonly" class="link-url", click: toggle, clickBubble: false type="text", value="${node['id']}@osf.io">
                </div>
                </h4>
                
                % if len(node['discussions_unsubs']):
                    <p>${node['contrib_count'] - len(node['discussions_unsubs'])} out of ${node['contrib_count']} contributors will receive any email sent to this address.</p>
                    <p>A contributor who is not subscribed to this mailing list will not recieve any emails sent to it. To
                    % if user['is_admin']:
                        disable or 
                    % endif:
                        unsubscribe from this mailing list, visit the <a href="${node['url']}settings/#configureNotificationsAnchor" class="">${node['category']} settings</a>.
                    </p>
                    <div style="padding-left: 15px; background-color: #F5F5F5; border: 1px solid #CCC;">
                        Contributors not on this list: 
                        <a id="unsubToggle" role="button" data-toggle="collapse" href="#unsubContribs" aria-expanded="false" aria-controls="unsubContribs">
                            Show
                        </a>
                        <div id="unsubContribs" class="panel-collapse collapse" role="tabpanel" aria-expanded="false" aria-labelledby="unsubToggle">
                        % for each in node['discussions_unsubs']:
                            <div style="padding-left: 15px">
                               ${each}
                            </div>
                        % endfor
                        </div>
                    </div>
                % else:
                    <br/>
                    <p>All contributors are subscribed and will receive any email sent to this address.</p>
                % endif

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-dismiss="modal">Close</a>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script>
$(document).ready(function() {
    $('#unsubContribs').on('hide.bs.collapse', function () {
        $('#unsubToggle').text('Show');
    });
    $('#unsubContribs').on('show.bs.collapse', function () {
        $('#unsubToggle').text('Hide');
    });
});
</script>
