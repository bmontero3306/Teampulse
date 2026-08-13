from itertools import count

from cuentas.models import Usuario
from empresas.models import Empresa

_seq = count(1)


def make_empresa(**kwargs):
    n = next(_seq)
    datos = {
        "nombre": f"Empresa {n}",
        "razon_social": f"Empresa {n} S.A.",
        "cuit": f"{30000000000 + n}",
        "email_contacto": f"contacto{n}@empresa.test",
        "estado": Empresa.Estado.ACTIVA,
    }
    datos.update(kwargs)
    return Empresa.objects.create(**datos)


def make_usuario(empresa, rol="empleado", **kwargs):
    n = next(_seq)
    password = kwargs.pop("password", "clave-test-123")
    email = kwargs.pop("email", f"usuario{n}@empresa.test")
    kwargs.setdefault("first_name", "Nombre")
    kwargs.setdefault("last_name", "Apellido")
    kwargs.setdefault("must_change_password", False)
    kwargs.setdefault("is_active", True)
    return Usuario.objects.create_user(
        email=email,
        password=password,
        empresa=empresa,
        rol=rol,
        **kwargs,
    )


def make_area(empresa, **kwargs):
    from organizacion.models import Area

    n = next(_seq)
    datos = {
        "empresa": empresa,
        "nombre": f"Área {n}",
        "activa": True,
    }
    datos.update(kwargs)
    return Area.objects.create(**datos)


def make_puesto(empresa, **kwargs):
    from organizacion.models import Puesto

    n = next(_seq)
    datos = {
        "empresa": empresa,
        "nombre": f"Puesto {n}",
        "descripcion": "",
        "activo": True,
    }
    datos.update(kwargs)
    return Puesto.objects.create(**datos)


def make_plantilla(empresa, **kwargs):
    from evaluaciones.models import PlantillaEvaluacion

    n = next(_seq)
    datos = {
        "empresa": empresa,
        "nombre": f"Plantilla {n}",
        "tipo": PlantillaEvaluacion.Tipo.MIXTA,
        "descripcion": "",
        "activa": True,
    }
    datos.update(kwargs)
    return PlantillaEvaluacion.objects.create(**datos)


def make_ciclo(empresa, **kwargs):
    from datetime import date, timedelta

    from evaluaciones.models import CicloEvaluacion

    n = next(_seq)
    plantilla_default = kwargs.pop("plantilla_default", None)
    if plantilla_default is None:
        plantilla_default = make_plantilla(empresa)
    datos = {
        "empresa": empresa,
        "nombre": f"Ciclo {n}",
        "fecha_inicio": date.today(),
        "fecha_cierre": date.today() + timedelta(days=30),
        "estado": CicloEvaluacion.Estado.BORRADOR,
        "plantilla_default": plantilla_default,
        "criterios_generales": "",
    }
    datos.update(kwargs)
    return CicloEvaluacion.objects.create(**datos)


def make_evaluacion(ciclo, evaluado, **kwargs):
    from evaluaciones.models import Evaluacion

    plantilla = kwargs.pop("plantilla", None) or ciclo.plantilla_default
    puesto = kwargs.pop("puesto", None) or evaluado.puesto
    if "evaluador" in kwargs:
        evaluador = kwargs.pop("evaluador")
    else:
        evaluador = getattr(evaluado, "supervisor", None)
    sin_evaluador = kwargs.pop("sin_evaluador", evaluador is None)
    datos = {
        "ciclo": ciclo,
        "empresa": ciclo.empresa,
        "evaluado": evaluado,
        "evaluador": evaluador,
        "puesto": puesto,
        "plantilla": plantilla,
        "estado": Evaluacion.Estado.PENDIENTE_AUTO,
        "sin_evaluador": sin_evaluador,
    }
    datos.update(kwargs)
    return Evaluacion.objects.create(**datos)


def make_competencia(empresa, **kwargs):
    from organizacion.models import Competencia

    n = next(_seq)
    datos = {
        "empresa": empresa,
        "nombre": f"Competencia {n}",
        "descripcion": "",
        "tipo": Competencia.Tipo.TECNICA,
        "activa": True,
    }
    datos.update(kwargs)
    return Competencia.objects.create(**datos)
