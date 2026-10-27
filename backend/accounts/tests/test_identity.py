"""Player identity: visitor / guest / account (ARCHITECTURE §5, D-01)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from accounts.identity import GUEST_SESSION_KEY, ensure_guest, get_player
from accounts.permissions import IsPlayer

pytestmark = pytest.mark.django_db


class PlayerView(APIView):
    """Stands in for future Player endpoints (M7): reads never create a guest, writes do."""

    permission_classes = [IsPlayer]

    def get(self, request):
        return Response({"kind": get_player(request).kind})

    def post(self, request):
        player = ensure_guest(request)
        return Response({"kind": player.kind, "guest_id": str(player.guest_id or "")})


urlpatterns = [path("player/", PlayerView.as_view())]


@pytest.fixture
def user():
    return get_user_model().objects.create_user("sam@example.com", "a-long-password-1")


@pytest.mark.urls(__name__)
class TestIdentity:
    def test_browsing_creates_no_guest(self):
        client = APIClient()
        assert client.get("/player/").json() == {"kind": "visitor"}
        assert GUEST_SESSION_KEY not in client.session

    def test_first_write_creates_a_guest_with_a_90_day_session(self):
        client = APIClient()
        body = client.post("/player/", {}, format="json").json()
        assert body["kind"] == "guest"
        guest_id = uuid.UUID(body["guest_id"])
        assert client.session[GUEST_SESSION_KEY] == str(guest_id)
        assert 89 * 86400 < client.session.get_expiry_age() <= 90 * 86400
        assert client.get("/player/").json() == {"kind": "guest"}

    def test_guest_id_is_stable_across_writes(self):
        client = APIClient()
        first = client.post("/player/", {}, format="json").json()["guest_id"]
        assert client.post("/player/", {}, format="json").json()["guest_id"] == first

    def test_account_wins_over_a_leftover_guest_id(self, user):
        client = APIClient()
        client.post("/player/", {}, format="json")
        client.force_login(user)
        assert client.get("/player/").json() == {"kind": "account"}
        body = client.post("/player/", {}, format="json").json()
        assert body == {"kind": "account", "guest_id": ""}

    def test_guest_writes_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post("/player/", {}, format="json")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_failed"
