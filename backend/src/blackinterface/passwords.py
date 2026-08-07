"""Password hashing and session tokens. One module, so there is one thing to audit.

Argon2id through `argon2-cffi`, at the library's own defaults. Two rules, and
they are not negotiable (ADR-0016 section 7):

  * a password is never stored, only its hash
  * nobody writes their own hashing here — not a salt, not an iteration count,
    not "sha256 plus something clever"

Cross-cutting like `errors.py` and `logs.py` rather than part of a layer:
`store/` writes the hash, `api/` checks it, and neither owns the algorithm.

Session tokens are handled differently on purpose. A password is low-entropy
and human-chosen, so it needs a slow hash. A session token is 256 bits from
`secrets`, so a fast digest is enough — the only thing that must not happen is
storing the token itself, because then the database *is* a set of working
credentials.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

#: Long enough that guessing is not a threat model, short enough for a cookie.
_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    """Argon2id, salt included in the returned string."""
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Constant-time as far as the library allows; False for every failure.

    `None` — an account whose identity lives in an external system — can never
    be signed in to with a local password. That is a deliberate closed door, not
    an oversight: half-federated accounts are how a decommissioned identity
    keeps working.

    A malformed hash returns False rather than raising. A corrupted row must
    lock one account out, not take down the login endpoint for everybody.
    """
    if not stored_hash:
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when the hash was made with weaker parameters than today's default."""
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True


def new_session_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """What goes in the database. See the module docstring for why not Argon2."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
