"""Auth and account endpoints (docs/API_PLAN.md §2). Guest play needs none of these (D-01)."""

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    password_validation,
    update_session_auth_hash,
)
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from casefile.api.exceptions import CasefileAPIError

from . import serializers as s
from .identity import get_player
from .models import profile_for
from .throttles import AuthAccountThrottle, AuthIPThrottle

User = get_user_model()
AUTH_THROTTLES = [AuthIPThrottle, AuthAccountThrottle]


def empty_claim() -> dict:
    """Guest progress moved into the account. Playthroughs (and claiming) arrive in M7."""
    return {"playthroughs": [], "conflicts": []}


def user_payload(user) -> dict:
    return s.UserSerializer(user).data


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Set the CSRF cookie", responses={204: None})
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Current user, guest, or neither", responses={200: s.MeOut})
    def get(self, request):
        player = get_player(request)
        if player.kind == "account":
            return Response({"user": user_payload(player.user), "guest": None})
        if player.kind == "guest":
            guest = {"has_progress": False, "expires_after_days": settings.GUEST_RETENTION_DAYS}
            return Response({"user": None, "guest": guest})
        return Response({"user": None, "guest": None})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = AUTH_THROTTLES

    @extend_schema(
        summary="Create an account and log in",
        request=s.RegisterSerializer,
        responses={201: s.AuthOut},
    )
    def post(self, request):
        data = s.RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        user = User.objects.create_user(v["email"], v["password"], display_name=v["display_name"])
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": user_payload(user), "claimed": empty_claim()}, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = AUTH_THROTTLES

    @extend_schema(summary="Log in", request=s.LoginSerializer, responses={200: s.AuthOut})
    def post(self, request):
        data = s.LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            username=data.validated_data["email"],
            password=data.validated_data["password"],
        )
        if user is None:
            raise CasefileAPIError("invalid_credentials", "That email and password don't match.")
        login(request._request, user)
        return Response({"user": user_payload(user), "claimed": empty_claim()})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Log out", request=None, responses={204: None})
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update display name and preferences",
        request=s.ProfileSerializer,
        responses={200: s.ProfileOut},
    )
    def patch(self, request):
        data = s.ProfileSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        profile = profile_for(request.user)
        if "display_name" in data.validated_data:
            profile.display_name = data.validated_data["display_name"]
        if "preferences" in data.validated_data:
            profile.preferences = {**profile.preferences, **data.validated_data["preferences"]}
        profile.save()
        return Response({"user": user_payload(request.user)})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password", request=s.PasswordChangeSerializer, responses={204: None}
    )
    def post(self, request):
        data = s.PasswordChangeSerializer(data=request.data, context={"user": request.user})
        data.is_valid(raise_exception=True)
        request.user.set_password(data.validated_data["new_password"])
        request.user.save()
        update_session_auth_hash(request._request, request.user)  # stay logged in
        return Response(status=status.HTTP_204_NO_CONTENT)


RESET_ACCEPTED = "If an account exists for that email, we've sent a link to reset the password."


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = AUTH_THROTTLES

    @extend_schema(
        summary="Request a password reset email",
        request=s.PasswordResetSerializer,
        responses={202: s.DetailOut},
    )
    def post(self, request):
        data = s.PasswordResetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=data.validated_data["email"], is_active=True
        ).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            origin = settings.PUBLIC_ORIGIN or request.build_absolute_uri("/").rstrip("/")
            link = f"{origin}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Reset your Casefile password",
                f"Someone asked to reset the password for this Casefile account.\n\n"
                f"Set a new password here: {link}\n\n"
                f"If that wasn't you, you can ignore this email.",
                None,
                [user.email],
            )
        # Same answer either way, so the endpoint can't be used to discover accounts.
        return Response({"detail": RESET_ACCEPTED}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle]

    @extend_schema(
        summary="Set a new password with a reset token",
        request=s.PasswordResetConfirmSerializer,
        responses={204: None},
    )
    def post(self, request):
        data = s.PasswordResetConfirmSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(v["uid"])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, v["token"]):
            raise serializers.ValidationError(
                {"token": "This reset link is invalid or has already been used."}
            )
        try:
            password_validation.validate_password(v["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages}) from exc
        user.set_password(v["new_password"])
        user.save()  # changing the password invalidates the token (single use)
        return Response(status=status.HTTP_204_NO_CONTENT)
