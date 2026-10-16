import os
from contextvars import ContextVar

import psycopg
from dotenv import load_dotenv

load_dotenv()

_connection_settings = ContextVar("smartfleet_connection_settings", default=None)


def set_connection_settings(settings):
    return _connection_settings.set(dict(settings))


def reset_connection_settings(token):
    _connection_settings.reset(token)


def get_connection():
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
