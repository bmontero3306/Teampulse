"""Servicios de organigrama y validación de jerarquías (WP3)."""


class JerarquiaCircularError(ValueError):
    """Se intentó asignar un padre/superior que genera un ciclo."""


def _descendientes_alcanzan(origen, objetivo_pk, get_hijos):
    """DFS iterativo: True si objetivo_pk está en el subárbol de origen."""
    if not getattr(origen, "pk", None) or objetivo_pk is None:
        return False
    pila = list(get_hijos(origen))
    vistos = set()
    while pila:
        nodo = pila.pop()
        pk = nodo.pk
        if pk in vistos:
            continue
        vistos.add(pk)
        if pk == objetivo_pk:
            return True
        pila.extend(get_hijos(nodo))
    return False


def validar_jerarquia_puestos(puesto, nuevo_superior):
    """Rechaza ciclos en puesto_superior (DFS sobre hijos)."""
    if nuevo_superior is None:
        return True
    if puesto is not None and getattr(puesto, "pk", None):
        if nuevo_superior.pk == puesto.pk:
            raise JerarquiaCircularError(
                "Un puesto no puede ser superior de sí mismo."
            )
        if _descendientes_alcanzan(
            puesto,
            nuevo_superior.pk,
            lambda n: list(puestos_hijos(n)),
        ):
            raise JerarquiaCircularError(
                "No se puede asignar ese puesto superior porque generaría una referencia circular."
            )
    return True


def validar_jerarquia_areas(area, nuevo_padre):
    """Rechaza ciclos en area_padre (DFS sobre subáreas)."""
    if nuevo_padre is None:
        return True
    if area is not None and getattr(area, "pk", None):
        if nuevo_padre.pk == area.pk:
            raise JerarquiaCircularError("Un área no puede ser padre de sí misma.")
        if _descendientes_alcanzan(
            area,
            nuevo_padre.pk,
            lambda n: list(n.areas_hijas.all()),
        ):
            raise JerarquiaCircularError(
                "No se puede asignar esa área padre porque generaría una referencia circular."
            )
    return True


def puestos_hijos(puesto, solo_activos=False):
    """Puestos que reportan directamente a `puesto`."""
    qs = puesto.puestos_hijos.order_by("nombre")
    if solo_activos:
        qs = qs.filter(activo=True)
    return qs


MENSAJE_SUPERIOR_INACTIVO = "El puesto superior tiene que estar activo."


def mensaje_desactivacion_con_hijos(hijos):
    """Texto para rechazar la baja de un puesto que todavía tiene dependientes."""
    nombres = [
        hijo.nombre if hijo.activo else f"{hijo.nombre} (inactivo)" for hijo in hijos
    ]
    lista = ", ".join(nombres)
    return (
        "No se puede desactivar este puesto porque tiene puestos a cargo: "
        f"{lista}. Reasigná cada uno a otro puesto superior y volvé a intentarlo."
    )


def validar_desactivacion_puesto(puesto):
    """Rechaza desactivar o eliminar un puesto con hijos directos."""
    from django.core.exceptions import ValidationError

    if not getattr(puesto, "pk", None):
        return
    hijos = list(puestos_hijos(puesto))
    if hijos:
        raise ValidationError({"activo": mensaje_desactivacion_con_hijos(hijos)})


def query_organigrama(empresa, *, solo_activos=True, raiz=None):
    """Árbol de puestos: raíces + hijos (atributo `hijos_organigrama`)."""
    from organizacion.models import Puesto

    qs = Puesto.objects.for_empresa(empresa).select_related("area", "puesto_superior")
    if solo_activos:
        qs = qs.filter(activo=True)
    puestos = list(qs.order_by("nombre"))
    by_id = {p.pk: p for p in puestos}
    for p in puestos:
        p.hijos_organigrama = []

    raices = []
    for p in puestos:
        superior_id = p.puesto_superior_id
        if superior_id and superior_id in by_id:
            by_id[superior_id].hijos_organigrama.append(p)
        else:
            raices.append(p)

    if raiz is None:
        return raices
    nodo = by_id.get(getattr(raiz, "pk", raiz))
    return [nodo] if nodo is not None else []
