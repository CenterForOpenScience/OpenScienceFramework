<%inherit file="notify_base.mako" />

<%def name="content()">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Registration of ${src.title} finished</h3>
  <span>
    <% from website import settings %>
    The registration of ${src.title} just finished! You can view the registration <a href="${settings.DOMAIN.rstrip('/') + src.url}">here</a>
  </span>
</%def>
