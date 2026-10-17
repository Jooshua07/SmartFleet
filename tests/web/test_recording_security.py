from unittest.mock import patch

import pytest

from tests.web.test_foundation import csrf, login


@pytest.mark.parametrize(
    "path",
    [
        "/record-expense",
        "/record-cashing",
        "/expenses",
        "/collections",
        "/obligations",
        "/obligations/1",
        "/delete/expense/1",
        "/collections/1/edit",
        "/collections/1/receipt",
    ],
)
def test_financial_pages_require_owner_before_database(client, path):
    with patch(
        "smartfleet_web.recording.get_connection",
        side_effect=AssertionError("Unauthenticated database access"),
    ):
        assert client.get(path).status_code == 302


@pytest.mark.parametrize(
    "path", ["/record-expense", "/record-cashing", "/obligations/1", "/delete/collection/1"]
)
def test_authenticated_financial_post_requires_csrf(client, path):
    assert login(client).status_code == 303
    with patch(
        "smartfleet_web.recording.get_connection", side_effect=AssertionError("CSRF was bypassed")
    ):
        assert client.post(path, data={"reason": "Test"}).status_code == 400


def test_anonymous_valid_csrf_does_not_authorize_financial_write(client):
    token = csrf(client)
    with patch(
        "smartfleet_web.recording.get_connection",
        side_effect=AssertionError("Owner authorization bypassed"),
    ):
        assert client.post("/record-expense", data={"csrf_token": token}).status_code == 302
