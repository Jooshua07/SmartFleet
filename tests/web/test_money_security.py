from unittest.mock import patch

import pytest

from smartfleet_web.money import ACTIONS, CANCELLATIONS
from tests.web.test_foundation import csrf, login

PAGES = [
    "/driver-money",
    "/driver-money/1",
    "/loans",
    "/owner-money",
    *["/money/" + a for a in ACTIONS],
    *[f"/money/cancel/{a}/1" for a in CANCELLATIONS],
]
POSTS = [*["/money/" + a for a in ACTIONS], *[f"/money/cancel/{a}/1" for a in CANCELLATIONS]]


@pytest.mark.parametrize("path", PAGES)
def test_money_owner_required_before_database(client, path):
    with patch(
        "smartfleet_web.money.get_connection",
        side_effect=AssertionError("Unauthorized database access"),
    ):
        assert client.get(path).status_code == 302


@pytest.mark.parametrize("path", POSTS)
def test_money_mutations_require_csrf(client, path):
    assert login(client).status_code == 303
    with patch("smartfleet_web.money.get_connection", side_effect=AssertionError("CSRF bypass")):
        assert client.post(path, data={"reason": "Synthetic"}).status_code == 400


@pytest.mark.parametrize("path", POSTS)
def test_valid_csrf_is_not_owner_permission(client, path):
    token = csrf(client)
    with patch("smartfleet_web.money.get_connection", side_effect=AssertionError("Owner bypass")):
        assert client.post(path, data={"csrf_token": token}).status_code == 302
