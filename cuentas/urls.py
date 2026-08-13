from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("recuperar/", views.PasswordResetView.as_view(), name="password_reset"),
    path("recuperar/enviado/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "recuperar/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("clave/", views.PasswordChangeView.as_view(), name="password_change"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/nuevo/", views.UsuarioCreateView.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_editar"),
    path(
        "usuarios/<int:pk>/desactivar/",
        views.UsuarioDesactivarView.as_view(),
        name="usuario_desactivar",
    ),
    path(
        "usuarios/<int:pk>/bloquear/",
        views.UsuarioBloquearView.as_view(),
        name="usuario_bloquear",
    ),
    path(
        "usuarios/<int:pk>/reset-clave/",
        views.UsuarioResetClaveView.as_view(),
        name="usuario_reset",
    ),
]
