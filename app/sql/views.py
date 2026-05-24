"""SQL-код создания представлений базы данных библиотеки."""

VIEWS_STATEMENTS: list[str] = [
    """
    CREATE OR REPLACE VIEW view_books_catalog AS
    WITH authors_by_book AS (
        SELECT
            ba.book_id,
            STRING_AGG(
                CONCAT_WS(' ', a.last_name, a.first_name, a.middle_name),
                ', '
                ORDER BY a.last_name, a.first_name, a.middle_name
            ) AS authors
        FROM book_authors ba
        JOIN authors a ON ba.author_id = a.author_id
        GROUP BY ba.book_id
    ),
    copies_by_book AS (
        SELECT
            c.book_id,
            COUNT(*) AS total_copies,
            COUNT(*) FILTER (WHERE c.status = 'доступен') AS available_copies,
            COUNT(*) FILTER (WHERE c.status = 'выдан') AS issued_copies,
            COUNT(*) FILTER (WHERE c.status = 'забронирован') AS reserved_copies,
            COUNT(*) FILTER (WHERE c.status = 'на реставрации') AS restoration_copies,
            COUNT(*) FILTER (WHERE c.status = 'списан') AS written_off_copies
        FROM copies c
        GROUP BY c.book_id
    )
    SELECT
        b.book_id,
        b.title AS book_title,
        COALESCE(ab.authors, '–') AS authors,
        g.name AS genre,
        p.name AS publisher,
        b.publication_year,
        b.isbn,
        b.language,
        b.page_count,
        b.cover_path,
        COALESCE(cb.total_copies, 0) AS total_copies,
        COALESCE(cb.available_copies, 0) AS available_copies,
        COALESCE(cb.issued_copies, 0) AS issued_copies,
        COALESCE(cb.reserved_copies, 0) AS reserved_copies,
        COALESCE(cb.restoration_copies, 0) AS restoration_copies,
        COALESCE(cb.written_off_copies, 0) AS written_off_copies
    FROM books b
    JOIN publishers p ON b.publisher_id = p.publisher_id
    JOIN genres g ON b.genre_id = g.genre_id
    LEFT JOIN authors_by_book ab ON b.book_id = ab.book_id
    LEFT JOIN copies_by_book cb ON b.book_id = cb.book_id;
    """,
    """
    CREATE OR REPLACE VIEW view_active_issues AS
    SELECT
        i.issue_id,
        r.reader_id,
        CONCAT_WS(' ', r.last_name, r.first_name, r.middle_name) AS reader_full_name,
        b.book_id,
        b.title AS book_title,
        c.copy_id,
        e.employee_id,
        CONCAT_WS(' ', e.last_name, e.first_name, e.middle_name) AS employee_full_name,
        i.issue_date,
        i.planned_return_date,
        CURRENT_DATE - i.planned_return_date AS days_overdue,
        CASE
            WHEN i.planned_return_date < CURRENT_DATE THEN 'просрочена'
            ELSE 'в срок'
        END AS return_state
    FROM issues i
    JOIN readers r ON i.reader_id = r.reader_id
    JOIN copies c ON i.copy_id = c.copy_id
    JOIN books b ON c.book_id = b.book_id
    JOIN employees e ON i.employee_id = e.employee_id
    WHERE
        i.issue_status = 'активна'
        AND i.actual_return_date IS NULL;
    """,
]
