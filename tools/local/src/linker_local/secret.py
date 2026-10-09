"""Generated passwords."""

from __future__ import annotations

import secrets


def password() -> str:
    """24 characters, the length of the passwords WP-CLI generates (`wp user
    create`, entity-command User_Command), drawn from [A-Za-z0-9_-], so they need
    no quoting in SQL, shell or PHP strings."""
    return secrets.token_urlsafe(18)
