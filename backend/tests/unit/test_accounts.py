"""Sign-in, sessions and seeded accounts (ADR-0017).

Runs the **real** resolution path — no `authz.use()` override anywhere in this
file. That is the point: `test_authz.py` proves the gate refuses the wrong
principal, and this one proves a browser actually becomes the right principal.
Testing only the first leaves the interesting half untested.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from blackinterface.api import accounts, authz, deps
from blackinterface.api import app as app_module
from blackinterface.api.source import StationStore
from blackinterface.config import Settings, get_settings
from blackinterface.domain.authz import Capability, Role
from blackinterface.passwords import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from blackinterface.store.db import Database
from blackinterface.store.users import UserRepository
from tests.conftest import SAS_TREE

PASSWORD = "seed-password-for-tests"


@pytest.fixture
def client(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("accounts")
    database = Database(data_dir / "test.sqlite")
    settings = Settings(
        source="fixture",
        fixture=SAS_TREE,
        data_dir=data_dir,
        realtime=False,
        auth="session",
        seed_password=PASSWORD,
    )
    # `get_settings` is cached, and both the app and `accounts` read it. One
    # patch keeps every reader looking at the same configuration.
    monkeypatch.setattr("blackinterface.config.get_settings", lambda: settings)
    monkeypatch.setattr("blackinterface.api.accounts.get_settings", lambda: settings)
    monkeypatch.setattr("blackinterface.api.routers.auth.get_settings", lambda: settings)
    monkeypatch.setattr(app_module, "settings", settings)
    authz.use(None)  # the real path, not an override
    deps.use(StationStore(settings, database), database)
    with TestClient(app_module.app) as test_client:
        yield test_client


def _login(client: TestClient, username: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/api/login", json={"username": username, "password": password})


# ------------------------------------------------------------------- seeding


def test_a_fresh_install_has_one_account_per_role(client: TestClient) -> None:
    users = {u.username: u for u in accounts.users().list()}
    assert set(users) == {seed[0] for seed in accounts.SEEDS}
    assert users["engineer"].roles == ("engineer",)
    # The lightly-manned station: one account, several jobs (ADR-0016 §1).
    assert set(users["truc"].roles) == {"operator", "supervisor", "maintenance"}


def test_no_seeded_account_can_both_edit_the_model_and_sign(client: TestClient) -> None:
    """The separation-of-duty rule, checked against the data actually shipped."""
    for user in accounts.users().list():
        caps = accounts.principal_of(user).capabilities
        assert not (Capability.MODEL_EDIT in caps and Capability.CONTROL_SIGN in caps), (
            user.username
        )


def test_seeding_does_not_resurrect_a_deleted_account(client: TestClient) -> None:
    """Guarded on the count, so an administrator's deletion stays deleted."""
    repo = accounts.users()
    with repo.db.transaction() as conn:
        conn.execute("DELETE FROM users WHERE username = 'protection'")
    accounts.seed_default_accounts(get_settings())
    assert repo.get_by_username("protection") is None


def test_seeded_passwords_are_reported_as_unchanged(client: TestClient) -> None:
    assert set(accounts.warn_about_seeded_passwords()) == {s[0] for s in accounts.SEEDS}


# ------------------------------------------------------------------- sign in


def test_signing_in_grants_that_account_and_nothing_more(client: TestClient) -> None:
    assert client.get("/api/station").status_code == 401

    body = _login(client, "operator").json()
    assert body["authenticated"] is True
    assert body["roles"] == ["operator"]
    assert body["display_name"] == "Vận hành viên"

    assert client.get("/api/station").status_code == 200
    assert client.get("/api/projects").status_code == 403  # no model.connect


def test_the_engineer_account_reaches_the_engineering_surface(client: TestClient) -> None:
    _login(client, "engineer")
    assert client.get("/api/projects").status_code == 200
    assert client.get("/api/station").status_code == 200


def test_the_multi_role_account_adds_its_roles_up(client: TestClient) -> None:
    body = _login(client, "truc").json()
    assert "control.sign" in body["capabilities"]  # from supervisor
    assert "control.draft" in body["capabilities"]  # from operator
    assert "model.publish" not in body["capabilities"]


def test_a_wrong_password_and_an_unknown_account_look_the_same(client: TestClient) -> None:
    """Otherwise the login tells an attacker which usernames are real."""
    wrong = _login(client, "operator", "not the password")
    missing = _login(client, "nobody-at-all", "not the password")
    assert wrong.status_code == missing.status_code == 400
    assert wrong.json()["error"] == missing.json()["error"]


def test_a_disabled_account_cannot_sign_in(client: TestClient) -> None:
    repo = accounts.users()
    user = repo.get_by_username("operator")
    assert user is not None
    repo.set_disabled(user.id, True)
    assert _login(client, "operator").status_code == 400


def test_disabling_an_account_ends_its_open_sessions(client: TestClient) -> None:
    """ "Disable" has to mean now, not when the cookie happens to expire."""
    _login(client, "maintenance")
    assert client.get("/api/station").status_code == 200

    repo = accounts.users()
    user = repo.get_by_username("maintenance")
    assert user is not None
    repo.set_disabled(user.id, True)

    assert client.get("/api/station").status_code == 401


def test_the_session_cookie_is_httponly(client: TestClient) -> None:
    """Unreadable from JavaScript, so an XSS cannot lift the session."""
    response = _login(client, "operator")
    raw = response.headers["set-cookie"].lower()
    assert "httponly" in raw and "samesite=lax" in raw


def test_the_cookie_does_not_contain_the_stored_token(client: TestClient) -> None:
    """Only the digest is stored, so the table is not a set of usable logins."""
    _login(client, "operator")
    token = client.cookies["bi_session"]
    rows = accounts.users().db.connection.execute("SELECT token_hash FROM sessions").fetchall()
    stored = {str(r["token_hash"]) for r in rows}
    assert token not in stored
    assert hash_session_token(token) in stored


def test_signing_out_invalidates_the_session_server_side(client: TestClient) -> None:
    _login(client, "operator")
    token = client.cookies["bi_session"]
    assert client.post("/api/logout").json()["authenticated"] is False

    # Replaying the old cookie must not work: clearing it in the browser is not
    # what ends a session.
    client.cookies.set("bi_session", token)
    assert client.get("/api/station").status_code == 401


def test_an_expired_session_stops_working(client: TestClient) -> None:
    repo = accounts.users()
    user = repo.get_by_username("operator")
    assert user is not None
    token = new_session_token()
    repo.start_session(user.id, hash_session_token(token), ttl_hours=-1)
    client.cookies.set("bi_session", token)
    assert client.get("/api/station").status_code == 401


def test_an_unknown_role_in_the_database_grants_nothing_extra(client: TestClient) -> None:
    """A hand-edited row must not be able to invent a permission."""
    repo = accounts.users()
    user = repo.get_by_username("operator")
    assert user is not None
    repo.set_roles(user.id, ["operator", "wizard"])
    body = _login(client, "operator").json()
    assert body["roles"] == ["operator"]


# ------------------------------------------------------------ password change


def test_changing_a_password_needs_the_current_one(client: TestClient) -> None:
    _login(client, "operator")
    refused = client.post(
        "/api/password", json={"current_password": "wrong", "new_password": "a-new-password"}
    )
    assert refused.status_code == 400

    ok = client.post(
        "/api/password", json={"current_password": PASSWORD, "new_password": "a-new-password"}
    )
    assert ok.status_code == 200
    assert _login(client, "operator", PASSWORD).status_code == 400
    assert _login(client, "operator", "a-new-password").status_code == 200


def test_a_short_password_is_refused(client: TestClient) -> None:
    _login(client, "operator")
    refused = client.post(
        "/api/password", json={"current_password": PASSWORD, "new_password": "short"}
    )
    assert refused.status_code == 400


def test_a_changed_password_stops_being_reported_as_seeded(client: TestClient) -> None:
    _login(client, "operator")
    client.post(
        "/api/password", json={"current_password": PASSWORD, "new_password": "a-new-password"}
    )
    assert "operator" not in accounts.warn_about_seeded_passwords()


# ------------------------------------------------------------------- hashing


def test_a_password_is_never_stored_in_the_clear(client: TestClient) -> None:
    for user in accounts.users().list():
        assert user.password_hash is not None
        assert PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")


def test_hashing_is_salted() -> None:
    """Two accounts with the same password must not share a hash."""
    assert hash_password("same") != hash_password("same")


def test_an_external_identity_has_no_local_password(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """`password_hash IS NULL` is the federation case, and it must be a closed
    door locally — not an account anybody can sign in to with anything."""
    database = Database(tmp_path_factory.mktemp("ext") / "test.sqlite")
    database.migrate()
    repo = UserRepository(database)
    user = repo.create(
        "from.ats",
        "Người từ ATS",
        password_hash=None,
        roles=[Role.OPERATOR.value],
        external_id="ats:1234",
    )
    assert user.external_id == "ats:1234"
    assert verify_password("", None) is False
    assert verify_password("anything", user.password_hash) is False


def test_a_corrupt_hash_locks_one_account_not_the_endpoint() -> None:
    assert verify_password("anything", "not-an-argon2-hash") is False
