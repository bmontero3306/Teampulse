from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler

from evaluaciones.exceptions import EvaluacionesError


def api_exception_handler(exc, context):
    if isinstance(exc, EvaluacionesError):
        exc = DRFValidationError({"detail": str(exc)})
    elif isinstance(exc, DjangoValidationError):
        if getattr(exc, "message_dict", None):
            exc = DRFValidationError(exc.message_dict)
        elif getattr(exc, "error_dict", None):
            exc = DRFValidationError(exc.message_dict)
        else:
            exc = DRFValidationError({"detail": exc.messages})
    return exception_handler(exc, context)
