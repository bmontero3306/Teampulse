from django.db import models


def for_empresa(queryset, empresa):
    """Filtra un queryset de negocio por la empresa del request."""
    if empresa is None:
        return queryset.none()
    return queryset.filter(empresa=empresa)


class EmpresaQuerySet(models.QuerySet):
    def for_empresa(self, empresa):
        return for_empresa(self, empresa)


class EmpresaManager(models.Manager.from_queryset(EmpresaQuerySet)):
    pass
