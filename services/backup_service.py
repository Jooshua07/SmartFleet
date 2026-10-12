import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "backups"
ENV_PATH = PROJECT_ROOT / ".env"
PG_DUMP_CANDIDATES = (
    Path("C:/Program Files/PostgreSQL/18/bin/pg_dump.exe"),
    Path("C:/Program Files/PostgreSQL/17/bin/pg_dump.exe"),
    Path("C:/Program Files/PostgreSQL/16/bin/pg_dump.exe"),
)
PG_RESTORE_CANDIDATES = (
    Path("C:/Program Files/PostgreSQL/18/bin/pg_restore.exe"),
    Path("C:/Program Files/PostgreSQL/17/bin/pg_restore.exe"),
    Path("C:/Program Files/PostgreSQL/16/bin/pg_restore.exe"),
)


def _load_database_settings() -> dict:
    values = dotenv_values(ENV_PATH)
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError("Database backup settings are incomplete.")
    return values


def _find_tool(tool_name: str, candidates: tuple[Path, ...]) -> str:
    found = shutil.which(tool_name)
    if found:
        return found
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise ValueError(f"{tool_name} was not found on this computer.")


def create_database_backup() -> Path:
    settings = _load_database_settings()
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{settings['DB_NAME']}_{timestamp}.dump"
    pg_dump = _find_tool("pg_dump", PG_DUMP_CANDIDATES)

    env = os.environ.copy()
    env["PGPASSWORD"] = str(settings["DB_PASSWORD"])
    result = subprocess.run(
        [
            pg_dump,
            "--host",
            str(settings["DB_HOST"]),
            "--port",
            str(settings["DB_PORT"]),
            "--username",
            str(settings["DB_USER"]),
            "--dbname",
            str(settings["DB_NAME"]),
            "--format",
            "custom",
            "--blobs",
            "--file",
            str(backup_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("Database backup failed.")
    return backup_path


def verify_backup(backup_path: Path) -> int:
    pg_restore = _find_tool("pg_restore", PG_RESTORE_CANDIDATES)
    result = subprocess.run(
        [pg_restore, "--list", str(backup_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("Backup verification failed.")
    return len(result.stdout.splitlines())


def list_backups(limit: int = 10) -> list[dict]:
    if not BACKUP_DIR.exists():
        return []
    backups = sorted(BACKUP_DIR.glob("*.dump"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        {
            "path": path,
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime),
        }
        for path in backups[:limit]
    ]


def latest_backup_age_hours() -> float | None:
    backups = list_backups(limit=1)
    if not backups:
        return None
    delta = datetime.now() - backups[0]["modified_at"]
    return delta.total_seconds() / 3600
