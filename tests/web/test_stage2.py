from datetime import date

import pytest

from services.collection_schedule_service import coverage_from_rules, validate_week
from services.smart_cashing_service import get_collection_coverage
from smartfleet_web import create_app
from smartfleet_web.commands import CommandConflict, decode_token, fingerprint, form_token
from smartfleet_web.management import money_value


def rules():
    return [
        {
            "collection_day": 4,
            "covered_days": [1, 2, 3],
            "include_previous_sunday": True,
            "effective_from": date(2026, 10, 1),
            "effective_to": None,
        },
        {
            "collection_day": 7,
            "covered_days": [4, 5, 6],
            "include_previous_sunday": False,
            "effective_from": date(2026, 10, 1),
            "effective_to": None,
        },
    ]


@pytest.mark.parametrize("day", [date(2026, 10, 4), date(2026, 10, 8), date(2027, 1, 3)])
def test_historical_defaults_match_legacy(day):
    assert coverage_from_rules(day, rules()) == get_collection_coverage(day)
    assert get_collection_coverage(day, schedule_rules=rules()) == get_collection_coverage(day)


def test_new_collection_day_and_previous_sunday():
    pattern = [
        {"collection_day": 2, "covered_days": [1], "include_previous_sunday": False},
        {"collection_day": 4, "covered_days": [2, 3], "include_previous_sunday": True},
        {"collection_day": 7, "covered_days": [4, 5, 6], "include_previous_sunday": False},
    ]
    validate_week(pattern)
    dated = [{**r, "effective_from": date(2026, 10, 19)} for r in pattern]
    coverage = coverage_from_rules(date(2026, 10, 20), dated)
    assert coverage["coverage_start"] == coverage["coverage_end"] == date(2026, 10, 19)
    assert coverage["collection_type"] == "TUESDAY"
    with pytest.raises(ValueError):
        coverage_from_rules(date(2026, 10, 13), dated)


@pytest.mark.parametrize("change", ["overlap", "gap", "duplicate", "sunday", "nonconsecutive"])
def test_reject_ambiguous_week(change):
    pattern = rules()
    if change == "overlap":
        pattern[1]["covered_days"].append(1)
    elif change == "gap":
        pattern[1]["covered_days"].remove(6)
    elif change == "duplicate":
        pattern.append(pattern[0])
    elif change == "sunday":
        pattern[1]["include_previous_sunday"] = True
    else:
        pattern[0]["covered_days"], pattern[1]["covered_days"] = [1, 3], [2, 4, 5, 6]
    with pytest.raises(ValueError):
        validate_week(pattern)


@pytest.mark.parametrize("amount", ["", "NaN", "Infinity", "-1", "2.001", "1000000000", "bad"])
def test_money_rejects_invalid_inputs(amount):
    with pytest.raises(ValueError):
        money_value({"amount": amount}, "amount")


@pytest.mark.parametrize("amount", ["0", "0.01", "4000", "999999999.99"])
def test_money_keeps_decimal_values(amount):
    assert str(money_value({"amount": amount}, "amount")) == amount


def test_command_tokens_are_scoped_and_tamper_resistant(app):
    with app.app_context():
        token = form_token("account:1", {"balance": "0.00"})
        assert decode_token(token, "account:1")["version"] == fingerprint({"balance": "0.00"})
        for altered, action in [
            (token + "tampered", "account:1"),
            (token, "account:2"),
            ("", "account:1"),
        ]:
            with pytest.raises(CommandConflict):
                decode_token(altered, action)


@pytest.mark.parametrize(
    "key,value",
    [
        ("host", "remote.invalid"),
        ("dbname", "smartfleet"),
        ("user", "smartfleet_flask_test_owner"),
        ("port", 5433),
        ("password", ""),
    ],
)
def test_writer_configuration_cannot_escape_isolation(app_config, key, value):
    writer = {**app_config["DB_SETTINGS"], "user": "smartfleet_flask_test_writer", key: value}
    with pytest.raises(ValueError):
        create_app({**app_config, "WRITE_DB_SETTINGS": writer})


@pytest.mark.parametrize(
    "path",
    [
        "/routes",
        "/drivers",
        "/accounts",
        "/presets",
        "/presets/schedule",
        "/buses/1",
        "/manage/bus-new",
    ],
)
def test_management_requires_owner(client, path):
    assert client.get(path).status_code == 302
    assert client.post(path, data={}).status_code in {400, 405}
