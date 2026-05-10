from psycopg import sql

from app.config import SETTINGS
from app.db import get_connection
from app.sql.schema import SCHEMA_STATEMENTS


def create_database_if_not_exists() -> bool:
    created = False
    with get_connection(database=SETTINGS.admin_database, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (SETTINGS.database,),
            )
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(SETTINGS.database))
                )
                created = True
    return created


def create_schema() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
        connection.commit()
