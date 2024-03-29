#from django.conf.urls import patterns, include, url
from os import name
from django.conf.urls import *
# from django.urls import path, re_path
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
import DjangoWeb.settings

from django.views.generic.base import TemplateView

admin.autodiscover()
from django.conf.urls import handler404, handler500

handler404 = "webserver.views.page_not_found"
handler500 = "webserver.views.page_error"

# app_name = 'DjangoWeb'
urlpatterns = [
    # Examples:
    # url(r'^$', 'DjangoWeb.views.home', name='home'),
    # url(r'^DjangoWeb/', include('DjangoWeb.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^webserver/', include('webserver.urls')),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': DjangoWeb.settings.STATIC_ROOT }),
    url('admin/', admin.site.urls),
    url('', TemplateView.as_view(template_name='index.html')),
    #url(r'^medias/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'F:/DjangoWeb/webserver/templates/images'}),
    #url(r'^css/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'F:/DjangoWeb/webserver/templates/css'}),
]