"""Сервис проверки серверных объектов базы данных."""

from datetime import date
from typing import Any, Iterable

from prettytable import PrettyTable

from app.db import get_connection


def _format_value(value: Any) -> str:
    """Преобразует значение из БД к удобному строковому представлению."""
    if value is None:
        return "–"
    return str(value)


def _print_table(
    title: str,
    columns: Iterable[str],
    rows: Iterable[tuple[Any, ...]],
    max_width: dict[str, int] | None = None,
) -> None:
    """Печатает результат SQL-запроса в виде таблицы PrettyTable."""
    table = PrettyTable()
    table.field_names = list(columns)
    table.align = "l"
    table.valign = "m"
    table.max_width = max_width or {}

    row_count = 0
    for row in rows:
        table.add_row([_format_value(value) for value in row])
        row_count += 1

    print(f"\n=== {title} ===")
    if row_count == 0:
        print("Данные не найдены.")
    else:
        print(table)


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
            _print_table(
                "Представление view_books_catalog",
                [
                    "Код книги",
                    "Название книги",
                    "Авторы",
                    "Жанр",
                    "Издательство",
                    "Всего, шт.",
                    "Доступно, шт.",
                    "Выдано, шт.",
                ],
                cursor.fetchall(),
                max_width={
                    "Название книги": 28,
                    "Авторы": 38,
                    "Жанр": 18,
                    "Издательство": 18,
                },
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
            _print_table(
                "Представление view_active_issues",
                [
                    "№ выдачи",
                    "Ф.И.О. читателя",
                    "Название книги",
                    "№ экземпляра",
                    "Плановая дата возврата",
                    "Просрочка, дн.",
                    "Состояние",
                ],
                cursor.fetchall(),
                max_width={
                    "Ф.И.О. читателя": 28,
                    "Название книги": 28,
                    "Плановая дата возврата": 18,
                },
            )


def test_functions() -> None:
    """Проверяет работу хранимых функций."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_available_copies_count(%s);", (1,))
            available_copies = cursor.fetchone()[0]
            _print_table(
                "Функция get_available_copies_count",
                ["Проверяемый параметр", "Значение параметра", "Результат"],
                [("book_id", 1, f"{available_copies} доступных экземпляра")],
            )

            cursor.execute("SELECT get_reader_active_issues_count(%s);", (2,))
            active_issues = cursor.fetchone()[0]
            _print_table(
                "Функция get_reader_active_issues_count",
                ["Проверяемый параметр", "Значение параметра", "Результат"],
                [("reader_id", 2, f"{active_issues} активная выдача")],
            )


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
                _print_table(
                    "До вызова процедуры return_book",
                    ["№ выдачи", "Статус выдачи", "Фактическая дата возврата", "№ экземпляра", "Статус экземпляра"],
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
                _print_table(
                    "После вызова процедуры return_book",
                    ["№ выдачи", "Статус выдачи", "Фактическая дата возврата", "№ экземпляра", "Статус экземпляра"],
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
                _print_table(
                    "До прямого изменения записи issues",
                    ["№ выдачи", "Статус выдачи", "Фактическая дата возврата", "№ экземпляра", "Статус экземпляра"],
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
                _print_table(
                    "После прямого изменения записи issues",
                    ["№ выдачи", "Статус выдачи", "Фактическая дата возврата", "№ экземпляра", "Статус экземпляра"],
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
