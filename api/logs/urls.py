from django.conf.urls import url

from api.logs import views

urlpatterns = [
    url(r'^$', views.LogList.as_view(), name='log-list'),
    url(r'^(?P<log_id>\w+)/nodes/$', views.LogNodeList.as_view(), name='log-nodes'),
]
