from django.urls import path

from . import views

urlpatterns = [
    path('sfci/', views.add_sfci),
    path('sfc/', views.sfc_view)
]
