"""Сервис проверки серверных объектов базы данных."""

from datetime import date
from typing import Any, Iterable

from app.db import get_connection


def _print_rows(title: str, columns: Iterable[str], rows: Iterable[tuple[Any, ...]]) -> None:
    print(f"\n=== {title} ===")
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(value) for value in row))


def test_views() -> None:
    """Проверяет работу созданных представлений."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    book_id,
                    book_title,
                    authors,
                    genre,
                    publisher,
                    total_copies,
                    available_copies,
                    issued_copies
                FROM view_books_catalog
                ORDER BY book_title
                LIMIT 10;
                """
            )
            _print_rows(
                "Представление view_books_catalog",
                [
                    "book_id",
                    "book_title",
                    "authors",
                    "genre",
                    "publisher",
                    "total_copies",
                    "available_copies",
                    "issued_copies",
                ],
                cursor.fetchall(),
            )

            cursor.execute(
                """
                SELECT
                    issue_id,
                    reader_full_name,
                    book_title,
                    copy_id,
                    planned_return_date,
                    days_overdue,
                    return_state
                FROM view_active_issues
                ORDER BY planned_return_date;
                """
            )
            _print_rows(
                "Представление view_active_issues",
                [
                    "issue_id",
                    "reader_full_name",
                    "book_title",
                    "copy_id",
                    "planned_return_date",
                    "days_overdue",
                    "return_state",
                ],
                cursor.fetchall(),
            )


def test_functions() -> None:
    """Проверяет работу хранимых функций."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_available_copies_count(%s);", (1,))
            available_copies = cursor.fetchone()[0]
            print("\n=== Функция get_available_copies_count ===")
            print(f"Количество доступных экземпляров книги с book_id=1: {available_copies}")

            cursor.execute("SELECT get_reader_active_issues_count(%s);", (2,))
            active_issues = cursor.fetchone()[0]
            print("\n=== Функция get_reader_active_issues_count ===")
            print(f"Количество активных выдач читателя с reader_id=2: {active_issues}")


def test_return_book_procedure() -> None:
    """Проверяет процедуру возврата книги без сохранения изменений в БД."""
    issue_id = 10
    return_date = date(2026, 5, 1)

    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        i.issue_id,
                        i.issue_status,
                        i.actual_return_date,
                        c.copy_id,
                        c.status
                    FROM issues i
                    JOIN copies c ON i.copy_id = c.copy_id
                    WHERE i.issue_id = %s;
                    """,
                    (issue_id,),
                )
                _print_rows(
                    "До вызова процедуры return_book",
                    ["issue_id", "issue_status", "actual_return_date", "copy_id", "copy_status"],
                    cursor.fetchall(),
                )

                cursor.execute("CALL return_book(%s, %s);", (issue_id, return_date))

                cursor.execute(
                    """
                    SELECT
                        i.issue_id,
                        i.issue_status,
                        i.actual_return_date,
                        c.copy_id,
                        c.status
                    FROM issues i
                    JOIN copies c ON i.copy_id = c.copy_id
                    WHERE i.issue_id = %s;
                    """,
                    (issue_id,),
                )
                _print_rows(
                    "После вызова процедуры return_book",
                    ["issue_id", "issue_status", "actual_return_date", "copy_id", "copy_status"],
                    cursor.fetchall(),
                )
        finally:
            connection.rollback()
            print("\nИзменения после проверки процедуры отменены с помощью ROLLBACK.")


def test_status_trigger() -> None:
    """Проверяет автоматическое изменение статуса экземпляра триггером."""
    issue_id = 11
    return_date = date(2026, 5, 2)

    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        i.issue_id,
                        i.issue_status,
                        i.actual_return_date,
                        c.copy_id,
                        c.status
                    FROM issues i
                    JOIN copies c ON i.copy_id = c.copy_id
                    WHERE i.issue_id = %s;
                    """,
                    (issue_id,),
                )
                _print_rows(
                    "До прямого изменения записи issues",
                    ["issue_id", "issue_status", "actual_return_date", "copy_id", "copy_status"],
                    cursor.fetchall(),
                )

                cursor.execute(
                    """
                    UPDATE issues
                    SET
                        issue_status = 'закрыта',
                        actual_return_date = %s
                    WHERE issue_id = %s;
                    """,
                    (return_date, issue_id),
                )

                cursor.execute(
                    """
                    SELECT
                        i.issue_id,
                        i.issue_status,
                        i.actual_return_date,
                        c.copy_id,
                        c.status
                    FROM issues i
                    JOIN copies c ON i.copy_id = c.copy_id
                    WHERE i.issue_id = %s;
                    """,
                    (issue_id,),
                )
                _print_rows(
                    "После прямого изменения записи issues",
                    ["issue_id", "issue_status", "actual_return_date", "copy_id", "copy_status"],
                    cursor.fetchall(),
                )
        finally:
            connection.rollback()
            print("\nИзменения после проверки триггера отменены с помощью ROLLBACK.")


def run_server_object_tests() -> None:
    """Запускает проверки всех созданных серверных объектов."""
    test_views()
    test_functions()
    test_return_book_procedure()
    test_status_trigger()
