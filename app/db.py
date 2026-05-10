from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.config import SETTINGS


def make_connection(database: str | None = None, autocommit: bool = False) -> psycopg.Connection:
    target_db = database or SETTINGS.database
    return psycopg.connect(
        host=SETTINGS.host,
        port=SETTINGS.port,
        user=SETTINGS.user,
        password=SETTINGS.password,
        dbname=target_db,
        autocommit=autocommit,
    )


@contextmanager
def get_connection(database: str | None = None, autocommit: bool = False) -> Iterator[psycopg.Connection]:
    connection = make_connection(database=database, autocommit=autocommit)
    try:
        yield connection
    finally:
        connection.close()
