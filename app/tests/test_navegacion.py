import re

from django.test import TestCase
from django.urls import reverse

from app.navigation import items_navegacion
from app.tests.factories import make_empresa, make_usuario


def _claves_nav(response):
    return re.findall(r'data-nav="([^"]+)"', response.content.decode())


class NavegacionPorRolTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()

    def _dashboard(self, usuario, empresa_sesion=None):
        self.client.force_login(usuario)
        if empresa_sesion is not None:
            session = self.client.session
            session["empresa_id"] = empresa_sesion.pk
            session.save()
        return self.client.get(reverse("app:dashboard"))

    def test_empleado_ve_solo_sus_links(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        response = self._dashboard(usuario)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _claves_nav(response),
            ["dashboard", "mias", "notificaciones", "ayuda", "perfil"],
        )
        self.assertNotContains(response, 'data-nav="usuarios"')
        self.assertNotContains(response, 'data-nav="equipo"')
        self.assertNotContains(response, 'data-nav="empresas"')
        self.assertNotContains(response, 'data-nav="plantillas"')
        self.assertNotContains(response, 'data-nav="ciclos"')
        self.assertNotContains(response, 'data-nav="reportes"')
        self.assertNotContains(response, 'data-nav="auditoria"')
        self.assertNotContains(response, 'data-nav="organigrama"')

    def test_supervisor_ve_equipo_organigrama_y_propias(self):
        usuario = make_usuario(self.empresa, rol="supervisor")
        response = self._dashboard(usuario)
        self.assertEqual(
            _claves_nav(response),
            [
                "dashboard",
                "organigrama",
                "plantillas",
                "ciclos",
                "equipo",
                "mias",
                "notificaciones",
                "ayuda",
                "perfil",
            ],
        )
        self.assertNotContains(response, 'data-nav="usuarios"')
        self.assertNotContains(response, 'data-nav="empresas"')
        self.assertNotContains(response, 'data-nav="reportes"')
        self.assertNotContains(response, 'data-nav="auditoria"')

    def test_admin_rrhh_ve_configuracion_de_empresa(self):
        usuario = make_usuario(self.empresa, rol="admin_rrhh")
        response = self._dashboard(usuario)
        self.assertEqual(
            _claves_nav(response),
            [
                "dashboard",
                "usuarios",
                "organigrama",
                "plantillas",
                "ciclos",
                "reportes",
                "auditoria",
                "notificaciones",
                "ayuda",
                "perfil",
            ],
        )
        self.assertNotContains(response, 'data-nav="empresas"')
        self.assertNotContains(response, 'data-nav="equipo"')
        self.assertNotContains(response, 'data-nav="mias"')
        self.assertContains(response, 'href="/reportes/iso/"')

    def test_superadmin_sin_contexto_solo_plataforma(self):
        usuario = make_usuario(None, rol="superadmin")
        response = self._dashboard(usuario)
        self.assertEqual(
            _claves_nav(response),
            ["dashboard", "empresas", "ayuda", "perfil"],
        )
        self.assertNotContains(response, 'data-nav="usuarios"')
        self.assertNotContains(response, 'data-nav="ciclos"')

    def test_superadmin_en_contexto_ve_resto_admin(self):
        usuario = make_usuario(None, rol="superadmin")
        response = self._dashboard(usuario, empresa_sesion=self.empresa)
        self.assertEqual(
            _claves_nav(response),
            [
                "dashboard",
                "empresas",
                "usuarios",
                "organigrama",
                "plantillas",
                "ciclos",
                "reportes",
                "auditoria",
                "notificaciones",
                "ayuda",
                "perfil",
            ],
        )

    def test_items_navegacion_helper_empleado(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        claves = [item["clave"] for item in items_navegacion(usuario, self.empresa)]
        self.assertEqual(claves, ["dashboard", "mias", "notificaciones", "ayuda", "perfil"])

    def test_sidebar_es_overlay_en_mobile(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        response = self._dashboard(usuario)
        self.assertContains(response, 'id="sidebar"')
        self.assertContains(response, "-translate-x-full")
        self.assertContains(response, "lg:static")
        self.assertContains(response, "lg:hidden")
        self.assertContains(response, 'id="btn-menu-movil"')
