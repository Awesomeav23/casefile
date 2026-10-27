"""Who is making this request: an account holder, a guest, or a visitor (ARCHITECTURE §5, D-01).

- Visitor: no guest ID yet. Browsing never creates one.
- Guest: an anonymous Django session holding a random `guest_id`, created lazily on the first
  write (e.g. starting a playthrough, M7). The session lasts GUEST_RETENTION_DAYS (D-22) and
  is renewed whenever `ensure_guest` runs.
- Account: an authenticated user. A guest ID left in the session is ignored; claiming that
  guest's progress into the account is M7's job (accounts/claim.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings

GUEST_SESSION_KEY = "casefile_guest_id"


def guest_session_age() -> timedelta:
    return timedelta(days=settings.GUEST_RETENTION_DAYS)


@dataclass(frozen=True)
class Player:
    user: object | None = None
    guest_id: uuid.UUID | None = None

    @property
    def kind(self) -> str:
        if self.user is not None:
            return "account"
        return "guest" if self.guest_id else "visitor"

    @property
    def throttle_key(self) -> str | None:
        if self.user is not None:
            return f"user:{self.user.pk}"
        return f"guest:{self.guest_id}" if self.guest_id else None


def _user(request):
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


def get_player(request) -> Player:
    """Read-only: never writes to the session."""
    user = _user(request)
    if user is not None:
        return Player(user=user)
    raw = request.session.get(GUEST_SESSION_KEY)
    try:
        return Player(guest_id=uuid.UUID(raw)) if raw else Player()
    except ValueError:
        return Player()


def ensure_guest(request) -> Player:
    """The current player, creating a guest identity for a visitor. Call only on writes."""
    player = get_player(request)
    if player.kind == "account":
        return player
    if player.kind == "visitor":
        player = Player(guest_id=uuid.uuid4())
        request.session[GUEST_SESSION_KEY] = str(player.guest_id)
    request.session.set_expiry(int(guest_session_age().total_seconds()))
    return player
