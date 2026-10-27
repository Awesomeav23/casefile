from rest_framework.authentication import SessionAuthentication


class CsrfSessionAuthentication(SessionAuthentication):
    """Session auth that enforces CSRF on every unsafe request, logged in or not.

    DRF's SessionAuthentication only checks CSRF for authenticated users, and DRF views are
    exempt from Django's CSRF middleware. Guests and the login/register forms also ride on
    the session cookie, so they need the same protection (ARCHITECTURE §5).
    """

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.enforce_csrf(request)
        if not user or not user.is_active or not user.is_authenticated:
            return None
        return (user, None)


try:  # describe it in the OpenAPI schema as cookie (session) auth
    from drf_spectacular.authentication import SessionScheme

    class CsrfSessionScheme(SessionScheme):
        target_class = "casefile.api.authentication.CsrfSessionAuthentication"
except ImportError:  # pragma: no cover
    pass
