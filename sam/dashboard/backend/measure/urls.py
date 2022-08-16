from django.urls import path

from . import views

urlpatterns = [
    path('servers/', views.get_server_set),
    path('links/', views.get_links),
    path('switches/', views.get_switches),
    path('sfcis/', views.get_sfcis),
]
