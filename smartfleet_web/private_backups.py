"""Private, bounded archives of the explicitly isolated Flask database only."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import psycopg

from services.backup_service import PG_DUMP_CANDIDATES, PG_RESTORE_CANDIDATES, _find_tool

MAX_ARCHIVE = 100 * 1024 * 1024
MAX_STORAGE = 500 * 1024 * 1024
MIN_FREE = 200 * 1024 * 1024
TIMEOUT = 60
ROOT = Path(__file__).resolve().parents[1] / ".local" / "flask-backups"


def isolated_settings(settings):
    name = settings.get("dbname")
    if (
        settings.get("host") not in {"localhost", "127.0.0.1", "::1"}
        or name not in {"smartfleet_flask_dev", "smartfleet_flask_test"}
        or settings.get("user") != name + "_reader"
    ):
        raise ValueError("Backups require the isolated loopback reader.")
    return name


def directory(settings, root=None):
    name = isolated_settings(settings)
    base = Path(root) if root is not None else ROOT
    # Reject links in every ancestor as well as the final directory.
    for path in (base, *base.parents):
        if path.is_symlink() or path.is_junction():
            raise ValueError("The private backup directory cannot be a link.")
    path = base / name
    if path.is_symlink() or path.is_junction():
        raise ValueError("The private backup directory cannot be a link.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def identity(key):
    try:
        result = str(UUID(str(key)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid backup reference.") from None
    if result != str(key):
        raise ValueError("Invalid backup reference.")
    return result


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def archive(settings, key, root=None):
    folder, key = directory(settings, root), identity(key)
    path, manifest = folder / (key + ".dump"), folder / (key + ".json")
    if path.is_symlink() or manifest.is_symlink():
        raise ValueError("Invalid backup reference.")
    try:
        if manifest.stat().st_size > 8192:
            raise ValueError("Invalid backup metadata.")
        record = json.loads(manifest.read_text(encoding="utf-8"))
        if (
            record["database"] != settings["dbname"]
            or record["key"] != key
            or record["size"] != path.stat().st_size
            or record["size"] > MAX_ARCHIVE
            or record["sha256"] != fingerprint(path)
            or not record["archive_checked"]
        ):
            raise ValueError("Backup integrity check failed.")
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("Backup is incomplete or unavailable.") from None
    return path, record


def list_archives(settings, root=None):
    folder = directory(settings, root)
    records = []
    for manifest in folder.glob("*.json"):
        try:
            # Listing checks metadata/size without hashing every archive on every page load.
            key = identity(manifest.stem)
            path = folder / (key + ".dump")
            if manifest.is_symlink() or path.is_symlink():
                continue
            if manifest.stat().st_size > 8192:
                continue
            record = json.loads(manifest.read_text(encoding="utf-8"))
            if (
                record["database"] == settings["dbname"]
                and record["key"] == key
                and record["size"] == path.stat().st_size
                and 0 < record["size"] <= MAX_ARCHIVE
                and record["archive_checked"]
            ):
                if datetime.fromisoformat(record["created_at"]).tzinfo is None:
                    continue
                records.append(record)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(records, key=lambda r: r["created_at"], reverse=True)[:20]


def latest_age(settings, root=None):
    records = list_archives(settings, root)
    if not records:
        return None
    created = datetime.fromisoformat(records[0]["created_at"])
    return (datetime.now(timezone.utc) - created).total_seconds() / 3600


def bounded_run(args, env, watched=None):
    # Neither credentials nor stderr containing database details leave this private operation.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=errors)  # noqa: S603
        deadline = time.monotonic() + TIMEOUT
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise ValueError("Backup timed out. Please retry later.")
                if watched and watched.exists() and watched.stat().st_size > MAX_ARCHIVE:
                    raise ValueError("Backup exceeds the local archive limit.")
                time.sleep(0.05)
            if process.returncode:
                raise ValueError("The backup tool failed. No completed backup was published.")
            if watched and watched.stat().st_size > MAX_ARCHIVE:
                raise ValueError("Backup exceeds the local archive limit.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def create_archive(settings, key, actor, root=None):
    folder, key = directory(settings, root), identity(key)
    complete, manifest = folder / (key + ".dump"), folder / (key + ".json")
    partial, metadata = folder / (key + ".partial"), folder / (key + ".json.partial")
    with psycopg.connect(**{**settings, "autocommit": True, "connect_timeout": 5}) as connection:
        locked = connection.execute(
            "SELECT pg_try_advisory_lock(hashtext(%s))", ("smartfleet-private-backup",)
        ).fetchone()[0]
        if not locked:
            raise ValueError("Another backup is running. Please retry shortly.")
        try:
            if manifest.exists() or manifest.is_symlink():
                return archive(settings, key, root)[1]
            if any(p.is_symlink() for p in (partial, complete, metadata)):
                raise ValueError("Invalid backup reference.")
            size = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
            if (
                size + MAX_ARCHIVE > MAX_STORAGE
                or shutil.disk_usage(folder).free < MIN_FREE + MAX_ARCHIVE
            ):
                raise ValueError(
                    "Not enough private backup storage. Preserve backups elsewhere before retrying."
                )
            env = {
                **os.environ,
                "PGPASSWORD": str(settings["password"]),
                "PGOPTIONS": "-c default_transaction_read_only=on",
                "PGCONNECT_TIMEOUT": "5",
            }
            dump = _find_tool("pg_dump", PG_DUMP_CANDIDATES)
            restore = _find_tool("pg_restore", PG_RESTORE_CANDIDATES)
            # Truncate only this request's unpublished partial, never an existing archive.
            with partial.open("wb"):
                pass
            partial.chmod(0o600)
            bounded_run(
                [
                    dump,
                    "--host",
                    str(settings["host"]),
                    "--port",
                    str(settings.get("port", 5432)),
                    "--username",
                    str(settings["user"]),
                    "--dbname",
                    settings["dbname"],
                    "--format=custom",
                    "--no-password",
                    "--file",
                    str(partial),
                ],
                env,
                partial,
            )
            bounded_run([restore, "--list", str(partial)], env)
            record = {
                "key": key,
                "database": settings["dbname"],
                "actor": actor,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "size": partial.stat().st_size,
                "sha256": fingerprint(partial),
                "archive_checked": True,
            }
            with partial.open("r+b") as source:
                os.fsync(source.fileno())
            with metadata.open("w", encoding="utf-8") as destination:
                metadata.chmod(0o600)
                json.dump(record, destination)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(partial, complete)
            os.replace(metadata, manifest)
            if os.name != "nt":
                descriptor = os.open(folder, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            return record
        finally:
            for path in (partial, metadata):
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            connection.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))", ("smartfleet-private-backup",)
            )
