import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = get_user_model().objects.create_superuser("admin@example.com", "a-long-password-1")
    client.force_login(admin)
    return client, admin


@pytest.mark.parametrize("url", ["/admin/accounts/user/", "/admin/accounts/user/add/"])
def test_user_admin_pages_load(admin_client, url):
    client, _ = admin_client
    assert client.get(url).status_code == 200


def test_user_admin_change_page_loads(admin_client):
    client, admin = admin_client
    assert client.get(f"/admin/accounts/user/{admin.pk}/change/").status_code == 200
