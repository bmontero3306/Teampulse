from django.urls import path

from notificaciones import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.ListaNotificacionesView.as_view(), name="lista"),
    path("leer-todas/", views.LeerTodasNotificacionesView.as_view(), name="leer_todas"),
    path("<int:pk>/leer/", views.LeerNotificacionView.as_view(), name="leer"),
]
