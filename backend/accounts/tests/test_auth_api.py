"""Auth and account endpoints (API_PLAN §2; TESTING_PLAN §4)."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.identity import GUEST_SESSION_KEY
from accounts.models import PlayerProfile

pytestmark = pytest.mark.django_db
PASSWORD = "a-long-password-1"


@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    return get_user_model().objects.create_user("sam@example.com", PASSWORD, display_name="Sam")


@pytest.fixture
def account(user):
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def guest():
    client = APIClient()
    session = client.session
    session[GUEST_SESSION_KEY] = "0d6c8f3e-6c3a-4a0e-9a35-1b9d4c1f0e21"
    session.save()
    return client


def error(response):
    return response.json()["error"]


# --- csrf / me -------------------------------------------------------------------------


def test_csrf_endpoint_sets_the_cookie():
    response = APIClient().get("/api/v1/auth/csrf/")
    assert response.status_code == 204
    assert "csrftoken" in response.cookies


def test_me_for_a_visitor():
    assert APIClient().get("/api/v1/auth/me/").json() == {"user": None, "guest": None}


def test_me_for_a_guest(guest):
    assert guest.get("/api/v1/auth/me/").json() == {
        "user": None,
        "guest": {"has_progress": False, "expires_after_days": 90},
    }


def test_me_for_an_account(account, user):
    body = account.get("/api/v1/auth/me/").json()
    assert body["guest"] is None
    assert body["user"] == {
        "id": user.id,
        "email": "sam@example.com",
        "display_name": "Sam",
        "is_staff": False,
        "preferences": {
            "text_scale": 1,
            "reduced_motion": False,
            "theme": "dark",
            "show_tips": True,
        },
    }


# --- register ----------------------------------------------------------------------------


def register(client, **overrides):
    data = {"email": "new@example.com", "password": PASSWORD, "display_name": "Nova"} | overrides
    return client.post("/api/v1/auth/register/", data, format="json")


def test_register_creates_account_and_profile_and_logs_in():
    client = APIClient()
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["display_name"] == "Nova"
    assert body["claimed"] == {"playthroughs": [], "conflicts": []}
    assert PlayerProfile.objects.get(user__email="new@example.com").display_name == "Nova"
    assert client.get("/api/v1/auth/me/").json()["user"]["email"] == "new@example.com"


def test_register_rejects_duplicate_email_case_insensitively(user):
    response = register(APIClient(), email="SAM@example.com")
    assert response.status_code == 400
    assert error(response)["code"] == "validation_error"
    assert "email" in error(response)["details"]


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"password": "short"}, "password"),
        ({"password": "new@example.com"}, "password"),
        ({"email": "not-an-email"}, "email"),
        ({"display_name": ""}, "display_name"),
        ({"display_name": "x" * 41}, "display_name"),
    ],
)
def test_register_validation(overrides, field):
    response = register(APIClient(), **overrides)
    assert response.status_code == 400
    assert field in error(response)["details"]


# --- login / logout ---------------------------------------------------------------------


def login(client, email="sam@example.com", password=PASSWORD, **extra):
    return client.post(
        "/api/v1/auth/login/", {"email": email, "password": password}, format="json", **extra
    )


def test_login_succeeds_case_insensitively(user):
    client = APIClient()
    response = login(client, email="Sam@Example.com")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "sam@example.com"
    assert response.json()["claimed"] == {"playthroughs": [], "conflicts": []}
    assert client.get("/api/v1/auth/me/").json()["user"] is not None


@pytest.mark.parametrize(
    "email, password", [("sam@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)]
)
def test_login_failure_is_generic(user, email, password):
    response = login(APIClient(), email=email, password=password)
    assert response.status_code == 400
    assert error(response)["code"] == "invalid_credentials"


def test_inactive_user_cannot_log_in(user):
    user.is_active = False
    user.save()
    assert error(login(APIClient()))["code"] == "invalid_credentials"


def test_logout(account):
    assert account.post("/api/v1/auth/logout/").status_code == 204
    assert account.get("/api/v1/auth/me/").json() == {"user": None, "guest": None}


# --- profile and password ----------------------------------------------------------------


def test_profile_update_merges_preferences(account):
    response = account.patch(
        "/api/v1/me/profile/",
        {"display_name": "Samira", "preferences": {"text_scale": 1.3}},
        format="json",
    )
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["display_name"] == "Samira"
    assert user["preferences"] == {
        "text_scale": 1.3,
        "reduced_motion": False,
        "theme": "dark",
        "show_tips": True,
    }


@pytest.mark.parametrize(
    "preferences", [{"text_scale": 2}, {"theme": "neon"}, {"reduced_motion": "yes"}, {"volume": 3}]
)
def test_profile_rejects_invalid_preferences(account, preferences):
    response = account.patch("/api/v1/me/profile/", {"preferences": preferences}, format="json")
    assert response.status_code == 400


def test_password_change(account, user):
    wrong = account.post(
        "/api/v1/me/password/",
        {"current_password": "nope", "new_password": "another-long-pass-2"},
        format="json",
    )
    assert wrong.status_code == 400 and "current_password" in error(wrong)["details"]
    ok = account.post(
        "/api/v1/me/password/",
        {"current_password": PASSWORD, "new_password": "another-long-pass-2"},
        format="json",
    )
    assert ok.status_code == 204
    assert account.get("/api/v1/auth/me/").json()["user"] is not None  # still logged in
    assert login(APIClient(), password="another-long-pass-2").status_code == 200


# --- password reset ----------------------------------------------------------------------


def test_reset_request_gives_the_same_answer_for_unknown_emails(user):
    unknown = APIClient().post(
        "/api/v1/auth/password-reset/", {"email": "ghost@example.com"}, format="json"
    )
    known = APIClient().post(
        "/api/v1/auth/password-reset/", {"email": "sam@example.com"}, format="json"
    )
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["sam@example.com"]


def test_reset_link_sets_a_new_password(user):
    APIClient().post(
        "/api/v1/auth/password-reset/",
        {"email": "sam@example.com"},
        format="json",
        HTTP_HOST="localhost",
    )
    link = re.search(r"http\S+/reset-password\?uid=(\S+)&token=(\S+)", mail.outbox[0].body)
    assert link, mail.outbox[0].body
    uid, token = link.groups()
    bad = APIClient().post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": "bad-token", "new_password": "brand-new-pass-3"},
        format="json",
    )
    assert bad.status_code == 400 and "token" in error(bad)["details"]
    ok = APIClient().post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "brand-new-pass-3"},
        format="json",
    )
    assert ok.status_code == 204
    assert login(APIClient(), password="brand-new-pass-3").status_code == 200
    reused = APIClient().post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "brand-new-pass-4"},
        format="json",
    )
    assert reused.status_code == 400  # tokens are single-use


# --- throttling and CSRF ------------------------------------------------------------------


def test_login_is_rate_limited_per_ip(user, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"auth_ip": "2/min", "auth_account": "100/min"},
    }
    client = APIClient()
    assert [login(client, password="x").status_code for _ in range(3)] == [400, 400, 429]
    assert error(login(client))["code"] == "rate_limited"


def test_login_is_rate_limited_per_account_across_ips(user, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"auth_ip": "100/min", "auth_account": "2/min"},
    }
    codes = [
        login(APIClient(), password="x", REMOTE_ADDR=f"10.0.0.{i}").status_code for i in range(3)
    ]
    assert codes == [400, 400, 429]


def test_login_requires_csrf():
    client = APIClient(enforce_csrf_checks=True)
    assert error(login(client))["code"] == "csrf_failed"


def test_login_works_with_the_csrf_token(user):
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    assert login(client, HTTP_X_CSRFTOKEN=token).status_code == 200


# --- permission matrix -------------------------------------------------------------------

STAFF = "staff"
ENDPOINTS = [
    ("get", "/api/v1/auth/csrf/", {"visitor": 204, "guest": 204, "account": 204, STAFF: 204}),
    ("get", "/api/v1/auth/me/", {"visitor": 200, "guest": 200, "account": 200, STAFF: 200}),
    ("post", "/api/v1/auth/logout/", {"visitor": 401, "guest": 401, "account": 204, STAFF: 204}),
    ("patch", "/api/v1/me/profile/", {"visitor": 401, "guest": 401, "account": 200, STAFF: 200}),
    ("post", "/api/v1/me/password/", {"visitor": 401, "guest": 401, "account": 400, STAFF: 400}),
]


@pytest.mark.parametrize("method, url, expected", ENDPOINTS, ids=[e[1] for e in ENDPOINTS])
@pytest.mark.parametrize("who", ["visitor", "guest", "account", STAFF])
def test_permission_matrix(method, url, expected, who, user, guest):
    client = {"visitor": APIClient(), "guest": guest}.get(who) or APIClient()
    if who in ("account", STAFF):
        if who == STAFF:
            user.is_staff = True
            user.save()
        client.force_login(user)
    response = getattr(client, method)(url, {}, format="json")
    assert response.status_code == expected[who], response.content
