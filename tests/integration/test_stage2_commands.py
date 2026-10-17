import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest

from database.connection import get_connection
from services.route_service import add_route
from smartfleet_web.commands import CommandConflict, execute_command, fingerprint
from smartfleet_web.management import snapshot

pytestmark = pytest.mark.integration


def command(writer, key, name, version, operation=None):
    return execute_command(
        writer,
        "synthetic-command-owner",
        key,
        "route-create",
        {"name": name},
        "reference-data",
        "Synthetic test",
        lambda c: snapshot(c, ("routes",)),
        operation or (lambda: add_route(name)),
        version,
    )


def version(owner):
    with psycopg.connect(**owner) as connection:
        return fingerprint(snapshot(connection, ("routes",)))


def test_runtime_writer_is_restricted(stage2_database):
    _, writer = stage2_database
    with psycopg.connect(**writer) as connection:
        assert connection.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        ).fetchone() == (False, False, False, False)
    for statement in (
        "DELETE FROM buses WHERE false",
        "UPDATE web_command_audit SET reason='x' WHERE false",
        "DELETE FROM web_commands WHERE false",
        "CREATE TABLE forbidden_probe(id int)",
        "INSERT INTO expense_categories(name) VALUES ('Not allowed')",
    ):
        with (
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            psycopg.connect(**writer) as connection,
        ):
            connection.execute(statement)


def test_retry_replay_conflict_and_atomic_audit(stage2_database):
    owner, writer = stage2_database
    key, name = str(uuid4()), "TEST-" + uuid4().hex
    original_version = version(owner)
    first = command(writer, key, name, original_version)
    assert (
        command(writer, key, name, original_version, lambda: pytest.fail("Replay executed"))
        == first
    )
    with pytest.raises(CommandConflict):
        command(writer, key, name + "changed", original_version)
    with psycopg.connect(**owner) as connection:
        assert (
            connection.execute("SELECT count(*) FROM routes WHERE name=%s", (name,)).fetchone()[0]
            == 1
        )
        audit = connection.execute(
            "SELECT actor,reason,before_state,after_state FROM web_command_audit WHERE command_key=%s",
            (key,),
        ).fetchone()
        assert audit[0:2] == ("synthetic-command-owner", "Synthetic test")
        assert len(audit[3]["routes"]) == len(audit[2]["routes"]) + 1


def test_replay_survives_a_fresh_python_process(stage2_database):
    owner, writer = stage2_database
    key, name, original_version = str(uuid4()), "TEST-" + uuid4().hex, version(owner)
    expected = command(writer, key, name, original_version)
    code = """
import json,sys
from dotenv import dotenv_values
from tests.integration.test_stage2_commands import command
env=dotenv_values('.env.flask.test.local')
assert env['SMARTFLEET_DB_NAME']=='smartfleet_flask_test'
assert env['SMARTFLEET_DB_HOST'] in {'localhost','127.0.0.1','::1'}
settings=dict(host=env['SMARTFLEET_DB_HOST'],port=env['SMARTFLEET_DB_PORT'],
dbname='smartfleet_flask_test',user=env['SMARTFLEET_WRITE_DB_USER'],password=env['SMARTFLEET_WRITE_DB_PASSWORD'])
key,name,version=json.loads(sys.stdin.read())
def forbidden():
    raise RuntimeError('A replay must not execute')
print(json.dumps(command(settings,key,name,version,forbidden)))
"""
    result = subprocess.run(  # noqa: S603 -- fixed interpreter/code, synthetic payload on stdin.
        [sys.executable, "-c", code],
        input=json.dumps([key, name, original_version]),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert json.loads(result.stdout) == expected


def test_simultaneous_same_key_exactly_once(stage2_database):
    owner, writer = stage2_database
    key, name, start = str(uuid4()), "TEST-" + uuid4().hex, Barrier(2)
    original_version = version(owner)

    def submit():
        start.wait(timeout=10)
        return command(writer, key, name, original_version)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert results[0] == results[1]
    with psycopg.connect(**owner) as connection:
        assert (
            connection.execute(
                "SELECT count(*) FROM web_command_audit WHERE command_key=%s", (key,)
            ).fetchone()[0]
            == 1
        )


def test_simultaneous_distinct_keys_detect_stale_form(stage2_database):
    owner, writer = stage2_database
    start, original_version = Barrier(2), version(owner)

    def submit(number):
        start.wait(timeout=10)
        try:
            command(writer, str(uuid4()), "TEST-" + uuid4().hex, original_version)
            return "saved"
        except CommandConflict:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == ["saved", "stale"]


@pytest.mark.parametrize("swallow", [False, True])
def test_service_context_never_commits_partial_failure(stage2_database, swallow):
    owner, writer = stage2_database
    name, key = "TEST-" + uuid4().hex, str(uuid4())

    def operation():
        add_route(name)
        try:
            with get_connection():
                raise ValueError("synthetic failure")
        except ValueError:
            if not swallow:
                raise
        return {"unexpected": "success"}

    with pytest.raises((ValueError, RuntimeError)):
        command(writer, key, name, version(owner), operation)
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT 1 FROM routes WHERE name=%s", (name,)).fetchone() is None
        assert (
            connection.execute("SELECT 1 FROM web_commands WHERE command_key=%s", (key,)).fetchone()
            is None
        )


def test_commit_time_deferred_financial_error_rolls_back_command(stage2_database):
    owner, _ = stage2_database
    key, name = str(uuid4()), "TEST-" + uuid4().hex

    def operation():
        route = add_route(name)
        with get_connection() as connection:
            account = connection.execute("SELECT id FROM financial_accounts LIMIT 1").fetchone()[0]
            connection.execute(
                """INSERT INTO financial_transactions(account_id,transaction_date,
                transaction_type,direction,amount) VALUES (%s,DATE '2026-10-01','CASHING','IN',100)""",
                (account,),
            )
        return route

    with pytest.raises(psycopg.Error):
        command(owner, key, name, version(owner), operation)
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT 1 FROM routes WHERE name=%s", (name,)).fetchone() is None
        assert (
            connection.execute("SELECT 1 FROM web_commands WHERE command_key=%s", (key,)).fetchone()
            is None
        )
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0


def test_audit_failure_rolls_back_the_service_and_command_result(stage2_database):
    owner, writer = stage2_database
    key, name = str(uuid4()), "TEST-" + uuid4().hex
    with pytest.raises(psycopg.DataError):
        execute_command(
            writer,
            "synthetic-command-owner",
            key,
            "route-create",
            {"name": name},
            "reference-data",
            "Invalid audit text\x00",
            lambda c: snapshot(c, ("routes",)),
            lambda: add_route(name),
            version(owner),
        )
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT 1 FROM routes WHERE name=%s", (name,)).fetchone() is None
        assert (
            connection.execute("SELECT 1 FROM web_commands WHERE command_key=%s", (key,)).fetchone()
            is None
        )
