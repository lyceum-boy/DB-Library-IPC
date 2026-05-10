import csv
from pathlib import Path

from psycopg import sql

from app.config import DATA_DIR
from app.db import get_connection

TABLE_ORDER = [
    "publishers",
    "genres",
    "authors",
    "readers",
    "employees",
    "suppliers",
    "books",
    "receipts",
    "copies",
    "book_authors",
    "receipt_items",
    "issues",
]

CSV_FILES = {
    "publishers": "publishers.csv",
    "genres": "genres.csv",
    "authors": "authors.csv",
    "readers": "readers.csv",
    "employees": "employees.csv",
    "suppliers": "suppliers.csv",
    "books": "books.csv",
    "receipts": "receipts.csv",
    "copies": "copies.csv",
    "book_authors": "book_authors.csv",
    "receipt_items": "receipt_items.csv",
    "issues": "issues.csv",
}

IDENTITY_TABLES = {
    "publishers": "publisher_id",
    "genres": "genre_id",
    "authors": "author_id",
    "readers": "reader_id",
    "employees": "employee_id",
    "suppliers": "supplier_id",
    "books": "book_id",
    "receipts": "receipt_id",
    "copies": "copy_id",
    "issues": "issue_id",
}


def _read_csv_rows(file_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            prepared = {key: (value if value != "" else None) for key, value in row.items()}
            rows.append(prepared)
    return rows


def truncate_all_tables() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE "
                "issues, receipt_items, book_authors, copies, receipts, books, "
                "suppliers, employees, readers, authors, genres, publishers "
                "RESTART IDENTITY CASCADE;"
            )
        connection.commit()


def load_seed_data() -> None:
    truncate_all_tables()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for table_name in TABLE_ORDER:
                file_path = DATA_DIR / CSV_FILES[table_name]
                rows = _read_csv_rows(file_path)
                if not rows:
                    continue

                columns = list(rows[0].keys())
                column_identifiers = [sql.Identifier(column) for column in columns]
                placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)

                insert_statement = sql.SQL(
                    "INSERT INTO {table} ({columns}) {override} VALUES ({values})"
                ).format(
                    table=sql.Identifier(table_name),
                    columns=sql.SQL(", ").join(column_identifiers),
                    override=sql.SQL("OVERRIDING SYSTEM VALUE") if table_name in IDENTITY_TABLES else sql.SQL(""),
                    values=placeholders,
                )

                for row in rows:
                    values = tuple(row[column] for column in columns)
                    cursor.execute(insert_statement, values)

            for table_name, id_column in IDENTITY_TABLES.items():
                reset_statement = sql.SQL(
                    '''
                    SELECT setval(
                        pg_get_serial_sequence(%s, %s),
                        COALESCE((SELECT MAX({id_column}) FROM {table_name}), 1),
                        COALESCE((SELECT MAX({id_column}) IS NOT NULL FROM {table_name}), FALSE)
                    );
                    '''
                ).format(
                    id_column=sql.Identifier(id_column),
                    table_name=sql.Identifier(table_name),
                )
                cursor.execute(reset_statement, (f"public.{table_name}", id_column))

        connection.commit()
