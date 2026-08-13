from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse

from app.tests.factories import make_empresa
from cuentas.models import Usuario
from empresas.models import Empresa
from empresas.views import (
    EmpresaActivarView,
    EmpresaCrearView,
    EmpresaDetalleView,
    EmpresaEditarView,
    EmpresaListaView,
    EmpresaSeleccionarView,
    EmpresaSuspenderView,
)


def _usuario(empresa=None, rol="empleado", **kwargs):
    """Usuario en memoria: WP2 aún no migró puesto/area/supervisor."""
    return Usuario(
        email=kwargs.get("email", f"{rol}@empresa.test"),
        rol=rol,
        empresa=empresa,
        is_staff=kwargs.get("is_staff", rol == "superadmin"),
        is_superuser=kwargs.get("is_superuser", rol == "superadmin"),
        is_active=True,
        first_name="Nombre",
        last_name="Apellido",
    )


def _datos_form(**kwargs):
    data = {
        "nombre": "Nueva Co",
        "razon_social": "Nueva Co S.A.",
        "cuit": "30999999999",
        "email_contacto": "nueva@test.com",
        "telefono": "1111",
        "direccion": "Calle 123",
        "estado": Empresa.Estado.ACTIVA,
    }
    data.update(kwargs)
    return data


class RequestViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _auth(self, request, user, empresa=None):
        request.user = user
        request.empresa = empresa if empresa is not None else getattr(user, "empresa", None)
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request


class PermisosEmpresasTests(RequestViewTestCase):
    def setUp(self):
        super().setUp()
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.superadmin = _usuario(None, rol="superadmin")
        self.admin_a = _usuario(self.empresa_a, rol="admin_rrhh", email="admin-a@empresa.test")
        self.empleado_a = _usuario(self.empresa_a, rol="empleado", email="emp-a@empresa.test")

    def test_anonimo_redirige_a_login(self):
        request = self.factory.get(reverse("empresas:lista"))
        self._auth(request, AnonymousUser(), empresa=None)
        response = EmpresaListaView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_superadmin_ve_lista(self):
        request = self.factory.get(reverse("empresas:lista"))
        self._auth(request, self.superadmin)
        response = EmpresaListaView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.empresa_a.nombre)
        self.assertContains(response, self.empresa_b.nombre)

    def test_empleado_no_accede_a_lista(self):
        request = self.factory.get(reverse("empresas:lista"))
        self._auth(request, self.empleado_a)
        with self.assertRaises(PermissionDenied):
            EmpresaListaView.as_view()(request)

    def test_admin_rrhh_no_accede_a_lista_plataforma(self):
        request = self.factory.get(reverse("empresas:lista"))
        self._auth(request, self.admin_a)
        with self.assertRaises(PermissionDenied):
            EmpresaListaView.as_view()(request)

    def test_admin_empresa_a_no_ve_empresa_b(self):
        request = self.factory.get(reverse("empresas:detalle", args=[self.empresa_a.pk]))
        self._auth(request, self.admin_a)
        propia = EmpresaDetalleView.as_view()(request, pk=self.empresa_a.pk)
        self.assertEqual(propia.status_code, 200)
        self.assertContains(propia, self.empresa_a.nombre)

        request_b = self.factory.get(reverse("empresas:detalle", args=[self.empresa_b.pk]))
        self._auth(request_b, self.admin_a)
        with self.assertRaises(Http404):
            EmpresaDetalleView.as_view()(request_b, pk=self.empresa_b.pk)

        request_editar = self.factory.get(reverse("empresas:editar", args=[self.empresa_b.pk]))
        self._auth(request_editar, self.admin_a)
        with self.assertRaises(Http404):
            EmpresaEditarView.as_view()(request_editar, pk=self.empresa_b.pk)

    def test_admin_rrhh_no_puede_crear_ni_suspender(self):
        request = self.factory.get(reverse("empresas:crear"))
        self._auth(request, self.admin_a)
        with self.assertRaises(PermissionDenied):
            EmpresaCrearView.as_view()(request)

        request_s = self.factory.post(reverse("empresas:suspender", args=[self.empresa_a.pk]))
        self._auth(request_s, self.admin_a)
        with self.assertRaises(PermissionDenied):
            EmpresaSuspenderView.as_view()(request_s, pk=self.empresa_a.pk)

        request_a = self.factory.post(reverse("empresas:activar", args=[self.empresa_a.pk]))
        self._auth(request_a, self.admin_a)
        with self.assertRaises(PermissionDenied):
            EmpresaActivarView.as_view()(request_a, pk=self.empresa_a.pk)

    def test_admin_rrhh_edita_ficha_propia_sin_desactivar(self):
        request = self.factory.post(
            reverse("empresas:editar", args=[self.empresa_a.pk]),
            {
                "nombre": "Empresa A Renombrada",
                "email_contacto": "nuevo@a.test",
                "telefono": "222",
                "direccion": "Nueva dir",
                "estado": Empresa.Estado.SUSPENDIDA,
                "cuit": "20111111111",
            },
        )
        self._auth(request, self.admin_a)
        response = EmpresaEditarView.as_view()(request, pk=self.empresa_a.pk)
        self.assertEqual(response.status_code, 302)
        self.empresa_a.refresh_from_db()
        self.assertEqual(self.empresa_a.nombre, "Empresa A Renombrada")
        self.assertEqual(self.empresa_a.email_contacto, "nuevo@a.test")
        self.assertEqual(self.empresa_a.estado, Empresa.Estado.ACTIVA)
        self.assertNotEqual(self.empresa_a.cuit, "20111111111")


class CrudEmpresasTests(RequestViewTestCase):
    def setUp(self):
        super().setUp()
        self.superadmin = _usuario(None, rol="superadmin")

    def test_crear_empresa(self):
        request = self.factory.post(reverse("empresas:crear"), _datos_form())
        self._auth(request, self.superadmin)
        response = EmpresaCrearView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        empresa = Empresa.objects.get(cuit="30999999999")
        self.assertEqual(empresa.nombre, "Nueva Co")
        self.assertEqual(empresa.estado, Empresa.Estado.ACTIVA)

    def test_editar_y_pasar_a_inactiva(self):
        empresa = make_empresa()
        request = self.factory.post(
            reverse("empresas:editar", args=[empresa.pk]),
            _datos_form(
                nombre="Editada",
                razon_social=empresa.razon_social,
                cuit=empresa.cuit,
                email_contacto=empresa.email_contacto,
                estado=Empresa.Estado.INACTIVA,
            ),
        )
        self._auth(request, self.superadmin)
        response = EmpresaEditarView.as_view()(request, pk=empresa.pk)
        self.assertEqual(response.status_code, 302)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nombre, "Editada")
        self.assertEqual(empresa.estado, Empresa.Estado.INACTIVA)

    def test_suspender_post(self):
        empresa = make_empresa()
        request_get = self.factory.get(reverse("empresas:suspender", args=[empresa.pk]))
        self._auth(request_get, self.superadmin)
        confirmacion = EmpresaSuspenderView.as_view()(request_get, pk=empresa.pk)
        self.assertEqual(confirmacion.status_code, 200)

        request = self.factory.post(reverse("empresas:suspender", args=[empresa.pk]))
        self._auth(request, self.superadmin)
        response = EmpresaSuspenderView.as_view()(request, pk=empresa.pk)
        self.assertEqual(response.status_code, 302)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.SUSPENDIDA)
        self.assertFalse(empresa.permite_login)

    def test_activar_post(self):
        empresa = make_empresa(estado=Empresa.Estado.SUSPENDIDA)
        request = self.factory.post(reverse("empresas:activar", args=[empresa.pk]))
        self._auth(request, self.superadmin)
        response = EmpresaActivarView.as_view()(request, pk=empresa.pk)
        self.assertEqual(response.status_code, 302)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, Empresa.Estado.ACTIVA)

    def test_filtro_por_estado(self):
        make_empresa(nombre="Activa X", estado=Empresa.Estado.ACTIVA)
        suspendida = make_empresa(nombre="Suspendida Y", estado=Empresa.Estado.SUSPENDIDA)
        request = self.factory.get(reverse("empresas:lista"), {"estado": "suspendida"})
        self._auth(request, self.superadmin)
        response = EmpresaListaView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, suspendida.nombre)
        self.assertEqual(
            list(response.context_data["empresas"].values_list("pk", flat=True)),
            [suspendida.pk],
        )

    def test_plataforma_empresas_resuelve(self):
        resolved = resolve("/plataforma/empresas/")
        self.assertEqual(resolved.url_name, "lista")
        response = self.client.get("/plataforma/empresas/")
        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)


class SelectorEmpresaTests(RequestViewTestCase):
    def test_superadmin_selecciona_empresa_en_sesion(self):
        empresa = make_empresa()
        superadmin = _usuario(None, rol="superadmin")
        request = self.factory.post(reverse("empresas:seleccionar", args=[empresa.pk]))
        self._auth(request, superadmin)
        response = EmpresaSeleccionarView.as_view()(request, pk=empresa.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session["empresa_id"], empresa.pk)
        self.assertEqual(request.empresa, empresa)

    def test_admin_rrhh_no_selecciona_contexto(self):
        empresa = make_empresa()
        admin = _usuario(empresa, rol="admin_rrhh")
        request = self.factory.post(reverse("empresas:seleccionar", args=[empresa.pk]))
        self._auth(request, admin)
        with self.assertRaises(PermissionDenied):
            EmpresaSeleccionarView.as_view()(request, pk=empresa.pk)
