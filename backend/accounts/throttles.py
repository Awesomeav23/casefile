"""Rate limits for login, register and password reset (API_PLAN §10).

Counts live in Django's cache (process-local in v1.0; the deployment milestone M20 decides
whether a shared cache is needed when running several workers).
"""

from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class _LiveRateThrottle(SimpleRateThrottle):
    """Reads the rate at request time (DRF copies it at import), so settings overrides apply."""

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class AuthIPThrottle(_LiveRateThrottle):
    scope = "auth_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class AuthAccountThrottle(_LiveRateThrottle):
    """Per email address, so spreading guesses across IPs doesn't help."""

    scope = "auth_account"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request, "data") else None
        if not isinstance(email, str) or not email.strip():
            return None
        return self.cache_format % {"scope": self.scope, "ident": email.strip().lower()}
