<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki (History)</%def>

<div class="wiki">
    <div class="row">
        <div class="col-md-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
        <div class="col-md-9">
            <%include file="wiki/templates/status.mako"/>
        </div>
        <div class="col-md-6 wiki">
            ${wiki_content | n}
        </div>
        <div class="col-md-3">
            <%include file="wiki/templates/history.mako" />
        </div>
    </div>
</div>

<script type="text/javascript">
    window.onload = function() {
        $('#pageName').append('<h5 style="margin-top:5px"><span>Version: </span>${compare_version}</h5>');
    }
</script>
