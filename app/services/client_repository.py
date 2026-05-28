"""Сервис доступа к данным для клиентского приложения библиотеки.

В модуле используются только явные SQL-запросы и вызовы серверных объектов
PostgreSQL. ORM-технологии не применяются.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from psycopg.rows import dict_row

from app.db import get_connection
from app.sql.queries import QUERY_3_SQL

Row = dict[str, Any]


class LibraryRepository:
    """Набор операций, используемых графическим клиентским приложением."""

    # ----------------------------- Выборки -----------------------------

    def fetch_books_catalog(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                book_id,
                book_title,
                authors,
                genre,
                publisher,
                publication_year,
                isbn,
                language,
                page_count,
                cover_path,
                total_copies,
                available_copies,
                issued_copies,
                reserved_copies,
                restoration_copies,
                written_off_copies
            FROM view_books_catalog
            WHERE
                %s = ''
                OR LOWER(book_title) LIKE %s
                OR LOWER(authors) LIKE %s
                OR LOWER(genre) LIKE %s
                OR LOWER(publisher) LIKE %s
                OR LOWER(isbn) LIKE %s
            ORDER BY book_title;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern, pattern, pattern))

    def fetch_active_issues(self, search_text: str = "", overdue_only: bool = False) -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                issue_id,
                reader_id,
                reader_full_name,
                book_id,
                book_title,
                copy_id,
                employee_id,
                employee_full_name,
                issue_date,
                planned_return_date,
                days_overdue,
                return_state
            FROM view_active_issues
            WHERE
                (%s = ''
                    OR LOWER(reader_full_name) LIKE %s
                    OR LOWER(book_title) LIKE %s
                    OR LOWER(employee_full_name) LIKE %s)
                AND (%s = FALSE OR return_state = 'просрочена')
            ORDER BY planned_return_date, issue_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern, overdue_only))

    def fetch_readers(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                reader_id,
                last_name,
                first_name,
                middle_name,
                CONCAT_WS(' ', last_name, first_name, middle_name) AS reader_full_name,
                phone,
                registration_date,
                category,
                status
            FROM readers
            WHERE
                %s = ''
                OR LOWER(CONCAT_WS(' ', last_name, first_name, middle_name)) LIKE %s
                OR LOWER(COALESCE(phone, '')) LIKE %s
                OR LOWER(category) LIKE %s
                OR LOWER(status) LIKE %s
            ORDER BY reader_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern, pattern))

    def fetch_employees(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                employee_id,
                last_name,
                first_name,
                middle_name,
                CONCAT_WS(' ', last_name, first_name, middle_name) AS employee_full_name,
                position,
                phone
            FROM employees
            WHERE
                %s = ''
                OR LOWER(CONCAT_WS(' ', last_name, first_name, middle_name)) LIKE %s
                OR LOWER(position) LIKE %s
                OR LOWER(COALESCE(phone, '')) LIKE %s
            ORDER BY employee_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern))

    def fetch_authors(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                author_id,
                last_name,
                first_name,
                middle_name,
                CONCAT_WS(' ', last_name, first_name, middle_name) AS author_full_name,
                birth_date
            FROM authors
            WHERE
                %s = ''
                OR LOWER(CONCAT_WS(' ', last_name, first_name, middle_name)) LIKE %s
            ORDER BY last_name, first_name, middle_name;
        """
        return self._fetch_all(query, (search_text.strip(), pattern))

    def fetch_publishers(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT publisher_id, name, city, phone
            FROM publishers
            WHERE %s = '' OR LOWER(name) LIKE %s OR LOWER(city) LIKE %s OR LOWER(COALESCE(phone, '')) LIKE %s
            ORDER BY publisher_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern))

    def fetch_genres(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT genre_id, name, description
            FROM genres
            WHERE %s = '' OR LOWER(name) LIKE %s OR LOWER(COALESCE(description, '')) LIKE %s
            ORDER BY genre_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern))

    def fetch_suppliers(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT supplier_id, name, address, phone, contact_person
            FROM suppliers
            WHERE
                %s = ''
                OR LOWER(name) LIKE %s
                OR LOWER(address) LIKE %s
                OR LOWER(COALESCE(phone, '')) LIKE %s
                OR LOWER(COALESCE(contact_person, '')) LIKE %s
            ORDER BY supplier_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern, pattern))

    def fetch_copies(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                c.copy_id,
                c.book_id,
                b.title AS book_title,
                c.receipt_id,
                c.arrival_date,
                c.condition_state,
                c.status,
                c.storage_location
            FROM copies c
            JOIN books b ON c.book_id = b.book_id
            WHERE
                %s = ''
                OR LOWER(b.title) LIKE %s
                OR LOWER(c.status) LIKE %s
                OR LOWER(c.storage_location) LIKE %s
            ORDER BY c.copy_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern))

    def fetch_receipts(self, search_text: str = "") -> list[Row]:
        pattern = f"%{search_text.strip().lower()}%"
        query = """
            SELECT
                r.receipt_id,
                r.supplier_id,
                s.name AS supplier_name,
                r.employee_id,
                CONCAT_WS(' ', e.last_name, e.first_name, e.middle_name) AS employee_full_name,
                r.receipt_date,
                r.invoice_number,
                r.total_amount
            FROM receipts r
            JOIN suppliers s ON r.supplier_id = s.supplier_id
            JOIN employees e ON r.employee_id = e.employee_id
            WHERE
                %s = ''
                OR LOWER(s.name) LIKE %s
                OR LOWER(CONCAT_WS(' ', e.last_name, e.first_name, e.middle_name)) LIKE %s
                OR LOWER(r.invoice_number) LIKE %s
            ORDER BY r.receipt_id;
        """
        return self._fetch_all(query, (search_text.strip(), pattern, pattern, pattern))

    def fetch_receipts_summary(self) -> list[Row]:
        return self._fetch_all(QUERY_3_SQL)

    def fetch_available_books(self) -> list[Row]:
        query = """
            SELECT book_id, book_title, authors, available_copies
            FROM view_books_catalog
            WHERE available_copies > 0
            ORDER BY book_title;
        """
        return self._fetch_all(query)

    def fetch_books_for_lookup(self) -> list[Row]:
        query = """
            SELECT book_id, title AS book_title
            FROM books
            ORDER BY title;
        """
        return self._fetch_all(query)

    def fetch_receipts_for_lookup(self) -> list[Row]:
        query = """
            SELECT receipt_id, invoice_number, receipt_date
            FROM receipts
            ORDER BY receipt_id;
        """
        return self._fetch_all(query)

    def fetch_book_details(self, book_id: int) -> Row:
        rows = self._fetch_all(
            """
                SELECT
                    b.*,
                    COALESCE(
                        ARRAY_AGG(ba.author_id ORDER BY ba.author_id)
                            FILTER (WHERE ba.author_id IS NOT NULL),
                        ARRAY[]::integer[]
                    ) AS author_ids
                FROM books b
                LEFT JOIN book_authors ba ON b.book_id = ba.book_id
                WHERE b.book_id = %s
                GROUP BY b.book_id;
            """,
            (book_id,),
        )
        if not rows:
            raise ValueError(f"Книга с кодом {book_id} не найдена.")
        return rows[0]

    def fetch_receipt_details(self, receipt_id: int) -> Row:
        rows = self._fetch_all(
            """
                SELECT
                    receipt_id,
                    supplier_id,
                    employee_id,
                    receipt_date,
                    invoice_number,
                    total_amount
                FROM receipts
                WHERE receipt_id = %s;
            """,
            (receipt_id,),
        )
        if not rows:
            raise ValueError(f"Поступление с кодом {receipt_id} не найдено.")
        receipt = rows[0]
        receipt["items"] = self._fetch_all(
            """
                SELECT book_id, quantity, unit_price
                FROM receipt_items
                WHERE receipt_id = %s
                ORDER BY book_id;
            """,
            (receipt_id,),
        )
        return receipt

    # ---------------------- Функции и процедура PostgreSQL ----------------------

    def get_available_copies_count(self, book_id: int) -> int:
        rows = self._fetch_all("SELECT get_available_copies_count(%s) AS available_copies;", (book_id,))
        return int(rows[0]["available_copies"]) if rows else 0

    def get_reader_active_issues_count(self, reader_id: int) -> int:
        rows = self._fetch_all("SELECT get_reader_active_issues_count(%s) AS active_issues;", (reader_id,))
        return int(rows[0]["active_issues"]) if rows else 0

    def return_book(self, issue_id: int, return_date: date) -> None:
        with get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("CALL return_book(%s, %s);", (issue_id, return_date))
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    # ----------------------------- Добавление -----------------------------

    def create_reader(self, **data: Any) -> int:
        data = self._prepare_reader_data(data)
        self._validate_unique_phone("readers", "reader_id", data.get("phone"))
        return self._insert_returning_id(
            """
                INSERT INTO readers (last_name, first_name, middle_name, phone, registration_date, category, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING reader_id;
            """,
            (
                data["last_name"], data["first_name"], data.get("middle_name"), data.get("phone"),
                data.get("registration_date") or date.today(), data["category"], data["status"],
            ),
        )

    def create_employee(self, **data: Any) -> int:
        data = self._prepare_employee_data(data)
        self._validate_unique_phone("employees", "employee_id", data.get("phone"))
        return self._insert_returning_id(
            """
                INSERT INTO employees (last_name, first_name, middle_name, position, phone)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING employee_id;
            """,
            (data["last_name"], data["first_name"], data.get("middle_name"), data["position"], data.get("phone")),
        )

    def create_author(self, **data: Any) -> int:
        data = self._prepare_author_data(data)
        self._validate_author_duplicate(data)
        return self._insert_returning_id(
            """
                INSERT INTO authors (last_name, first_name, middle_name, birth_date)
                VALUES (%s, %s, %s, %s)
                RETURNING author_id;
            """,
            (data["last_name"], data["first_name"], data.get("middle_name"), data.get("birth_date")),
        )

    def create_publisher(self, **data: Any) -> int:
        data = self._prepare_publisher_data(data)
        self._validate_unique_name("publishers", "publisher_id", data["name"])
        self._validate_unique_phone("publishers", "publisher_id", data.get("phone"))
        return self._insert_returning_id(
            """
                INSERT INTO publishers (name, city, phone)
                VALUES (%s, %s, %s)
                RETURNING publisher_id;
            """,
            (data["name"], data["city"], data.get("phone")),
        )

    def create_genre(self, **data: Any) -> int:
        data = self._prepare_genre_data(data)
        self._validate_unique_name("genres", "genre_id", data["name"])
        return self._insert_returning_id(
            """
                INSERT INTO genres (name, description)
                VALUES (%s, %s)
                RETURNING genre_id;
            """,
            (data["name"], data.get("description")),
        )

    def create_supplier(self, **data: Any) -> int:
        data = self._prepare_supplier_data(data)
        self._validate_unique_name("suppliers", "supplier_id", data["name"])
        self._validate_unique_phone("suppliers", "supplier_id", data.get("phone"))
        return self._insert_returning_id(
            """
                INSERT INTO suppliers (name, address, phone, contact_person)
                VALUES (%s, %s, %s, %s)
                RETURNING supplier_id;
            """,
            (data["name"], data["address"], data.get("phone"), data.get("contact_person")),
        )

    def create_book(self, **data: Any) -> int:
        data = self._prepare_book_data(data)
        self._validate_book_isbn_unique(data["isbn"])
        with get_connection() as connection:
            try:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(
                        """
                            INSERT INTO books (
                                isbn, title, publication_year, publisher_id, genre_id, language, page_count, cover_path
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING book_id;
                        """,
                        (
                            data["isbn"], data["title"], data["publication_year"], data["publisher_id"],
                            data["genre_id"], data["language"], data["page_count"], data.get("cover_path"),
                        ),
                    )
                    book_id = int(cursor.fetchone()["book_id"])
                    self._replace_book_authors(cursor, book_id, data["author_ids"])
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return book_id

    def create_copy(self, **data: Any) -> int:
        data = self._prepare_copy_data(data)
        return self._insert_returning_id(
            """
                INSERT INTO copies (book_id, receipt_id, arrival_date, condition_state, status, storage_location)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING copy_id;
            """,
            (data["book_id"], data["receipt_id"], data["arrival_date"], data["condition_state"], data["status"], data["storage_location"]),
        )

    def create_receipt(self, **data: Any) -> int:
        data = self._prepare_receipt_data(data)
        with get_connection() as connection:
            try:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(
                        """
                            INSERT INTO receipts (supplier_id, employee_id, receipt_date, invoice_number, total_amount)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING receipt_id;
                        """,
                        (data["supplier_id"], data["employee_id"], data["receipt_date"], data["invoice_number"], data["total_amount"]),
                    )
                    receipt_id = int(cursor.fetchone()["receipt_id"])
                    self._replace_receipt_items(cursor, receipt_id, data["items"])
                    self._ensure_receipt_copies(cursor, receipt_id, data["receipt_date"], data["items"])
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return receipt_id

    # ----------------------------- Редактирование -----------------------------

    def update_reader(self, reader_id: int, **data: Any) -> None:
        data = self._prepare_reader_data(data)
        self._validate_unique_phone("readers", "reader_id", data.get("phone"), reader_id)
        self._execute_write(
            """
                UPDATE readers
                SET last_name=%s, first_name=%s, middle_name=%s, phone=%s,
                    registration_date=%s, category=%s, status=%s
                WHERE reader_id=%s;
            """,
            (
                data["last_name"], data["first_name"], data.get("middle_name"), data.get("phone"),
                data.get("registration_date") or date.today(), data["category"], data["status"], reader_id,
            ),
        )

    def update_employee(self, employee_id: int, **data: Any) -> None:
        data = self._prepare_employee_data(data)
        self._validate_unique_phone("employees", "employee_id", data.get("phone"), employee_id)
        self._execute_write(
            """
                UPDATE employees
                SET last_name=%s, first_name=%s, middle_name=%s, position=%s, phone=%s
                WHERE employee_id=%s;
            """,
            (data["last_name"], data["first_name"], data.get("middle_name"), data["position"], data.get("phone"), employee_id),
        )

    def update_author(self, author_id: int, **data: Any) -> None:
        data = self._prepare_author_data(data)
        self._validate_author_duplicate(data, author_id)
        self._execute_write(
            """
                UPDATE authors
                SET last_name=%s, first_name=%s, middle_name=%s, birth_date=%s
                WHERE author_id=%s;
            """,
            (data["last_name"], data["first_name"], data.get("middle_name"), data.get("birth_date"), author_id),
        )

    def update_publisher(self, publisher_id: int, **data: Any) -> None:
        data = self._prepare_publisher_data(data)
        self._validate_unique_name("publishers", "publisher_id", data["name"], publisher_id)
        self._validate_unique_phone("publishers", "publisher_id", data.get("phone"), publisher_id)
        self._execute_write(
            """
                UPDATE publishers
                SET name=%s, city=%s, phone=%s
                WHERE publisher_id=%s;
            """,
            (data["name"], data["city"], data.get("phone"), publisher_id),
        )

    def update_genre(self, genre_id: int, **data: Any) -> None:
        data = self._prepare_genre_data(data)
        self._validate_unique_name("genres", "genre_id", data["name"], genre_id)
        self._execute_write(
            """
                UPDATE genres
                SET name=%s, description=%s
                WHERE genre_id=%s;
            """,
            (data["name"], data.get("description"), genre_id),
        )

    def update_supplier(self, supplier_id: int, **data: Any) -> None:
        data = self._prepare_supplier_data(data)
        self._validate_unique_name("suppliers", "supplier_id", data["name"], supplier_id)
        self._validate_unique_phone("suppliers", "supplier_id", data.get("phone"), supplier_id)
        self._execute_write(
            """
                UPDATE suppliers
                SET name=%s, address=%s, phone=%s, contact_person=%s
                WHERE supplier_id=%s;
            """,
            (data["name"], data["address"], data.get("phone"), data.get("contact_person"), supplier_id),
        )

    def update_book(self, book_id: int, **data: Any) -> None:
        data = self._prepare_book_data(data)
        self._validate_book_isbn_unique(data["isbn"], book_id)
        with get_connection() as connection:
            try:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(
                        """
                            UPDATE books
                            SET isbn=%s, title=%s, publication_year=%s, publisher_id=%s, genre_id=%s,
                                language=%s, page_count=%s, cover_path=%s
                            WHERE book_id=%s;
                        """,
                        (
                            data["isbn"], data["title"], data["publication_year"], data["publisher_id"],
                            data["genre_id"], data["language"], data["page_count"], data.get("cover_path"), book_id,
                        ),
                    )
                    self._replace_book_authors(cursor, book_id, data["author_ids"])
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def update_copy(self, copy_id: int, **data: Any) -> None:
        data = self._prepare_copy_data(data)
        self._execute_write(
            """
                UPDATE copies
                SET book_id=%s, receipt_id=%s, arrival_date=%s, condition_state=%s, status=%s, storage_location=%s
                WHERE copy_id=%s;
            """,
            (data["book_id"], data["receipt_id"], data["arrival_date"], data["condition_state"], data["status"], data["storage_location"], copy_id),
        )

    def update_receipt(self, receipt_id: int, **data: Any) -> None:
        data = self._prepare_receipt_data(data)
        with get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                            UPDATE receipts
                            SET supplier_id=%s, employee_id=%s, receipt_date=%s, invoice_number=%s, total_amount=%s
                            WHERE receipt_id=%s;
                        """,
                        (data["supplier_id"], data["employee_id"], data["receipt_date"], data["invoice_number"], data["total_amount"], receipt_id),
                    )
                    self._replace_receipt_items(cursor, receipt_id, data["items"])
                    self._ensure_receipt_copies(cursor, receipt_id, data["receipt_date"], data["items"])
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def issue_book(
        self,
        *,
        reader_id: int,
        book_id: int,
        employee_id: int,
        issue_date: date,
        planned_return_date: date,
    ) -> tuple[int, int]:
        if planned_return_date < issue_date:
            raise ValueError("Плановая дата возврата не может быть раньше даты выдачи.")

        with get_connection() as connection:
            try:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute("SELECT status FROM readers WHERE reader_id = %s;", (reader_id,))
                    reader = cursor.fetchone()
                    if reader is None:
                        raise ValueError(f"Читатель с кодом {reader_id} не найден.")
                    if str(reader["status"]).lower() != "активен":
                        raise ValueError("Новая выдача разрешена только активному читателю.")

                    cursor.execute("SELECT get_available_copies_count(%s) AS available_copies;", (book_id,))
                    available = int(cursor.fetchone()["available_copies"])
                    if available <= 0:
                        raise ValueError("Для выбранной книги нет доступных экземпляров.")

                    cursor.execute(
                        """
                            SELECT copy_id
                            FROM copies
                            WHERE book_id = %s AND status = 'доступен'
                            ORDER BY copy_id
                            LIMIT 1
                            FOR UPDATE;
                        """,
                        (book_id,),
                    )
                    copy = cursor.fetchone()
                    if copy is None:
                        raise ValueError("Не удалось найти доступный экземпляр выбранной книги.")

                    copy_id = int(copy["copy_id"])
                    cursor.execute(
                        """
                            INSERT INTO issues (
                                reader_id, copy_id, employee_id, issue_date, planned_return_date, issue_status
                            )
                            VALUES (%s, %s, %s, %s, %s, 'активна')
                            RETURNING issue_id;
                        """,
                        (reader_id, copy_id, employee_id, issue_date, planned_return_date),
                    )
                    issue_id = int(cursor.fetchone()["issue_id"])
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return issue_id, copy_id

    # ----------------------------- Валидация -----------------------------

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        value = (phone or "").strip()
        if not value:
            return None

        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        elif len(digits) == 11 and digits.startswith("7"):
            pass
        else:
            raise ValueError("Телефон должен содержать 10 цифр или российский номер из 11 цифр.")

        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

    def _prepare_reader_data(self, data: Row) -> Row:
        return {
            "last_name": self._required_text(data.get("last_name"), "Фамилия", 30),
            "first_name": self._required_text(data.get("first_name"), "Имя", 20),
            "middle_name": self._optional_text(data.get("middle_name"), 30),
            "phone": self.normalize_phone(data.get("phone")),
            "registration_date": data.get("registration_date") or date.today(),
            "category": self._required_text(data.get("category") or "читатель", "Категория", 20),
            "status": self._required_text(data.get("status") or "активен", "Статус", 15),
        }

    def _prepare_employee_data(self, data: Row) -> Row:
        return {
            "last_name": self._required_text(data.get("last_name"), "Фамилия", 30),
            "first_name": self._required_text(data.get("first_name"), "Имя", 20),
            "middle_name": self._optional_text(data.get("middle_name"), 30),
            "position": self._required_text(data.get("position"), "Должность", 30),
            "phone": self.normalize_phone(data.get("phone")),
        }

    def _prepare_author_data(self, data: Row) -> Row:
        return {
            "last_name": self._required_text(data.get("last_name"), "Фамилия", 30),
            "first_name": self._required_text(data.get("first_name"), "Имя", 20),
            "middle_name": self._optional_text(data.get("middle_name"), 30),
            "birth_date": data.get("birth_date"),
        }

    def _prepare_publisher_data(self, data: Row) -> Row:
        return {
            "name": self._required_text(data.get("name"), "Наименование", 50),
            "city": self._required_text(data.get("city"), "Город", 30),
            "phone": self.normalize_phone(data.get("phone")),
        }

    def _prepare_genre_data(self, data: Row) -> Row:
        return {
            "name": self._required_text(data.get("name"), "Наименование", 30),
            "description": self._optional_text(data.get("description"), 100),
        }

    def _prepare_supplier_data(self, data: Row) -> Row:
        return {
            "name": self._required_text(data.get("name"), "Наименование", 60),
            "address": self._required_text(data.get("address"), "Адрес", 255),
            "phone": self.normalize_phone(data.get("phone")),
            "contact_person": self._optional_text(data.get("contact_person"), 127),
        }

    def _prepare_book_data(self, data: Row) -> Row:
        author_ids = [int(value) for value in data.get("author_ids", [])]
        if not author_ids:
            raise ValueError("Для книги необходимо выбрать хотя бы одного автора.")
        return {
            "isbn": self._required_text(data.get("isbn"), "ISBN", 17),
            "title": self._required_text(data.get("title"), "Название", 100),
            "publication_year": self._positive_int(data.get("publication_year"), "Год издания", allow_zero=True),
            "publisher_id": self._positive_int(data.get("publisher_id"), "Издательство"),
            "genre_id": self._positive_int(data.get("genre_id"), "Жанр"),
            "language": self._required_text(data.get("language") or "русский", "Язык", 20),
            "page_count": self._positive_int(data.get("page_count"), "Количество страниц"),
            "cover_path": self._optional_text(data.get("cover_path"), 255),
            "author_ids": author_ids,
        }

    def _prepare_copy_data(self, data: Row) -> Row:
        return {
            "book_id": self._positive_int(data.get("book_id"), "Книга"),
            "receipt_id": self._positive_int(data.get("receipt_id"), "Поступление"),
            "arrival_date": data.get("arrival_date") or date.today(),
            "condition_state": self._required_text(data.get("condition_state") or "новое", "Состояние", 20),
            "status": self._required_text(data.get("status") or "доступен", "Статус", 20),
            "storage_location": self._required_text(data.get("storage_location"), "Место хранения", 30),
        }

    def _prepare_receipt_data(self, data: Row) -> Row:
        items = self._prepare_receipt_items(data.get("items") or [])
        total_amount = sum((item["quantity"] * item["unit_price"] for item in items), Decimal("0.00"))
        return {
            "supplier_id": self._positive_int(data.get("supplier_id"), "Поставщик"),
            "employee_id": self._positive_int(data.get("employee_id"), "Сотрудник"),
            "receipt_date": data.get("receipt_date") or date.today(),
            "invoice_number": self._required_text(data.get("invoice_number"), "Номер накладной", 20),
            "total_amount": total_amount,
            "items": items,
        }

    def _prepare_receipt_items(self, items: Iterable[Row]) -> list[Row]:
        prepared_items: list[Row] = []
        used_book_ids: set[int] = set()
        for item in items:
            book_id = self._positive_int(item.get("book_id"), "Книга")
            if book_id in used_book_ids:
                raise ValueError("Одна и та же книга не должна повторяться в составе поступления.")
            used_book_ids.add(book_id)
            quantity = self._positive_int(item.get("quantity"), "Количество")
            try:
                unit_price = Decimal(str(item.get("unit_price")).replace(",", "."))
            except Exception as exc:
                raise ValueError("Цена за единицу должна быть числом.") from exc
            if unit_price < 0:
                raise ValueError("Цена за единицу не может быть отрицательной.")
            prepared_items.append(
                {
                    "book_id": book_id,
                    "quantity": quantity,
                    "unit_price": unit_price.quantize(Decimal("0.01")),
                }
            )
        if not prepared_items:
            raise ValueError("В составе поступления должна быть хотя бы одна позиция.")
        return prepared_items

    @staticmethod
    def _required_text(value: Any, field_name: str, max_length: int) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"Поле «{field_name}» обязательно для заполнения.")
        if len(text) > max_length:
            raise ValueError(f"Поле «{field_name}» не должно быть длиннее {max_length} символов.")
        return text

    @staticmethod
    def _optional_text(value: Any, max_length: int) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        if len(text) > max_length:
            raise ValueError(f"Значение не должно быть длиннее {max_length} символов.")
        return text

    @staticmethod
    def _positive_int(value: Any, field_name: str, *, allow_zero: bool = False) -> int:
        try:
            number = int(str(value).strip())
        except Exception as exc:
            raise ValueError(f"Поле «{field_name}» должно быть целым числом.") from exc
        if allow_zero:
            if number < 0:
                raise ValueError(f"Поле «{field_name}» не может быть отрицательным.")
        elif number <= 0:
            raise ValueError(f"Поле «{field_name}» должно быть положительным числом.")
        return number

    def _validate_unique_phone(
        self,
        table_name: str,
        id_column: str,
        phone: str | None,
        current_id: int | None = None,
    ) -> None:
        if phone is None:
            return
        self._validate_unique_value(table_name, id_column, "phone", phone, current_id, "Телефон уже используется в этой таблице.")

    def _validate_unique_name(
        self,
        table_name: str,
        id_column: str,
        name: str,
        current_id: int | None = None,
    ) -> None:
        self._validate_unique_value(
            table_name,
            id_column,
            "name",
            name,
            current_id,
            "Запись с таким наименованием уже существует.",
            case_insensitive=True,
        )

    def _validate_book_isbn_unique(self, isbn: str, current_id: int | None = None) -> None:
        self._validate_unique_value("books", "book_id", "isbn", isbn, current_id, "Книга с таким ISBN уже существует.")

    def _validate_author_duplicate(self, data: Row, current_id: int | None = None) -> None:
        query = """
            SELECT author_id
            FROM authors
            WHERE LOWER(last_name) = LOWER(%s)
              AND LOWER(first_name) = LOWER(%s)
              AND COALESCE(LOWER(middle_name), '') = COALESCE(LOWER(%s), '')
              AND COALESCE(birth_date, DATE '0001-01-01') = COALESCE(%s::date, DATE '0001-01-01')
        """
        params: list[Any] = [data["last_name"], data["first_name"], data.get("middle_name"), data.get("birth_date")]
        if current_id is not None:
            query += " AND author_id <> %s"
            params.append(current_id)
        rows = self._fetch_all(query + " LIMIT 1;", tuple(params))
        if rows:
            raise ValueError("Автор с таким Ф.И.О. и датой рождения уже существует.")

    def _validate_unique_value(
        self,
        table_name: str,
        id_column: str,
        value_column: str,
        value: str,
        current_id: int | None,
        message: str,
        *,
        case_insensitive: bool = False,
    ) -> None:
        # Имена таблиц и колонок передаются только из кода приложения, а не из пользовательского ввода.
        if case_insensitive:
            condition = f"LOWER({value_column}) = LOWER(%s)"
        else:
            condition = f"{value_column} = %s"
        query = f"SELECT {id_column} FROM {table_name} WHERE {condition}"
        params: list[Any] = [value]
        if current_id is not None:
            query += f" AND {id_column} <> %s"
            params.append(current_id)
        query += " LIMIT 1;"
        if self._fetch_all(query, tuple(params)):
            raise ValueError(message)

    # ----------------------------- Низкоуровневые методы -----------------------------

    def _replace_book_authors(self, cursor: Any, book_id: int, author_ids: Iterable[int]) -> None:
        cursor.execute("DELETE FROM book_authors WHERE book_id = %s;", (book_id,))
        for author_id in sorted(set(author_ids)):
            cursor.execute(
                "INSERT INTO book_authors (book_id, author_id) VALUES (%s, %s);",
                (book_id, int(author_id)),
            )

    def _replace_receipt_items(self, cursor: Any, receipt_id: int, items: Iterable[Row]) -> None:
        cursor.execute("DELETE FROM receipt_items WHERE receipt_id = %s;", (receipt_id,))
        for item in items:
            cursor.execute(
                """
                    INSERT INTO receipt_items (receipt_id, book_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s);
                """,
                (receipt_id, item["book_id"], item["quantity"], item["unit_price"]),
            )

    def _ensure_receipt_copies(self, cursor: Any, receipt_id: int, receipt_date: date, items: Iterable[Row]) -> None:
        for item in items:
            book_id = int(item["book_id"])
            required_quantity = int(item["quantity"])
            cursor.execute(
                """
                    SELECT COUNT(*) AS existing_count
                    FROM copies
                    WHERE receipt_id = %s AND book_id = %s;
                """,
                (receipt_id, book_id),
            )
            row = cursor.fetchone()
            existing_count = int(row["existing_count"] if isinstance(row, dict) else row[0])
            missing_count = required_quantity - existing_count
            for _ in range(max(missing_count, 0)):
                cursor.execute(
                    """
                        INSERT INTO copies (
                            book_id, receipt_id, arrival_date, condition_state, status, storage_location
                        )
                        VALUES (%s, %s, %s, 'новое', 'доступен', 'Абонемент A-01');
                    """,
                    (book_id, receipt_id, receipt_date),
                )

    def _insert_returning_id(self, query: str, params: tuple[Any, ...]) -> int:
        with get_connection() as connection:
            try:
                with connection.cursor(row_factory=dict_row) as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return int(next(iter(row.values())))

    def _execute_write(self, query: str, params: tuple[Any, ...]) -> None:
        with get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[Row]:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
        return [dict(row) for row in rows]
