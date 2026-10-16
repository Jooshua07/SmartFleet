import os
from contextlib import contextmanager
from contextvars import ContextVar

import psycopg
from dotenv import load_dotenv

load_dotenv()

_connection_settings = ContextVar("smartfleet_connection_settings", default=None)
_transaction = ContextVar("smartfleet_transaction", default=None)


class BorrowedConnection:
    """Let legacy service contexts borrow, but never commit, the command connection."""

    def __init__(self, connection, state):
        self.connection = connection
        self.state = state

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type:
            self.state["failed"] = True

    def __getattr__(self, name):
        if name in {"commit", "rollback", "close", "transaction"}:
            raise RuntimeError("Only the command may finish its transaction.")
        return getattr(self.connection, name)


@contextmanager
def shared_transaction(settings):
    if _transaction.get() is not None:
        raise RuntimeError("Nested command transactions are not supported.")
    with psycopg.connect(**settings) as connection:
        state = {"connection": connection, "failed": False}
        token = _transaction.set(state)
        try:
            yield connection
            if state["failed"]:
                raise RuntimeError("A service failed; the entire command must roll back.")
        finally:
            _transaction.reset(token)


def set_connection_settings(settings):
    return _connection_settings.set(dict(settings))


def reset_connection_settings(token):
    _connection_settings.reset(token)


def get_connection():
    transaction = _transaction.get()
    if transaction is not None:
        return BorrowedConnection(transaction["connection"], transaction)
    settings = _connection_settings.get()
    if settings is not None:
        return psycopg.connect(**settings)
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
