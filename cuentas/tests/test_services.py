from django.test import TestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.services import sincronizar_supervisor
from organizacion.models import Area, Puesto


class SincronizarSupervisorTests(TestCase):
    def test_sin_puesto_no_crashea(self):
        empresa = make_empresa()
        usuario = make_usuario(empresa)
        self.assertIsNone(sincronizar_supervisor(usuario))

    def test_deriva_supervisor_del_puesto_superior(self):
        empresa = make_empresa()
        area = Area.objects.create(empresa=empresa, nombre="Operaciones")
        puesto_jefe = Puesto.objects.create(empresa=empresa, nombre="Jefe", area=area)
        puesto_analista = Puesto.objects.create(
            empresa=empresa,
            nombre="Analista",
            area=area,
            puesto_superior=puesto_jefe,
        )
        jefe = make_usuario(empresa, rol="supervisor", puesto=puesto_jefe)
        empleado = make_usuario(empresa, rol="empleado", puesto=puesto_analista)
        sincronizar_supervisor(empleado)
        self.assertEqual(empleado.supervisor, jefe)
