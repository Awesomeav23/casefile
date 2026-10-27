from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from .models import profile_for

User = get_user_model()

TEXT_SCALES = (1, 1.15, 1.3)
THEMES = ("dark",)  # a light theme is open decision D-08


class UserSerializer(serializers.Serializer):
    """The `user` object in auth responses (API_PLAN §2)."""

    def to_representation(self, user):
        profile = profile_for(user)
        return {
            "id": user.id,
            "email": user.email,
            "display_name": profile.display_name,
            "is_staff": user.is_staff,
            "preferences": profile.preferences,
        }


def _strong_password(value, email=""):
    password_validation.validate_password(value, User(email=email))
    return value


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=40)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        try:
            _strong_password(attrs["password"], attrs["email"])
        except Exception as exc:  # django ValidationError → DRF field error
            raise serializers.ValidationError(
                {"password": list(getattr(exc, "messages", [str(exc)]))}
            ) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class PreferencesSerializer(serializers.Serializer):
    text_scale = serializers.ChoiceField(choices=TEXT_SCALES, required=False)
    reduced_motion = serializers.BooleanField(required=False)
    theme = serializers.ChoiceField(choices=THEMES, required=False)
    show_tips = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields) if isinstance(data, dict) else set()
        if unknown:
            raise serializers.ValidationError({k: "Unknown preference." for k in sorted(unknown)})
        if (
            isinstance(data, dict)
            and "reduced_motion" in data
            and not isinstance(data["reduced_motion"], bool)
        ):
            raise serializers.ValidationError({"reduced_motion": "Must be true or false."})
        return super().to_internal_value(data)


class ProfileSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=40, required=False)
    preferences = PreferencesSerializer(required=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("That isn't your current password.")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context["user"])
        return value


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False)


# --- response shapes (for the OpenAPI schema and generated frontend types) ------------------


class PreferencesOut(serializers.Serializer):
    text_scale = serializers.FloatField()
    reduced_motion = serializers.BooleanField()
    theme = serializers.CharField()
    show_tips = serializers.BooleanField()


class UserOut(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    is_staff = serializers.BooleanField()
    preferences = PreferencesOut()


class GuestOut(serializers.Serializer):
    has_progress = serializers.BooleanField()
    expires_after_days = serializers.IntegerField()


class MeOut(serializers.Serializer):
    user = UserOut(allow_null=True)
    guest = GuestOut(allow_null=True)


class ClaimedPlaythroughOut(serializers.Serializer):
    id = serializers.UUIDField()
    case = serializers.CharField()
    status = serializers.CharField()


class ClaimConflictOut(serializers.Serializer):
    case = serializers.CharField()
    kept = serializers.UUIDField()
    abandoned = serializers.UUIDField()


class ClaimedOut(serializers.Serializer):
    playthroughs = ClaimedPlaythroughOut(many=True)
    conflicts = ClaimConflictOut(many=True)


class AuthOut(serializers.Serializer):
    user = UserOut()
    claimed = ClaimedOut()


class ProfileOut(serializers.Serializer):
    user = UserOut()


class DetailOut(serializers.Serializer):
    detail = serializers.CharField()
