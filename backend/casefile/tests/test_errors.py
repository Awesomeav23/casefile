"""Every non-2xx API response uses the error envelope (ARCHITECTURE §6, API_PLAN §9)."""

import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.urls import path
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from casefile.api.exceptions import CasefileAPIError

# --- Test-only views, mounted via @pytest.mark.urls(__name__) -----------------------------


class _NameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=5)


class ValidationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        _NameSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({"ok": True})


class PrivateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"ok": True})

    def post(self, request):
        return Response({"ok": True})


class RaisingView(APIView):
    permission_classes = [AllowAny]
    exc = None

    def get(self, request):
        raise self.exc


urlpatterns = [
    path("validate/", ValidationView.as_view()),
    path("private/", PrivateView.as_view()),
    path(
        "custom/",
        RaisingView.as_view(
            exc=CasefileAPIError("action_unavailable", "That isn't available.", status_code=422)
        ),
    ),
    path("forbidden/", RaisingView.as_view(exc=PermissionDenied())),
    path("throttled/", RaisingView.as_view(exc=Throttled(wait=30))),
    path("missing/", RaisingView.as_view(exc=Http404("secret internal detail"))),
    path("boom/", RaisingView.as_view(exc=RuntimeError("secret internal detail"))),
]


def assert_envelope(response, status, code):
    assert response.status_code == status, response.content
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    return body["error"]


# --- Tests ----------------------------------------------------------------------------------


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.urls(__name__)
class TestEnvelope:
    def test_validation_error_has_field_details(self, client):
        error = assert_envelope(
            client.post("/validate/", {"name": "far too long"}, format="json"),
            400,
            "validation_error",
        )
        assert "name" in error["details"]

    def test_malformed_json(self, client):
        response = client.post("/validate/", data="{not json", content_type="application/json")
        assert_envelope(response, 400, "malformed_request")

    def test_unsupported_media_type(self, client):
        response = client.post("/validate/", data="name=x", content_type="text/plain")
        assert_envelope(response, 415, "unsupported_media_type")

    def test_not_authenticated_is_401(self, client):
        assert_envelope(client.get("/private/"), 401, "not_authenticated")

    def test_method_not_allowed(self, client):
        assert_envelope(client.delete("/validate/"), 405, "method_not_allowed")

    def test_permission_denied(self, client):
        assert_envelope(client.get("/forbidden/"), 403, "permission_denied")

    def test_throttled(self, client):
        error = assert_envelope(client.get("/throttled/"), 429, "rate_limited")
        assert error["details"]["retry_after_seconds"] == 30

    def test_http404_does_not_leak_detail(self, client):
        error = assert_envelope(client.get("/missing/"), 404, "not_found")
        assert "secret" not in error["message"]

    def test_custom_casefile_error(self, client):
        error = assert_envelope(client.get("/custom/"), 422, "action_unavailable")
        assert error["message"] == "That isn't available."

    def test_unhandled_exception_is_generic_500(self, client):
        error = assert_envelope(client.get("/boom/"), 500, "server_error")
        assert "secret" not in error["message"]
        assert error["details"] == {}

    @pytest.mark.django_db
    def test_csrf_failure(self):
        user = get_user_model().objects.create_user("sam@example.com", "a-long-password-1")
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        assert_envelope(csrf_client.post("/private/", {}, format="json"), 403, "csrf_failed")


def test_unknown_api_route_uses_envelope(client):
    assert_envelope(client.get("/api/v1/does-not-exist/"), 404, "not_found")
