"""Encrypting the one secret this product stores: the model's API key.

What this protects against
--------------------------
Somebody who obtains a copy of the SQLite file — a backup, a support bundle, a
laptop taken off site — cannot read the key out of it. That is a real and common
way keys leak, and it is worth closing.

What it does not protect against
--------------------------------
Somebody with shell access on the running machine. The process must be able to
decrypt the key in order to use it, so `BI_SECRET_KEY` is in its environment. If
that variable is set in a file sitting next to the database, this moves the
secret; it does not remove it. Say so plainly rather than letting the word
"encrypted" do work it cannot do.

The trade the operator is making
--------------------------------
**Lose `BI_SECRET_KEY` and the stored key is gone** — it must be entered again.
Nothing else in the database depends on it, so that is the whole cost. The
alternative, deriving the key from something already on disk, would be
decoration.

`BI_SECRET_KEY` must be random, not a chosen password. The derivation below is a
single hash, which is right for a high-entropy secret and useless against a
guessable one. Generate one with:

    python -c "import secrets; print(secrets.token_urlsafe(32))"
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from blackinterface.errors import ConfigurationError
from blackinterface.logs import get_logger

log = get_logger(__name__)


class SecretsUnavailableError(ConfigurationError):
    """`BI_SECRET_KEY` is not set, so nothing can be sealed or opened."""


def _fernet(secret: str) -> Fernet:
    if not secret:
        raise SecretsUnavailableError(
            "BI_SECRET_KEY is not set, so the API key cannot be stored",
            hint='generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"',
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(plaintext: str, secret: str) -> bytes:
    """Encrypt a secret for storage. Raises when there is no `BI_SECRET_KEY`."""
    return _fernet(secret).encrypt(plaintext.encode("utf-8"))


def unseal(token: bytes | None, secret: str) -> str | None:
    """Decrypt a stored secret.

    Returns `None` for a token this key cannot open — which is what a rotated or
    forgotten `BI_SECRET_KEY` looks like. Deliberately not an exception: the
    caller's honest response is "there is no usable key, the assistant is off",
    the same response as never having set one. Logged, because silently behaving
    as if a configured assistant were unconfigured would be baffling.
    """
    if token is None:
        return None
    try:
        return _fernet(secret).decrypt(token).decode("utf-8")
    except SecretsUnavailableError:
        log.warning("assistant_key_unreadable", reason="BI_SECRET_KEY not set")
        return None
    except InvalidToken:
        log.warning("assistant_key_unreadable", reason="BI_SECRET_KEY does not match")
        return None
