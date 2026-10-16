from pathlib import Path

import pytest
from dotenv import dotenv_values
from werkzeug.security import generate_password_hash

from smartfleet_web import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def isolated_config():
    path = ROOT / ".env.flask.test.local"
    if not path.is_file():
        pytest.fail("Required isolated local PostgreSQL test configuration is unavailable.")
    env = dotenv_values(path)
    assert env["SMARTFLEET_ENV"] == "testing"
    assert env["SMARTFLEET_DB_NAME"] == "smartfleet_flask_test"
    assert env["SMARTFLEET_DB_USER"] == "smartfleet_flask_test_reader"
    assert env["SMARTFLEET_DB_HOST"] in {"localhost", "127.0.0.1", "::1"}
    return {
        "TESTING": True,
        "SMARTFLEET_ENV": "testing",
        "SECRET_KEY": env["SMARTFLEET_SECRET_KEY"],
        "OWNER_USERNAME": "browser-owner",
        "OWNER_PASSWORD_HASH": generate_password_hash("browser-synthetic-passphrase"),
        "DB_SETTINGS": {
            "host": env["SMARTFLEET_DB_HOST"],
            "port": env["SMARTFLEET_DB_PORT"],
            "dbname": env["SMARTFLEET_DB_NAME"],
            "user": env["SMARTFLEET_DB_USER"],
            "password": env["SMARTFLEET_DB_PASSWORD"],
        },
        "TRUSTED_HOSTS": ["localhost", "127.0.0.1"],
    }


@pytest.fixture
def isolated_app(isolated_config):
    return create_app(isolated_config)
