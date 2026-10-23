from django.db import DatabaseError, connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import CasefileAPIError, error_payload


def check_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


class HealthView(APIView):
    """Liveness + database check, used by Render health checks and CI smoke tests."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Service health",
        responses=inline_serializer(
            "Health",
            fields={"status": serializers.CharField(), "database": serializers.CharField()},
        ),
    )
    def get(self, request):
        try:
            check_database()
        except DatabaseError as exc:
            raise CasefileAPIError(
                "service_unavailable",
                "The service is temporarily unavailable.",
                status_code=503,
                details={"database": "unavailable"},
            ) from exc
        return Response({"status": "ok", "database": "ok"})


def api_not_found(request, *args, **kwargs):
    """Catch-all for unknown /api/ routes, so they get the envelope instead of an HTML page."""
    return JsonResponse(error_payload("not_found", "Not found."), status=404)


def api_server_error(request, *args, **kwargs):
    """handler500: JSON envelope for /api/ paths, Django's default page elsewhere."""
    if request.path.startswith("/api/"):
        payload = error_payload("server_error", "Something went wrong on our side.")
        return JsonResponse(payload, status=500)
    from django.views.defaults import server_error

    return server_error(request)
