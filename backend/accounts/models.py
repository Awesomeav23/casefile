from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        display_name = extra_fields.pop("display_name", None)
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        PlayerProfile.objects.create(
            user=user, display_name=display_name or default_display_name(email)
        )
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Emails are unique case-insensitively, so log-in matches them that way too.
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin):
    """Account holder. Accounts are optional (D-01); guests have no row here."""

    # unique=True satisfies Django's USERNAME_FIELD check; the Lower() constraint below
    # adds the real rule: emails are unique case-insensitively (DATA_MODEL §2).
    email = models.EmailField(max_length=254, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self):
        return self.email


def default_preferences() -> dict:
    return {"text_scale": 1, "reduced_motion": False, "theme": "dark", "show_tips": True}


def default_display_name(email: str) -> str:
    return email.split("@")[0][:40] or "Detective"


class PlayerProfile(models.Model):
    """Display name and preferences for an account holder (guests keep these in the browser)."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="profile"
    )
    display_name = models.CharField(max_length=40)
    preferences = models.JSONField(default=default_preferences)

    def __str__(self):
        return self.display_name


def profile_for(user: User) -> PlayerProfile:
    """The user's profile, created on first use for accounts made without one."""
    profile, _ = PlayerProfile.objects.get_or_create(
        user=user, defaults={"display_name": default_display_name(user.email)}
    )
    return profile
