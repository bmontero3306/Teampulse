from django.test import TestCase

from app.tests.factories import make_empresa, make_usuario
from cuentas.models import Usuario
from cuentas.services import sincronizar_supervisor, usuarios_para_recuperar_clave
from empresas.models import Empresa
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


class UsuariosParaRecuperarTests(TestCase):
    def test_solo_activos_no_bloqueados_con_clave_y_empresa_activa_o_superadmin(self):
        empresa = make_empresa()
        activo = make_usuario(empresa, email="activo@empresa.test")
        make_usuario(empresa, email="bloqueado@empresa.test", bloqueado=True)
        make_usuario(empresa, email="inactivo@empresa.test", is_active=False)
        sin_clave = make_usuario(empresa, email="sinclave@empresa.test")
        sin_clave.set_unusable_password()
        sin_clave.save(update_fields=["password"])
        suspendida = make_empresa(estado=Empresa.Estado.SUSPENDIDA)
        make_usuario(suspendida, email="suspendido@empresa.test")
        inactiva = make_empresa(estado=Empresa.Estado.INACTIVA)
        make_usuario(inactiva, email="inactiva@empresa.test")
        Usuario.objects.create_superuser(
            email="super@teampulse.test",
            password="clave-test-123",
        )

        self.assertEqual(
            [usuario.pk for usuario in usuarios_para_recuperar_clave("ACTIVO@empresa.test")],
            [activo.pk],
        )
        self.assertEqual(
            [usuario.email for usuario in usuarios_para_recuperar_clave("super@teampulse.test")],
            ["super@teampulse.test"],
        )
        for email in (
            "bloqueado@empresa.test",
            "inactivo@empresa.test",
            "sinclave@empresa.test",
            "suspendido@empresa.test",
            "inactiva@empresa.test",
        ):
            self.assertEqual(list(usuarios_para_recuperar_clave(email)), [])
