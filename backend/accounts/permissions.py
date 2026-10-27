from rest_framework.permissions import BasePermission


class IsPlayer(BasePermission):
    """Account holders and guests (D-01). Visitors may read, and a write makes them a guest
    via `ensure_guest`, so nobody is ever asked to sign up to play."""

    def has_permission(self, request, view):
        return True
