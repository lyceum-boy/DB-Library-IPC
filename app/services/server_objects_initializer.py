"""Сервис создания серверных объектов базы данных."""

from app.db import get_connection
from app.sql.functions import FUNCTIONS_STATEMENTS
from app.sql.procedures import PROCEDURES_STATEMENTS
from app.sql.triggers import TRIGGER_STATEMENTS
from app.sql.views import VIEWS_STATEMENTS


def create_server_objects() -> None:
    """Создаёт представления, функции, процедуру и триггеры в PostgreSQL."""
    statement_groups = [
        VIEWS_STATEMENTS,
        FUNCTIONS_STATEMENTS,
        PROCEDURES_STATEMENTS,
        TRIGGER_STATEMENTS,
    ]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statements in statement_groups:
                for statement in statements:
                    cursor.execute(statement)
        connection.commit()
