"""Provision new loopback-only synthetic databases, never reset an existing database."""

import os
import re
import secrets
import shutil
import subprocess
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"


def local_admin_settings():
    source = dotenv_values(ROOT / ".env")
    if source.get("DB_HOST") not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Refusing non-loopback source/admin connection.")
    if not all(source.get(key) for key in ("DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")):
        raise ValueError("Local source/admin configuration is incomplete.")
    if (
        any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,62}", source[key])
            for key in ("DB_NAME", "DB_USER")
        )
        or not str(source["DB_PORT"]).isdigit()
    ):
        raise ValueError(
            "Only literal local identifiers/ports are accepted, not connection strings."
        )
    return source


def run_tool(name, args, env):
    executable = shutil.which(name)
    if not executable:
        raise ValueError(f"Required local PostgreSQL tool unavailable: {name}")
    result = subprocess.run(
        [executable, *args], env=env, capture_output=True, text=True, timeout=90, check=False
    )
    if result.returncode:
        raise RuntimeError(f"{name} failed; no source database was modified.")


def provision():
    source = local_admin_settings()
    paths = [ROOT / ".env.flask.local", ROOT / ".env.flask.test.local"]
    if any(path.exists() for path in paths):
        if not all(path.exists() for path in paths):
            raise ValueError("Partial local setup exists. Inspect it; never overwrite credentials.")
        print("Local Flask configuration already exists; no provisioning or reset performed.")
        return
    LOCAL.mkdir(exist_ok=True)
    admin = dict(
        host=source["DB_HOST"],
        port=source["DB_PORT"],
        dbname="postgres",
        user=source["DB_USER"],
        password=source["DB_PASSWORD"],
        connect_timeout=5,
    )
    with psycopg.connect(**admin, autocommit=True) as conn:
        is_admin = conn.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user"
        ).fetchone()[0]
        if not is_admin:
            raise ValueError("Separate local provisioning permission is required.")
        targets = ("smartfleet_flask_dev", "smartfleet_flask_test")
        for name in targets:
            names = [name + "_owner", name + "_reader"]
            if conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
                raise ValueError("An isolated target already exists; refusing to overwrite it.")
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=ANY(%s)", (names,)).fetchone():
                raise ValueError(
                    "A target role already exists; inspect partial setup before proceeding."
                )
        env = os.environ.copy()
        env["PGPASSWORD"] = source["DB_PASSWORD"]
        schema_path = LOCAL / "flask-schema-only.sql"
        common = ["--host", source["DB_HOST"], "--port", source["DB_PORT"]]
        run_tool(
            "pg_dump",
            [
                *common,
                "--username",
                source["DB_USER"],
                "--dbname",
                source["DB_NAME"],
                "--schema-only",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(schema_path),
            ],
            env,
        )
        owner_password = secrets.token_urlsafe(32)
        username = "owner"
        owner_hash = generate_password_hash(owner_password)
        for name, config_path in zip(targets, paths, strict=True):
            owner, reader = name + "_owner", name + "_reader"
            owner_db_password, reader_password = (
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(32),
            )
            for role, password in ((owner, owner_db_password), (reader, reader_password)):
                conn.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                        "NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                    sql.Identifier(name), sql.Identifier(owner)
                )
            )
            conn.execute(
                sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name))
            )
            conn.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(name), sql.Identifier(reader)
                )
            )
            target_env = env.copy()
            target_env["PGPASSWORD"] = owner_db_password
            run_tool(
                "psql",
                [
                    *common,
                    "--username",
                    owner,
                    "--dbname",
                    name,
                    "--no-psqlrc",
                    "--set",
                    "ON_ERROR_STOP=1",
                    "--file",
                    str(schema_path),
                ],
                target_env,
            )
            with psycopg.connect(
                host=source["DB_HOST"],
                port=source["DB_PORT"],
                dbname=name,
                user=owner,
                password=owner_db_password,
            ) as isolated:
                isolated.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(reader))
                )
                isolated.execute(
                    sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                        sql.Identifier(reader)
                    )
                )
                route = isolated.execute(
                    "INSERT INTO routes(name) VALUES (%s) RETURNING id", ("Synthetic Route A",)
                ).fetchone()[0]
                for registration, status in (
                    ("DEMO101", "ACTIVE"),
                    ("DEMO102", "ACTIVE"),
                    ("DEMO103", "INACTIVE"),
                    ("DEMO104", "ACTIVE"),
                ):
                    isolated.execute(
                        "INSERT INTO buses(registration_number,route_id,status,model,seating_capacity) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (registration, route, status, "Synthetic minibus", 26),
                    )
            conn.execute(
                sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(
                    sql.Identifier(reader)
                )
            )
            mode = "testing" if name.endswith("test") else "development"
            values = {
                "SMARTFLEET_ENV": mode,
                "SMARTFLEET_SECRET_KEY": secrets.token_urlsafe(48),
                "SMARTFLEET_OWNER_USERNAME": username,
                "SMARTFLEET_OWNER_PASSWORD_HASH": owner_hash,
                "SMARTFLEET_DB_HOST": source["DB_HOST"],
                "SMARTFLEET_DB_PORT": source["DB_PORT"],
                "SMARTFLEET_DB_NAME": name,
                "SMARTFLEET_DB_USER": reader,
                "SMARTFLEET_DB_PASSWORD": reader_password,
                "SMARTFLEET_FIXTURE_USER": owner,
                "SMARTFLEET_FIXTURE_PASSWORD": owner_db_password,
                "SMARTFLEET_TRUSTED_HOSTS": "localhost,127.0.0.1,[::1]",
            }
            with config_path.open("x", encoding="utf-8") as output:
                output.write("".join(f"{key}='{value}'\n" for key, value in values.items()))
        login_path = LOCAL / "FLASK_OWNER_LOGIN.txt"
        with login_path.open("x", encoding="utf-8") as output:
            output.write(
                f"Local synthetic Flask application only\nUsername: {username}\nPassword: {owner_password}\n"
            )
    print("Created two isolated synthetic databases and restricted reader roles.")
    print("Generated credentials are in ignored local files; no credentials printed.")


if __name__ == "__main__":
    provision()
