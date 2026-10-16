import secrets

import pytest
from werkzeug.security import generate_password_hash

from smartfleet_web import create_app


@pytest.fixture(scope="session")
def owner_hash():
    return generate_password_hash("synthetic-test-passphrase")


@pytest.fixture
def app_config(owner_hash):
    return {
        "TESTING": True,
        "SMARTFLEET_ENV": "testing",
        "SECRET_KEY": secrets.token_urlsafe(48),
        "OWNER_USERNAME": "test-owner",
        "OWNER_PASSWORD_HASH": owner_hash,
        "SESSION_COOKIE_SECURE": False,
        "DB_SETTINGS": {
            "host": "127.0.0.1",
            "port": 5432,
            "dbname": "smartfleet_flask_test",
            "user": "smartfleet_flask_test_reader",
            "password": "synthetic-unit-only",
        },
        "TRUSTED_HOSTS": ["localhost"],
    }


@pytest.fixture
def app(app_config):
    return create_app(app_config)


@pytest.fixture
def client(app):
    return app.test_client()
