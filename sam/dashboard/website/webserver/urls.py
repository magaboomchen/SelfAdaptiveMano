from django.conf.urls import *
from webserver import views
import DjangoWeb.settings
# from .views import  UserInfoUpdate
# from webserver.views import login
# from webserver.viewsModule import viewsUser
# import webserver.viewsUser as viewsUser
from django.contrib.auth import views as user_views

# app_name = 'webserver'
urlpatterns = [
    url(r'^$', views.login),
    url(r'^login/$',views.login),
    url(r'^index/$',views.index),
    url(r'^logout/$',views.logout),
    # url(r'^user/list/$',views.userList, name='user_list'),
    # url(r'^user/list/(.+)/$',views.showUserList,name='user_listcc'),
    # url(r'^user/$',views.showUserList),
    url(r'^user/list/$',views.showUserList, name='user_list'),
    url(r'^user/list/(.+)/$',views.showUserList,name='user_listcc'),
    url(r'^user/$',views.showUserList),
    url(r'^zone/list/$',views.showZoneList, name='zone_list'),
    url(r'^zone/list/(.+)/$',views.showZoneList,name='zone_listcc'),
    url(r'^zone/$',views.showZoneList),
    url(r'^routingmorphic/list/$',views.showRoutingMorphicList, name='routingmorphic_list'),
    url(r'^routingmorphic/list/(.+)/$',views.showRoutingMorphicList,name='routingmorphic_listcc'),
    url(r'^routingmorphic/$',views.showRoutingMorphicList),
    url(r'^server/list/$',views.showServerList, name='server_list'),
    url(r'^server/list/(.+)/$',views.showServerList,name='server_listcc'),
    url(r'^server/$',views.showServerList),
    url(r'^switch/list/$',views.showSwitchList, name='switch_list'),
    url(r'^switch/list/(.+)/$',views.showSwitchList,name='switch_listcc'),
    url(r'^switch/$',views.showSwitchList),
    url(r'^link/list/$',views.showLinkList, name='link_list'),
    url(r'^link/list/(.+)/$',views.showLinkList,name='link_listcc'),
    url(r'^link/$',views.showLinkList),
    url(r'^request/list/$',views.showRequestList, name='request_list'),
    url(r'^request/list/(.+)/$',views.showRequestList,name='request_listcc'),
    url(r'^request/$',views.showRequestList),
    url(r'^user/add/$',views.userAdd),
    url(r'^user/alter/(.+)/$',views.userAlter,name='user_alter'),
    # url(r'^user/alter/(?P<id>\d+)/$', UserInfoUpdate.userAlter,name='user_alter'),
    # url(r'^user/alter/(.+)/$', UserInfoUpdate.userAlter,name='user_alter'),
    url(r'^cmdb/serverlist/$',views.serverList, name='server_list'),
    url(r'^cmdb/serverlist/(.+)/$',views.serverList,name='server_listcc'),
    url(r'^cmdb/serveradd/$',views.serverAdd, name='server_add'),
    url(r'^cmdb/hostadmin/$',views.hostAdmin, name='hostadmin'),
    url(r'^cmdb/monitor/$',views.getMonitor, name='monitor'),
    url(r'^cmdb/$',views.serverList),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',{'document_root': DjangoWeb.settings.STATIC_ROOT }),
]

