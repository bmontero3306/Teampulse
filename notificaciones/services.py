import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from notificaciones.events import resolver_contenido
from notificaciones.models import Notificacion

logger = logging.getLogger("notificaciones")


def notificar(tipo=None, usuario=None, titulo="", mensaje="", url="", empresa=None, **kwargs):
    """Crea una notificación in-app y envía email. Nunca relanza errores de mail.

    Firma principal: notificar(tipo, usuario, titulo, mensaje, url, empresa).
    También acepta evento= y contexto= (plan §8): resuelve título/mensaje en events.py.
    Si el tercer argumento posicional es un dict, se trata como contexto.
    """
    evento = kwargs.pop("evento", None)
    contexto = kwargs.pop("contexto", None)
    if isinstance(titulo, dict) and contexto is None:
        contexto = titulo
        titulo = ""
    tipo = evento or tipo
    if usuario is None or not tipo:
        logger.warning("notificar omitido: falta usuario o tipo.")
        return None

    empresa = empresa or getattr(usuario, "empresa", None)
    contexto = dict(contexto or {})
    plantilla_titulo, plantilla_mensaje, plantilla_url = resolver_contenido(tipo, contexto)
    titulo = titulo or plantilla_titulo or "Notificación TeamPulse"
    mensaje = mensaje or plantilla_mensaje or ""
    url = url or plantilla_url or ""

    notificacion = Notificacion.objects.create(
        empresa=empresa,
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        url=url,
        leida=False,
        email_enviado=False,
    )
    _enviar_email(notificacion, usuario)
    return notificacion


def _enviar_email(notificacion, usuario):
    destinatario = getattr(usuario, "email", "") or ""
    if not destinatario:
        logger.warning(
            "Notificación %s sin email de destinatario; email_enviado=False.",
            notificacion.pk,
        )
        return
    contexto = {
        "notificacion": notificacion,
        "usuario": usuario,
        "titulo": notificacion.titulo,
        "mensaje": notificacion.mensaje,
        "url": notificacion.url,
    }
    try:
        texto = render_to_string("notificaciones/email/notificacion.txt", contexto)
        html = render_to_string("notificaciones/email/notificacion.html", contexto)
        correo = EmailMultiAlternatives(
            subject=notificacion.titulo,
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        correo.attach_alternative(html, "text/html")
        enviados = correo.send()
        if enviados:
            notificacion.email_enviado = True
            notificacion.save(update_fields=["email_enviado"])
        else:
            logger.warning(
                "El backend no envió el email de la notificación %s.",
                notificacion.pk,
            )
    except Exception as exc:
        logger.error(
            "Falló el envío de email de la notificación %s: %s. email_enviado=False.",
            notificacion.pk,
            exc,
        )


def _queryset_usuario(request):
    qs = Notificacion.objects.de_usuario(request.user)
    empresa = getattr(request, "empresa", None)
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    return qs
