"""Rutas de la SPA. Si el nombre Django ya no existe, usa el path de Angular."""

from django.urls import NoReverseMatch, reverse


def ruta(nombre, fallback, args=None):
    try:
        return reverse(nombre, args=args) if args else reverse(nombre)
    except NoReverseMatch:
        return fallback
