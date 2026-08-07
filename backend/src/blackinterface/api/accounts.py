"""Identity: who is signed in, and how an account comes to exist (ADR-0017).

Sits between `store/users.py` (rows) and `api/authz.py` (the gate). It is the
only module that turns a request into a `Principal`, which is why signing in,
signing out and seeding all live here rather than in a router — a router should
read as a list of what the API offers.

Roles arrive from the database as strings and are validated on the way in. A
role nobody recognises is dropped, not honoured: a row edited by hand, or left
behind by an older version, must not be able to invent a permission.
"""

from __future__ import annotations

from fastapi import Request, Response

from blackinterface.api import deps
from blackinterface.config import Settings, get_settings
from blackinterface.domain.authz import (
    ANONYMOUS,
    Principal,
    Role,
    build_principal,
    check_role_set,
    parse_roles,
)
from blackinterface.errors import ConfigurationError, InvalidInputError
from blackinterface.logs import get_logger
from blackinterface.passwords import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from blackinterface.store.users import UserRepository, UserRow

log = get_logger(__name__)

#: One account per role, created on a database that has none, so a fresh
#: install can be signed in to at all. The last one is deliberate: it is the
#: lightly-manned station of ADR-0016 section 1, where one person covers several
#: jobs, and it exists so that arrangement is exercised rather than assumed.
#:
#: Note what is *not* here: no account combines `engineer` with a role that can
#: sign an operation. `check_role_set` would refuse to build it.
SEEDS: tuple[tuple[str, str, tuple[Role, ...]], ...] = (
    ("operator", "Vận hành viên", (Role.OPERATOR,)),
    ("supervisor", "Trạm trưởng", (Role.SUPERVISOR,)),
    ("maintenance", "Kỹ thuật viên", (Role.MAINTENANCE,)),
    ("protection", "Kỹ sư bảo vệ", (Role.PROTECTION,)),
    ("admin", "Quản trị", (Role.ADMIN,)),
    ("engineer", "Kỹ sư hệ thống", (Role.ENGINEER,)),
    ("truc", "Trực trạm ít người", (Role.OPERATOR, Role.SUPERVISOR, Role.MAINTENANCE)),
)


def users() -> UserRepository:
    """Built per call over the current database — see `deps.py` for why."""
    return UserRepository(deps.get_database())


# ------------------------------------------------------------------- identity


def principal_of(user: UserRow) -> Principal:
    """A stored account as a set of permissions.

    Unknown role names are dropped with a warning rather than raising: one bad
    row should cost that account its extra role, not lock everybody out of a
    station. `check_role_set` still applies, so a combination the ADR forbids
    cannot be smuggled in by editing the database.
    """
    known: list[Role] = []
    for name in user.roles:
        try:
            known.append(Role(name))
        except ValueError:
            log.warning("unknown role ignored", user=user.username, role=name)
    try:
        check_role_set(known)
    except ValueError as exc:
        log.error(
            "illegal role combination; treating as no roles", user=user.username, error=str(exc)
        )
        known = []
    return build_principal(user.username, known, user.display_name)


def env_principal(settings: Settings) -> Principal:
    """The single principal of `BI_AUTH=env`. Raises on a bad `BI_ROLE`.

    Failing at startup is the point: a typo that quietly fell back to some
    default would hand out permissions nobody chose.
    """
    try:
        roles = parse_roles(settings.role)
    except ValueError as exc:
        raise ConfigurationError(f"BI_ROLE is not usable: {exc}", role=settings.role) from exc
    if not roles:
        raise ConfigurationError("BI_ROLE is empty; name at least one role", role=settings.role)
    return build_principal(settings.user, roles)


def resolve(request: Request) -> Principal:
    """Turn a request into a caller. `ANONYMOUS` when nobody is signed in.

    Never falls back to a default role when a session is missing or expired:
    that fallback is how "the login broke" silently becomes "everyone is an
    operator".
    """
    settings = get_settings()
    if settings.auth == "env":
        return env_principal(settings)

    token = request.cookies.get(settings.session_cookie)
    if not token:
        return ANONYMOUS
    user = users().user_for_session(hash_session_token(token))
    return principal_of(user) if user is not None else ANONYMOUS


# ------------------------------------------------------------ sign in and out


def sign_in(username: str, password: str, response: Response) -> Principal:
    """Verify a password, start a session, set the cookie.

    One error for every failure — unknown account, wrong password, disabled
    account — and the password is verified even when the account does not
    exist. Both are on purpose: a login that answers faster, or differently, for
    a real username tells an attacker which names to keep trying.
    """
    settings = get_settings()
    if settings.auth != "session":
        raise InvalidInputError(
            "this installation does not use sign-in; identity comes from BI_ROLE",
            auth=settings.auth,
        )

    repo = users()
    user = repo.get_by_username(username.strip())
    stored = user.password_hash if user is not None else None
    ok = verify_password(password, stored)
    if user is None or not ok or not user.enabled:
        log.warning("sign-in refused", username=username)
        raise InvalidInputError("tên đăng nhập hoặc mật khẩu không đúng")

    token = new_session_token()
    repo.start_session(user.id, hash_session_token(token), ttl_hours=settings.session_hours)
    response.set_cookie(
        settings.session_cookie,
        token,
        max_age=int(settings.session_hours * 3600),
        httponly=True,  # unreadable from JavaScript, so an XSS cannot lift it
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    log.info("signed in", user=user.username, roles=list(user.roles))
    return principal_of(user)


def sign_out(request: Request, response: Response) -> None:
    """Drop the session server-side, then clear the cookie.

    That order matters: deleting only the cookie would leave a session that
    still works to anyone who kept the token.
    """
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie)
    if token:
        users().end_session(hash_session_token(token))
    response.delete_cookie(settings.session_cookie, path="/")


def change_password(principal: Principal, current: str, new: str) -> None:
    repo = users()
    user = repo.get_by_username(principal.user)
    if user is None or not verify_password(current, user.password_hash):
        raise InvalidInputError("mật khẩu hiện tại không đúng")
    if len(new) < 8:
        raise InvalidInputError("mật khẩu mới phải dài ít nhất 8 ký tự")
    repo.set_password(user.id, hash_password(new))
    log.info("password changed", user=user.username)


# -------------------------------------------------------------------- seeding


def seed_default_accounts(settings: Settings) -> list[str]:
    """Create the starter accounts, but only on a database that has none.

    Guarded by the count rather than by per-username checks: once an
    administrator has taken over account management, this must not quietly put
    back an account they deleted.
    """
    if not settings.seed_accounts or settings.auth != "session":
        return []
    repo = users()
    if repo.count():
        return []

    password_hash = hash_password(settings.seed_password)
    created = []
    for username, display_name, roles in SEEDS:
        check_role_set(roles)  # a bad seed must fail loudly, at install time
        repo.create(
            username,
            display_name,
            password_hash=password_hash,
            roles=[r.value for r in roles],
        )
        created.append(username)
    log.warning(
        "seeded starter accounts with a known default password - change them",
        accounts=created,
        password=settings.seed_password,
    )
    return created


def warn_about_seeded_passwords() -> list[str]:
    """Name every account still using the password the installer set.

    Said out loud at every startup, not once at seeding: a warning nobody sees
    again after the first boot is a warning that stops working the moment it
    starts mattering.
    """
    stale = [u.username for u in users().list() if u.uses_seeded_password]
    if stale:
        log.warning("accounts still using the default password", accounts=stale)
    return stale
