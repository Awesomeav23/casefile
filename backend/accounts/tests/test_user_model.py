import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


@pytest.fixture
def User():
    return get_user_model()


def test_custom_user_model_uses_email_login(User):
    assert User._meta.label == "accounts.User"
    assert User.USERNAME_FIELD == "email"
    assert not hasattr(User, "username")


def test_create_user_normalises_domain_and_hashes_with_argon2(User):
    user = User.objects.create_user("Sam@Example.COM", "a-long-password-1")
    assert user.email == "Sam@example.com"
    assert user.password.startswith("argon2")
    assert user.check_password("a-long-password-1")
    assert user.is_active and not user.is_staff and not user.is_superuser
    assert str(user) == "Sam@example.com"


def test_create_user_requires_email(User):
    with pytest.raises(ValueError):
        User.objects.create_user("", "a-long-password-1")


def test_create_superuser(User):
    admin = User.objects.create_superuser("admin@example.com", "a-long-password-1")
    assert admin.is_staff and admin.is_superuser
    with pytest.raises(ValueError):
        User.objects.create_superuser("x@example.com", "pw-123456789", is_staff=False)


def test_email_unique_case_insensitively(User):
    User.objects.create_user("sam@example.com", "a-long-password-1")
    with pytest.raises(IntegrityError):
        User.objects.create_user("SAM@example.com", "a-long-password-1")


def test_natural_key_lookup_is_case_insensitive(User):
    user = User.objects.create_user("sam@example.com", "a-long-password-1")
    assert User.objects.get_by_natural_key("SAM@EXAMPLE.COM") == user
