from django.urls import path

from . import views

urlpatterns = [
    path('sfci/', views.add_sfci)
]
