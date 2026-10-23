"""The API error envelope (docs/ARCHITECTURE.md §6, docs/API_PLAN.md §9).

Every non-2xx response is:
    {"error": {"code": "<stable code>", "message": "<human message>", "details": {...}}}
"""

import logging
import math

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)


class CasefileAPIError(drf.APIException):
    """Raise from services/views for a documented error code, e.g. `action_unavailable`."""

    def __init__(self, code, message, *, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        self.status_code = status_code
        self.error_code = code
        self.message = message
        self.details = details or {}
        super().__init__(detail=message, code=code)


def error_payload(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _classify(exc):
    """Map a DRF exception to (status, code, message, details)."""
    if isinstance(exc, drf.ValidationError):
        details = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        return 400, "validation_error", "Some fields are invalid.", details
    if isinstance(exc, drf.ParseError):
        return 400, "malformed_request", "The request body couldn't be read.", {}
    if isinstance(exc, drf.NotAuthenticated | drf.AuthenticationFailed):
        # DRF answers 403 for session auth; the API contract says 401.
        return 401, "not_authenticated", "You need to log in to do that.", {}
    if isinstance(exc, drf.PermissionDenied):
        if str(exc.detail).startswith("CSRF Failed"):
            return (
                403,
                "csrf_failed",
                "Your security token is missing or out of date. Refresh the page and try again.",
                {},
            )
        return 403, "permission_denied", "You don't have permission to do that.", {}
    if isinstance(exc, drf.NotFound):
        return 404, "not_found", "Not found.", {}
    if isinstance(exc, drf.MethodNotAllowed):
        return 405, "method_not_allowed", "That method isn't allowed here.", {}
    if isinstance(exc, drf.NotAcceptable):
        return 406, "not_acceptable", "This API only returns JSON.", {}
    if isinstance(exc, drf.UnsupportedMediaType):
        return 415, "unsupported_media_type", "Send the request body as JSON.", {}
    if isinstance(exc, drf.Throttled):
        wait = math.ceil(exc.wait) if exc.wait is not None else None
        details = {"retry_after_seconds": wait} if wait is not None else {}
        return 429, "rate_limited", "Too many requests. Please wait a moment.", details
    return exc.status_code, exc.default_code, "The request couldn't be completed.", {}


def exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: render every error in the envelope."""
    if isinstance(exc, Http404):
        exc = drf.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf.PermissionDenied()

    if isinstance(exc, CasefileAPIError):
        status_code = exc.status_code
        body = error_payload(exc.error_code, exc.message, exc.details)
    elif isinstance(exc, drf.APIException):
        status_code, code, message, details = _classify(exc)
        body = error_payload(code, message, details)
    else:
        view = context.get("view")
        logger.exception("Unhandled API error in %s", type(view).__name__ if view else "?")
        status_code = 500
        body = error_payload("server_error", "Something went wrong on our side.")

    set_rollback()
    response = Response(body, status=status_code)
    if status_code == 429 and body["error"]["details"].get("retry_after_seconds") is not None:
        response["Retry-After"] = str(body["error"]["details"]["retry_after_seconds"])
    return response
