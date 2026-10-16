"""One durable, audited commit per authenticated command, including service-owned contexts."""

import hashlib
import json
from uuid import UUID, uuid4

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from database.connection import shared_transaction


class CommandConflict(ValueError):
    pass


def canonical(value):
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def form_token(action, state):
    return URLSafeTimedSerializer(current_app.secret_key, salt="command-form").dumps(
        {"key": str(uuid4()), "action": action, "version": fingerprint(state)}
    )


def decode_token(token, action):
    try:
        value = URLSafeTimedSerializer(current_app.secret_key, salt="command-form").loads(
            token, max_age=1800
        )
        UUID(value["key"])
        if value["action"] != action:
            raise ValueError
        return value
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        raise CommandConflict("This form expired or changed. Reload before saving.") from None


def execute_command(
    settings, actor, key, action, payload, resource, reason, read_state, operation, expected_version
):
    """Return only after commit; unique key/advisory locks serialize retries and edits."""
    if not actor or not reason.strip():
        raise ValueError("An owner and reason are required.")
    key = UUID(str(key))
    digest = fingerprint({"action": action, "payload": payload, "reason": reason})
    with shared_transaction(settings) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            # Stable database locks, not process locks, survive worker/restart boundaries.
            for lock in sorted({f"command:{actor}:{key}", f"resource:{resource}"}):
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (lock,))
            cursor.execute(
                "SELECT action,payload_hash,result FROM web_commands WHERE actor=%s AND command_key=%s",
                (actor, key),
            )
            existing = cursor.fetchone()
            if existing:
                if existing["action"] != action or existing["payload_hash"] != digest:
                    raise CommandConflict(
                        "This submission was already used with different details."
                    )
                result = existing["result"]
            else:
                before = read_state(connection)
                if fingerprint(before) != expected_version:
                    raise CommandConflict("These records changed. Reload and review before saving.")
                result = json.loads(canonical(operation()))
                after = read_state(connection)
                cursor.execute(
                    "INSERT INTO web_commands(actor,command_key,action,payload_hash,result) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (actor, key, action, digest, Jsonb(result)),
                )
                cursor.execute(
                    "INSERT INTO web_command_audit(actor,command_key,resource,reason,before_state,after_state) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        actor,
                        key,
                        resource,
                        reason,
                        Jsonb(json.loads(canonical(before))),
                        Jsonb(json.loads(canonical(after))),
                    ),
                )
    return result
