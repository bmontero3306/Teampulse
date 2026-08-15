from django.urls import path

from . import views

app_name = "app"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("ayuda/", views.AyudaIndexView.as_view(), name="ayuda"),
    path("ayuda/<slug:slug>/", views.AyudaPaginaView.as_view(), name="ayuda_pagina"),
]
