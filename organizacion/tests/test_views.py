from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from app.tests.factories import (
    make_area,
    make_competencia,
    make_empresa,
    make_puesto,
    make_usuario,
)
from cuentas.models import Usuario
from organizacion.models import Competencia, Puesto


def _items(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


class ApiOrganizacionTests(APITestCase):
    def setUp(self):
        self.empresa_a = make_empresa(nombre="Empresa A")
        self.empresa_b = make_empresa(nombre="Empresa B")
        self.admin_a = make_usuario(self.empresa_a, rol="admin_rrhh")
        self.admin_b = make_usuario(self.empresa_b, rol="admin_rrhh")
        self.supervisor_a = make_usuario(self.empresa_a, rol="supervisor")
        self.superadmin = make_usuario(self.empresa_a, rol=Usuario.Rol.SUPERADMIN)
        self.area_propia = make_area(self.empresa_a, nombre="Área propia")
        self.puesto_propio = make_puesto(
            self.empresa_a, nombre="Puesto propio", area=self.area_propia
        )
        self.empleado_a = make_usuario(
            self.empresa_a,
            rol="empleado",
            puesto=self.puesto_propio,
            area=self.area_propia,
        )
        self.empleado_sin_puesto = make_usuario(self.empresa_a, rol="empleado")

    def _auth(self, usuario, empresa=None):
        token, _ = Token.objects.get_or_create(user=usuario)
        extra = {}
        if empresa is not None:
            extra["HTTP_X_EMPRESA_ID"] = str(empresa.pk)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}", **extra)

    def test_listado_puestos_filtrado_por_tenant(self):
        make_puesto(self.empresa_a, nombre="De A")
        make_puesto(self.empresa_b, nombre="De B")
        self._auth(self.admin_a)
        response = self.client.get("/api/v1/puestos/")
        self.assertEqual(response.status_code, 200)
        nombres = [item["nombre"] for item in _items(response)]
        self.assertIn("De A", nombres)
        self.assertNotIn("De B", nombres)

    def test_listado_areas_filtrado_por_tenant(self):
        make_area(self.empresa_a, nombre="Área De A")
        make_area(self.empresa_b, nombre="Área De B")
        self._auth(self.admin_a)
        response = self.client.get("/api/v1/areas/")
        nombres = [item["nombre"] for item in _items(response)]
        self.assertIn("Área De A", nombres)
        self.assertNotIn("Área De B", nombres)

    def test_listado_competencias_filtrado_por_tenant(self):
        make_competencia(self.empresa_a, nombre="Comp De A")
        make_competencia(self.empresa_b, nombre="Comp De B")
        self._auth(self.admin_a)
        response = self.client.get("/api/v1/competencias/")
        nombres = [item["nombre"] for item in _items(response)]
        self.assertIn("Comp De A", nombres)
        self.assertNotIn("Comp De B", nombres)

    def test_organigrama_filtrado_por_tenant(self):
        raiz = make_puesto(self.empresa_a, nombre="Raíz A", descripcion="Dirige A")
        make_puesto(self.empresa_a, nombre="Analista", puesto_superior=raiz)
        make_puesto(self.empresa_b, nombre="Raíz B")
        self._auth(self.admin_a)
        response = self.client.get("/api/v1/organigrama/")
        self.assertEqual(response.status_code, 200)
        nombres = [nodo["nombre"] for nodo in response.data["raices"]]
        self.assertIn("Raíz A", nombres)
        self.assertNotIn("Raíz B", nombres)
        nodo = next(nodo for nodo in response.data["raices"] if nodo["nombre"] == "Raíz A")
        self.assertEqual(nodo["descripcion"], "Dirige A")
        self.assertEqual([hijo["nombre"] for hijo in nodo["hijos"]], ["Analista"])
        self.assertFalse(response.data["sin_puesto"])
        self.assertTrue(response.data["puede_editar"])

    def test_referencia_circular_de_puesto_rechazada(self):
        gerente = make_puesto(self.empresa_a, nombre="Gerente")
        jefe = make_puesto(self.empresa_a, nombre="Jefe", puesto_superior=gerente)
        self._auth(self.admin_a)
        response = self.client.patch(
            f"/api/v1/puestos/{gerente.pk}/",
            {"puesto_superior": jefe.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("circular", str(response.data["puesto_superior"]).lower())
        gerente.refresh_from_db()
        self.assertIsNone(gerente.puesto_superior_id)

    def test_referencia_circular_de_area_rechazada(self):
        direccion = make_area(self.empresa_a, nombre="Dirección")
        operaciones = make_area(
            self.empresa_a, nombre="Operaciones", area_padre=direccion
        )
        self._auth(self.admin_a)
        response = self.client.patch(
            f"/api/v1/areas/{direccion.pk}/",
            {"area_padre": operaciones.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("circular", str(response.data["area_padre"]).lower())
        direccion.refresh_from_db()
        self.assertIsNone(direccion.area_padre_id)

    def test_area_de_otra_empresa_rechazada_en_puesto(self):
        area_b = make_area(self.empresa_b, nombre="Área B")
        self._auth(self.admin_a)
        response = self.client.post(
            "/api/v1/puestos/",
            {"nombre": "Cruzado", "area": area_b.pk, "activo": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("area", response.data)
        self.assertFalse(Puesto.objects.filter(nombre="Cruzado").exists())

    def test_area_padre_de_otra_empresa_rechazada(self):
        area_b = make_area(self.empresa_b, nombre="Padre B")
        self._auth(self.admin_a)
        response = self.client.post(
            "/api/v1/areas/",
            {"nombre": "Hija A", "area_padre": area_b.pk, "activa": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("area_padre", response.data)

    def test_puesto_no_incluye_competencias(self):
        self._auth(self.admin_a)
        response = self.client.get(f"/api/v1/puestos/{self.puesto_propio.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("competencias", response.data)
        self.assertEqual(
            set(response.data),
            {
                "id",
                "nombre",
                "descripcion",
                "area",
                "area_nombre",
                "puesto_superior",
                "puesto_superior_nombre",
                "activo",
            },
        )

    def test_supervisor_lee_activos_y_no_crea(self):
        make_puesto(self.empresa_a, nombre="Visible", activo=True)
        make_puesto(self.empresa_a, nombre="Inactivo", activo=False)
        make_area(self.empresa_a, nombre="Área inactiva", activa=False)
        make_competencia(self.empresa_a, nombre="Comp inactiva", activa=False)
        self._auth(self.supervisor_a)
        puestos = self.client.get("/api/v1/puestos/")
        self.assertEqual(puestos.status_code, 200)
        nombres = [item["nombre"] for item in _items(puestos)]
        self.assertIn("Visible", nombres)
        self.assertNotIn("Inactivo", nombres)
        areas = [item["nombre"] for item in _items(self.client.get("/api/v1/areas/"))]
        self.assertNotIn("Área inactiva", areas)
        competencias = [
            item["nombre"] for item in _items(self.client.get("/api/v1/competencias/"))
        ]
        self.assertNotIn("Comp inactiva", competencias)
        alta = self.client.post(
            "/api/v1/puestos/",
            {"nombre": "No debería", "activo": True},
            format="json",
        )
        self.assertEqual(alta.status_code, 403)

    def test_rrhh_y_superadmin_ven_inactivos_de_su_empresa(self):
        make_puesto(self.empresa_a, nombre="Inactivo A", activo=False)
        make_puesto(self.empresa_b, nombre="Inactivo B", activo=False)
        for usuario in (self.admin_a, self.superadmin):
            self._auth(usuario)
            nombres = [
                item["nombre"] for item in _items(self.client.get("/api/v1/puestos/"))
            ]
            self.assertIn("Inactivo A", nombres)
            self.assertNotIn("Inactivo B", nombres)

    def test_empleado_solo_ve_su_puesto_y_area(self):
        make_puesto(self.empresa_a, nombre="Otro puesto")
        make_area(self.empresa_a, nombre="Otra área")
        make_competencia(self.empresa_a, nombre="Comp activa")
        make_competencia(self.empresa_a, nombre="Comp inactiva", activa=False)
        self._auth(self.empleado_a)
        puestos = _items(self.client.get("/api/v1/puestos/"))
        self.assertEqual([item["nombre"] for item in puestos], ["Puesto propio"])
        areas = _items(self.client.get("/api/v1/areas/"))
        self.assertEqual([item["nombre"] for item in areas], ["Área propia"])
        competencias = [
            item["nombre"] for item in _items(self.client.get("/api/v1/competencias/"))
        ]
        self.assertIn("Comp activa", competencias)
        self.assertNotIn("Comp inactiva", competencias)
        alta = self.client.post(
            "/api/v1/puestos/",
            {"nombre": "No", "activo": True},
            format="json",
        )
        self.assertEqual(alta.status_code, 403)

    def test_empleado_sin_puesto_ve_organigrama_vacio(self):
        make_puesto(self.empresa_a, nombre="Oculto para empleado")
        make_competencia(self.empresa_a, nombre="No la ve")
        self._auth(self.empleado_sin_puesto)
        response = self.client.get("/api/v1/organigrama/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["raices"], [])
        self.assertTrue(response.data["sin_puesto"])
        self.assertFalse(response.data["puede_editar"])
        self.assertEqual(_items(self.client.get("/api/v1/puestos/")), [])
        self.assertEqual(_items(self.client.get("/api/v1/areas/")), [])
        self.assertEqual(_items(self.client.get("/api/v1/competencias/")), [])

    def test_empleado_con_puesto_ve_su_rama(self):
        raiz = make_puesto(self.empresa_a, nombre="Director")
        hijo = make_puesto(self.empresa_a, nombre="Analista", puesto_superior=raiz)
        make_puesto(self.empresa_a, nombre="Ajeno")
        empleado = make_usuario(self.empresa_a, rol="empleado", puesto=hijo)
        self._auth(empleado)
        response = self.client.get("/api/v1/organigrama/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([nodo["nombre"] for nodo in response.data["raices"]], ["Analista"])
        self.assertFalse(response.data["sin_puesto"])

    def test_admin_no_edita_puesto_de_otra_empresa(self):
        puesto_b = make_puesto(self.empresa_b, nombre="Ajeno")
        self._auth(self.admin_a)
        response = self.client.get(f"/api/v1/puestos/{puesto_b.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_crear_puesto(self):
        self._auth(self.admin_a)
        response = self.client.post(
            "/api/v1/puestos/",
            {
                "nombre": "Líder",
                "descripcion": "Coordina el equipo",
                "area": None,
                "puesto_superior": None,
                "activo": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            Puesto.objects.filter(nombre="Líder", empresa=self.empresa_a).exists()
        )

    def test_autenticacion_requerida(self):
        response = self.client.get("/api/v1/puestos/")
        self.assertIn(response.status_code, (401, 403))


class CompetenciaRapidaTests(APITestCase):
    def setUp(self):
        self.empresa = make_empresa()
        self.otra = make_empresa()
        self.admin = make_usuario(self.empresa, rol="admin_rrhh")
        self.empleado = make_usuario(self.empresa, rol="empleado")

    def _auth(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_admin_crea_competencia_json(self):
        self._auth(self.admin)
        response = self.client.post(
            "/api/v1/competencias/rapida/",
            {
                "nombre": "Pensamiento crítico",
                "tipo": Competencia.Tipo.ACTITUDINAL,
                "descripcion": "Analiza problemas.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.data
        self.assertEqual(payload["nombre"], "Pensamiento crítico")
        self.assertEqual(payload["tipo"], Competencia.Tipo.ACTITUDINAL)
        competencia = Competencia.objects.get(pk=payload["id"])
        self.assertEqual(competencia.empresa_id, self.empresa.pk)
        self.assertTrue(competencia.activa)
        self.assertEqual(competencia.tipo, Competencia.Tipo.ACTITUDINAL)

    def test_nombre_vacio_devuelve_400(self):
        self._auth(self.admin)
        response = self.client.post(
            "/api/v1/competencias/rapida/",
            {"nombre": "", "tipo": Competencia.Tipo.TECNICA},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("nombre", response.data)

    def test_empleado_no_crea(self):
        self._auth(self.empleado)
        response = self.client.post(
            "/api/v1/competencias/rapida/",
            {"nombre": "No debería", "tipo": Competencia.Tipo.TECNICA},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Competencia.objects.filter(nombre="No debería").exists())

    def test_no_crea_en_otra_empresa(self):
        admin_b = make_usuario(self.otra, rol="admin_rrhh")
        self._auth(admin_b)
        response = self.client.post(
            "/api/v1/competencias/rapida/",
            {"nombre": "Solo B", "tipo": Competencia.Tipo.TECNICA},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        competencia = Competencia.objects.get(nombre="Solo B")
        self.assertEqual(competencia.empresa_id, self.otra.pk)
        self.assertFalse(
            Competencia.objects.filter(nombre="Solo B", empresa=self.empresa).exists()
        )
