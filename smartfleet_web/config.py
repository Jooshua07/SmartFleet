"""Fail-closed settings for isolated Flask development and tests."""

import os
import string
from datetime import timedelta

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DATABASES = {
    "development": ("smartfleet_flask_dev", "smartfleet_flask_dev_reader"),
    "testing": ("smartfleet_flask_test", "smartfleet_flask_test_reader"),
}


def settings_from_environment():
    env = os.environ
    return {
        "SMARTFLEET_ENV": env.get("SMARTFLEET_ENV", "development"),
        "SECRET_KEY": env.get("SMARTFLEET_SECRET_KEY"),
        "OWNER_USERNAME": env.get("SMARTFLEET_OWNER_USERNAME"),
        "OWNER_PASSWORD_HASH": env.get("SMARTFLEET_OWNER_PASSWORD_HASH"),
        "DB_SETTINGS": {
            "host": env.get("SMARTFLEET_DB_HOST"),
            "port": env.get("SMARTFLEET_DB_PORT", "5432"),
            "dbname": env.get("SMARTFLEET_DB_NAME"),
            "user": env.get("SMARTFLEET_DB_USER"),
            "password": env.get("SMARTFLEET_DB_PASSWORD"),
        },
        "WRITE_DB_SETTINGS": None
        if not env.get("SMARTFLEET_WRITE_DB_PASSWORD")
        else {
            "host": env.get("SMARTFLEET_DB_HOST"),
            "port": env.get("SMARTFLEET_DB_PORT", "5432"),
            "dbname": env.get("SMARTFLEET_DB_NAME"),
            "user": env.get("SMARTFLEET_WRITE_DB_USER"),
            "password": env.get("SMARTFLEET_WRITE_DB_PASSWORD"),
        },
        "TRUSTED_HOSTS": env.get("SMARTFLEET_TRUSTED_HOSTS", "localhost,127.0.0.1,[::1]").split(
            ","
        ),
        "SESSION_COOKIE_NAME": "smartfleet_dev_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": True,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=30),
        "SESSION_REFRESH_EACH_REQUEST": False,
        "MAX_CONTENT_LENGTH": 64 * 1024,
        "MAX_FORM_MEMORY_SIZE": 16 * 1024,
        "MAX_FORM_PARTS": 30,
        "WTF_CSRF_TIME_LIMIT": 1800,
        "TESTING": False,
    }


def validate_settings(config):
    mode = config["SMARTFLEET_ENV"]
    if mode not in DATABASES:
        raise ValueError("Only isolated development/testing is authorized at this stage.")
    expected_name, expected_user = DATABASES[mode]
    db = config["DB_SETTINGS"]
    if (
        db.get("host") not in LOCAL_HOSTS
        or db.get("dbname") != expected_name
        or db.get("user") != expected_user
        or not db.get("password")
    ):
        raise ValueError("Flask requires the explicitly isolated local database and reader role.")
    try:
        port = int(db["port"])
    except (ValueError, TypeError):
        raise ValueError("Invalid local PostgreSQL port.") from None
    if not 1 <= port <= 65535:
        raise ValueError("Invalid local PostgreSQL port.")
    secret = config.get("SECRET_KEY")
    if not isinstance(secret, str) or len(secret) < 32 or secret.startswith("replace-"):
        raise ValueError("A private random session secret of at least 32 characters is required.")
    username = config.get("OWNER_USERNAME")
    if not isinstance(username, str) or not username.strip() or len(username) > 100:
        raise ValueError("Configure the owner identity.")
    password_hash = config.get("OWNER_PASSWORD_HASH") or ""
    parts = password_hash.split("$")
    if len(parts) != 3 or not all(parts):
        raise ValueError("Configure a Werkzeug password hash, never a plaintext password.")
    method = parts[0]
    if method.startswith("pbkdf2:sha256:"):
        try:
            adequate = int(method.rsplit(":", 1)[1]) >= 1_000_000
        except ValueError:
            adequate = False
    else:
        adequate = method == "scrypt:32768:8:1"
    if not adequate:
        raise ValueError("The owner password hash does not meet the configured security baseline.")
    expected_length = 64 if method.startswith("pbkdf2:") else 128
    if (
        len(parts[1]) < 16
        or len(parts[2]) != expected_length
        or any(character not in string.hexdigits for character in parts[2])
    ):
        raise ValueError("The owner password hash is malformed.")
    if not config.get("TRUSTED_HOSTS") or any(
        not host or host.startswith(".") or "*" in host for host in config["TRUSTED_HOSTS"]
    ):
        raise ValueError("Explicit trusted browser host names are required.")
    config["DB_SETTINGS"] = {
        **db,
        "port": port,
        "connect_timeout": 5,
        "application_name": "smartfleet-flask-isolated",
        "options": "-c default_transaction_read_only=on -c statement_timeout=5000",
    }
    writer = config.get("WRITE_DB_SETTINGS")
    if writer is not None:
        if (
            writer.get("host") != db["host"]
            or writer.get("dbname") != expected_name
            or writer.get("user") != expected_name + "_writer"
            or str(writer.get("port")) != str(port)
            or not writer.get("password")
        ):
            raise ValueError("Writes require the separate restricted isolated writer role.")
        config["WRITE_DB_SETTINGS"] = {
            **writer,
            "port": port,
            "connect_timeout": 5,
            "application_name": "smartfleet-flask-command",
            "options": "-c statement_timeout=10000 -c lock_timeout=5000",
        }
