import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from openpyxl import load_workbook

from services.maintenance_service import servicing_warning
from services.report_export_service import csv_export, excel_export
from smartfleet_web import private_backups
from smartfleet_web.help_content import GUIDES
from tests.web.test_foundation import csrf, login

READS = [
    "/servicing",
    "/record-servicing",
    "/servicing/1/edit",
    "/servicing/schedule/1",
    "/reminders",
    "/reports",
    "/reports/export",
    "/backups",
    "/backups/invalid/download",
    "/help",
]
WRITES = ["/record-servicing", "/servicing/1/edit", "/servicing/schedule/1", "/backups"]


@pytest.mark.parametrize("path", READS)
def test_stage6_reads_require_owner_without_query(client, path):
    with (
        patch(
            "smartfleet_web.operations.get_connection",
            side_effect=AssertionError("No unauthenticated database access"),
        ),
        patch(
            "smartfleet_web.private_backups.directory",
            side_effect=AssertionError("No unauthenticated file access"),
        ),
    ):
        assert client.get(path).status_code == 302


@pytest.mark.parametrize("path", WRITES)
def test_stage6_posts_require_csrf_and_owner(client, path):
    assert client.post(path).status_code == 400
    token = csrf(client)
    assert client.post(path, data={"csrf_token": token}).status_code == 302
    assert login(client).status_code == 303
    assert client.post(path, data={"command_token": "forged"}).status_code == 400


def test_help_search_escape_and_topic_coverage(client):
    login(client)
    assert len(GUIDES) == 29
    assert len({g.id for g in GUIDES}) == len(GUIDES)
    assert client.get("/help?category=unknown").status_code == 400
    assert client.get("/help?q=" + "x" * 101).status_code == 400
    response = client.get("/help?q=%3Cscript%3E")
    assert response.status_code == 200 and b"<script>" not in response.data
    assert b"&lt;script&gt;" in response.data
    assert b"record completed servicing" in client.get("/help?q=completed+servicing").data
    assert b"No matching topics" in client.get("/help?category=Drivers&q=servicing").data


@pytest.mark.parametrize(
    "due,expected",
    [
        (None, "Not scheduled"),
        (date(2026, 10, 16), "Overdue"),
        (date(2026, 10, 17), "Urgent"),
        (date(2026, 10, 24), "Urgent"),
        (date(2026, 10, 31), "Warning"),
        (date(2026, 11, 1), "Normal"),
    ],
)
def test_servicing_warning_boundaries(due, expected):
    assert servicing_warning(due, date(2026, 10, 17)) == expected


@pytest.mark.parametrize("formula", ["=1+1", "+SUM(A1)", "-2+3", "@SUM(A1)", "\t=2", "\r=2"])
def test_exports_preserve_dates_decimals_and_block_formulas(formula):
    rows = [{"Name": formula, "Date": date(2026, 10, 1), "Amount": Decimal("-800.25")}]
    assert ("'" + formula) in csv_export(rows).decode("utf-8-sig")
    workbook = load_workbook(BytesIO(excel_export({"Ledger": rows, "Empty": []})))
    # XML normalizes a carriage return to LF; the apostrophe and literal cell type must survive.
    assert workbook["Ledger"]["A2"].value == "'" + formula.replace("\r", "\n")
    assert workbook["Ledger"]["A2"].data_type == "s"
    assert workbook["Ledger"]["C2"].value == -800.25
    assert workbook["Ledger"]["B2"].value.date() == date(2026, 10, 1)
    assert workbook["Empty"]["A1"].value == "No records for selected period"


@pytest.mark.parametrize(
    "changes",
    [
        {"dbname": "smartfleet"},
        {"host": "vps.invalid"},
        {"host": "0.0.0.0"},  # noqa: S104 -- deliberately rejected configuration.
        {"user": "postgres"},
        {"user": "smartfleet_flask_test_writer"},
    ],
)  # noqa: S104 -- rejected unsafe bind.
def test_backup_settings_fail_closed(app_config, changes):
    with pytest.raises(ValueError, match="isolated"):
        private_backups.isolated_settings({**app_config["DB_SETTINGS"], **changes})


@pytest.mark.parametrize("key", ["../secret", "..", "", "123", "A" * 36])
def test_backup_identity_rejects_paths(key):
    with pytest.raises(ValueError):
        private_backups.identity(key)


def test_backup_unpublished_or_tampered_manifest_unavailable(app_config, tmp_path):
    settings = app_config["DB_SETTINGS"]
    folder = private_backups.directory(settings, tmp_path)
    key = str(uuid4())
    with pytest.raises(ValueError):
        private_backups.archive(settings, key, tmp_path)
    (folder / (key + ".json")).write_text(json.dumps({"database": "smartfleet"}))
    assert private_backups.list_archives(settings, tmp_path) == []
    with pytest.raises(ValueError):
        private_backups.archive(settings, key, tmp_path)


def test_backup_process_timeout_terminates_and_tool_errors_are_private(monkeypatch):
    class Process:
        returncode = None
        stopped = False

        def poll(self):
            return 0 if self.stopped else None

        def terminate(self):
            self.stopped = True

        def wait(self, **kwargs):
            return 0

    process = Process()
    monkeypatch.setattr(private_backups.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(private_backups, "TIMEOUT", -1)
    with pytest.raises(ValueError, match="timed out"):
        private_backups.bounded_run(["fixed-tool"], {})
    assert process.stopped
    process.stopped = True
    process.returncode = 1
    with pytest.raises(ValueError, match="tool failed"):
        private_backups.bounded_run(["fixed-tool"], {})


def test_backup_missing_tool_has_no_shell_fallback(monkeypatch):
    monkeypatch.setattr(private_backups.shutil, "which", lambda name: None)
    with pytest.raises(ValueError, match="not found"):
        private_backups._find_tool("nonexistent", ())


def test_private_directory_rejects_link_ancestors(app_config, tmp_path, monkeypatch):
    from pathlib import Path

    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == tmp_path or original(path))
    with pytest.raises(ValueError, match="cannot be a link"):
        private_backups.directory(app_config["DB_SETTINGS"], tmp_path)


def test_report_resource_guard_precedes_loading(app, monkeypatch):
    from contextlib import contextmanager

    from smartfleet_web import operations

    class Result:
        def fetchone(self):
            return (10001, 4)

    class Connection:
        def execute(self, *args):
            return Result()

    @contextmanager
    def transaction(settings):
        yield Connection()

    monkeypatch.setattr(operations, "shared_transaction", transaction)
    monkeypatch.setattr(operations, "get_reporting_baseline_date", lambda: date(2026, 10, 1))
    with (
        app.app_context(),
        patch.object(
            operations.reports,
            "get_business_report",
            side_effect=AssertionError("Report must remain bounded"),
        ),
    ):
        with pytest.raises(ValueError, match="resource limit"):
            operations.report_data({})


def test_backup_oversize_terminates_child(tmp_path, monkeypatch):
    class Process:
        returncode = None
        stopped = False

        def poll(self):
            return 0 if self.stopped else None

        def terminate(self):
            self.stopped = True

        def wait(self, **kwargs):
            return 0

    process = Process()
    watched = tmp_path / "oversize.partial"
    watched.write_bytes(b"x" * 11)
    monkeypatch.setattr(private_backups, "MAX_ARCHIVE", 10)
    monkeypatch.setattr(private_backups.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(ValueError, match="archive limit"):
        private_backups.bounded_run(["fixed-tool"], {}, watched)
    assert process.stopped
