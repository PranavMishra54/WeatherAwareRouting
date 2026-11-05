from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health),
    path("analyze/", views.analyze),
    path("routes-preview/", views.routes_preview),
]