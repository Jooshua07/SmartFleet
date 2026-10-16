import copy
import re
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import psycopg
import pytest

from database.connection import get_connection, reset_connection_settings, set_connection_settings
from smartfleet_web import create_app
from smartfleet_web.auth import LoginThrottle, OwnerSessions, safe_next


def csrf(client, path="/login"):
    page = client.get(path)
    return re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()


def login(client, username="test-owner", password=None, suffix=""):
    if password is None:
        password = "synthetic-test-passphrase"
    token = csrf(client, "/login" + suffix)
    return client.post(
        "/login" + suffix,
        data={"csrf_token": token, "username": username, "password": password},
    )


@pytest.mark.parametrize("path", ["/", "/buses", "/finance", "/more", "/health/ready"])
def test_protected_pages_do_not_query_without_login(client, path):
    with patch("smartfleet_web.views.get_all_buses") as query:
        response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.location
    query.assert_not_called()


@pytest.mark.parametrize("path", ["/", "/buses", "/finance", "/more"])
def test_authenticated_navigation(client, path):
    assert login(client).status_code == 303
    with patch("smartfleet_web.views.get_all_buses", return_value=[]):
        response = client.get(path)
    assert response.status_code == 200
    for label in (b"Home", b"Buses", b"Finance", b"More"):
        assert label in response.data
    assert response.headers["Cache-Control"] == "no-store"


def test_login_logout_csrf_and_cookie_replay(client):
    assert client.post("/login", data={"username": "test-owner"}).status_code == 400
    assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 303
    cookie = client.get_cookie("smartfleet_dev_session").value
    assert client.post("/logout").status_code == 400
    assert client.get("/logout").status_code == 405
    token = csrf(client, "/more")
    assert client.post("/logout", data={"csrf_token": token}).status_code == 303
    client.set_cookie("smartfleet_dev_session", cookie)
    assert client.get("/").status_code == 302


def test_username_and_password_both_required(client):
    assert login(client, username="other").status_code == 401
    assert login(client, password="").status_code == 401
    assert b"synthetic-test-passphrase" not in client.get("/login").data


def test_failed_sign_in_retains_username_but_not_password(client):
    response = login(client, password="wrong-password-to-not-echo")
    assert response.status_code == 401
    assert b'value="test-owner"' in response.data
    assert b"wrong-password-to-not-echo" not in response.data


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.invalid",
        "//evil.invalid",
        "/\\evil.invalid",
        "javascript:alert(1)",
        "//[",
        "/unknown",
        "/%2fexample",
    ],
)
def test_external_or_unknown_redirects_rejected(app, target):
    with app.test_request_context():
        assert safe_next(target) == "/"


def test_local_redirect_preserves_filters(client):
    response = login(client, suffix="?next=%2Fbuses%3Fstatus%3DACTIVE")
    assert response.status_code == 303
    assert response.location == "/buses?status=ACTIVE"


def test_login_rate_limit(client):
    for _ in range(5):
        assert login(client, password="wrong").status_code == 401
    response = login(client)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_throttle_concurrency_bound_and_expiration():
    now = [0]
    limiter = LoginThrottle(clock=lambda: now[0])
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: limiter.consume("same-client"), range(20)))
    assert results.count(0) == 5
    assert len(limiter.clients) == 1
    now[0] = 61
    assert limiter.consume("same-client") == 0


def test_global_throttle_prevents_ip_rotation_and_memory_growth():
    limiter = LoginThrottle(clock=lambda: 0)
    results = [limiter.consume(str(index)) for index in range(1200)]
    assert results.count(0) == 30
    assert len(limiter.clients) <= 1024


def test_session_expiry_capacity_and_restart():
    now = [0]
    sessions = OwnerSessions(clock=lambda: now[0])
    first = sessions.issue()
    assert sessions.valid(first)
    for _ in range(32):
        sessions.issue()
    assert not sessions.valid(first)
    last = sessions.issue()
    now[0] = 1801
    assert not sessions.valid(last)
    assert not OwnerSessions().valid(first)


def test_password_change_revokes_existing_session(client, app, owner_hash):
    login(client)
    app.config["OWNER_USERNAME"] = "changed-owner"
    assert client.get("/").status_code == 302


def test_client_claimed_role_does_not_grant_owner_access(client):
    with client.session_transaction() as state:
        state["subject"] = "owner"
        state["role"] = "admin"
        state["credential_version"] = "forged"
    assert client.get("/buses").status_code == 302


def test_logout_token_cannot_be_reused_for_a_new_session(client):
    login(client)
    old_token = csrf(client, "/more")
    assert client.post("/logout", data={"csrf_token": old_token}).status_code == 303
    login(client)
    assert client.post("/logout", data={"csrf_token": old_token}).status_code == 400


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", "example.invalid"),
        ("host", "0.0.0.0"),  # noqa: S104 -- deliberately rejected unsafe configuration.
        ("dbname", "smartfleet"),
        ("dbname", "smartfleet_flask_dev"),
        ("user", "postgres"),
        ("password", ""),
        ("port", "bad"),
        ("port", 0),
    ],
)
def test_database_configuration_fails_closed(app_config, field, value):
    config = copy.deepcopy(app_config)
    config["DB_SETTINGS"][field] = value
    with pytest.raises(ValueError):
        create_app(config)


@pytest.mark.parametrize(
    "field,value",
    [
        ("SECRET_KEY", None),
        ("SECRET_KEY", "short"),
        ("OWNER_PASSWORD_HASH", "plaintext"),
        ("OWNER_PASSWORD_HASH", "pbkdf2:sha256:1$salt$hash"),
        ("OWNER_USERNAME", ""),
        ("SMARTFLEET_ENV", "production"),
        ("TRUSTED_HOSTS", ["*"]),
    ],
)
def test_insecure_configuration_rejected(app_config, field, value):
    config = copy.deepcopy(app_config)
    config[field] = value
    with pytest.raises(ValueError):
        create_app(config)


def test_request_settings_never_fall_back_to_legacy_credentials(client, app):
    login(client)
    with patch("database.connection.psycopg.connect") as connect:
        token = set_connection_settings(app.config["DB_SETTINGS"])
        try:
            get_connection()
        finally:
            reset_connection_settings(token)
    kwargs = connect.call_args.kwargs
    assert kwargs["dbname"] == "smartfleet_flask_test"
    assert kwargs["user"] == "smartfleet_flask_test_reader"
    assert "read_only=on" in kwargs["options"]


def test_settings_are_context_local(app_config):
    def configured(name):
        token = set_connection_settings({"dbname": name})
        try:
            with patch("database.connection.psycopg.connect") as connect:
                get_connection()
                return connect.call_args.kwargs["dbname"]
        finally:
            reset_connection_settings(token)

    assert configured("first") == "first"
    assert configured("second") == "second"


def test_buses_pagination_filters_and_html_escaping(client):
    login(client)
    row = dict(
        id=1,
        registration_number="<script>alert(1)</script>",
        route_name="Route",
        status="ACTIVE",
        model="Bus",
        seating_capacity=26,
    )
    with patch("smartfleet_web.views.get_all_buses", return_value=[row] * 21) as query:
        response = client.get("/buses?page=2&search=DEMO&status=ACTIVE")
    query.assert_called_once_with(limit=21, offset=20, search="DEMO", status="ACTIVE")
    assert response.status_code == 200
    assert b"&lt;script&gt;" in response.data
    assert b"<script>alert" not in response.data
    assert b"Next" in response.data and b"Previous" in response.data


@pytest.mark.parametrize(
    "query",
    ["page=0", "page=-1", "page=abc", "page=10001", "status=INVALID", "search=" + "x" * 101],
)
def test_invalid_bus_query_does_not_reach_database(client, query):
    login(client)
    with patch("smartfleet_web.views.get_all_buses") as rows:
        assert client.get("/buses?" + query).status_code == 400
    rows.assert_not_called()


def test_database_error_is_safe_and_security_headers_exist(client):
    login(client)
    with patch(
        "smartfleet_web.views.get_all_buses",
        side_effect=psycopg.OperationalError("PRIVATE DB PASSWORD"),
    ):
        response = client.get("/buses")
    assert response.status_code == 503
    assert b"PRIVATE DB PASSWORD" not in response.data
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_host_validation_and_public_health(client):
    assert client.get("/health/live").json == {"status": "ok"}
    assert client.get("/login", headers={"Host": "evil.invalid"}).status_code == 400


def test_cookie_security_defaults(app_config):
    app_config["SESSION_COOKIE_SECURE"] = True
    client = create_app(app_config).test_client()
    response = client.get("/login", base_url="https://localhost")
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Strict-Transport-Security" in response.headers
