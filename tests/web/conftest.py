import secrets
from datetime import date
from decimal import Decimal

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
def app(app_config, monkeypatch):
    # Unit navigation/auth tests have no database; real setup checks run in integration tests.
    monkeypatch.setattr(
        "services.validation_service.get_data_validation_warnings", lambda *args: []
    )
    return create_app(app_config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def empty_report():
    totals = {
        key: Decimal("0") for key in ("money_in", "money_out", "closing_balance", "other_payments")
    }
    totals["other_payment_breakdown"] = {}
    return dict(
        start=date(2026, 10, 1),
        end=date(2026, 10, 17),
        today=date(2026, 10, 17),
        baseline=date(2026, 10, 1),
        current=totals,
        selected=totals,
        operating={"revenue": Decimal("0"), "expenses": Decimal("0")},
        counts={"ACTIVE": 0, "INACTIVE": 0},
        fleet={"buses": [], "shared_general_costs": Decimal("0")},
        chart_data={},
        series=[],
        period_mode="1m",
        custom_mode="all",
        section="general",
        rows=[],
        page=1,
        has_next=False,
    )
