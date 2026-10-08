from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse


def spa(request, path=""):
    """Sirve el build de Angular. Las rutas de la app caen en index.html."""
    root = Path(settings.SPA_ROOT)
    if path:
        candidato = (root / path).resolve()
        if candidato.is_relative_to(root.resolve()) and candidato.is_file():
            return FileResponse(candidato.open("rb"))
    index = root / "index.html"
    if not index.is_file():
        return HttpResponse(
            "El frontend no está compilado. En frontend/: pnpm install && pnpm build.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
