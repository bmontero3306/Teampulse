from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from app.navigation import items_navegacion
from app.tests.factories import make_empresa, make_usuario

HREFS = {
    "dashboard": "/dashboard",
    "empresas": "/empresas",
    "usuarios": "/usuarios",
    "organigrama": "/organizacion",
    "plantillas": "/evaluaciones/plantillas",
    "ciclos": "/evaluaciones/ciclos",
    "equipo": "/evaluaciones/equipo",
    "mias": "/evaluaciones/mias",
    "reportes": "/reportes/iso",
    "auditoria": "/auditoria",
    "notificaciones": "/notificaciones",
    "ayuda": "/ayuda",
    "perfil": "/perfil",
}


def _claves(usuario, empresa=None):
    return [item["clave"] for item in items_navegacion(usuario, empresa)]


class NavegacionPorRolTests(TestCase):
    def setUp(self):
        self.empresa = make_empresa()

    def test_anonimo_no_ve_menu(self):
        self.assertEqual(items_navegacion(None), [])
        self.assertEqual(items_navegacion(AnonymousUser()), [])

    def test_empleado_ve_solo_sus_links(self):
        usuario = make_usuario(self.empresa, rol="empleado")
        self.assertEqual(
            _claves(usuario, self.empresa),
            ["dashboard", "mias", "notificaciones", "ayuda", "perfil"],
        )

    def test_supervisor_ve_equipo_organigrama_y_propias(self):
        usuario = make_usuario(self.empresa, rol="supervisor")
        self.assertEqual(
            _claves(usuario, self.empresa),
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

    def test_admin_rrhh_ve_configuracion_de_empresa(self):
        usuario = make_usuario(self.empresa, rol="admin_rrhh")
        items = items_navegacion(usuario, self.empresa)
        self.assertEqual(
            [item["clave"] for item in items],
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
        self.assertEqual(
            next(item["href"] for item in items if item["clave"] == "reportes"),
            "/reportes/iso",
        )

    def test_superadmin_sin_contexto_solo_plataforma(self):
        usuario = make_usuario(None, rol="superadmin")
        self.assertEqual(
            _claves(usuario, None),
            ["dashboard", "empresas", "ayuda", "perfil"],
        )

    def test_superadmin_en_contexto_ve_resto_admin(self):
        usuario = make_usuario(None, rol="superadmin")
        self.assertEqual(
            _claves(usuario, self.empresa),
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

    def test_hrefs_son_paths_de_la_spa(self):
        usuario = make_usuario(None, rol="superadmin")
        items = items_navegacion(usuario, self.empresa)
        self.assertEqual(
            {item["clave"]: item["href"] for item in items},
            {clave: HREFS[clave] for clave in _claves(usuario, self.empresa)},
        )
        for item in items:
            self.assertFalse(item["href"].endswith("/"))
            self.assertNotIn("cuentas:", item["href"])
