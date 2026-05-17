"""SQL-код создания хранимых функций базы данных библиотеки."""

FUNCTIONS_STATEMENTS: list[str] = [
    """
    CREATE OR REPLACE FUNCTION get_available_copies_count(p_book_id integer)
    RETURNS integer
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_available_count integer;
    BEGIN
        SELECT COUNT(*)
        INTO v_available_count
        FROM copies
        WHERE
            book_id = p_book_id
            AND status = 'доступен';

        RETURN v_available_count;
    END;
    $$;
    """,
    """
    CREATE OR REPLACE FUNCTION get_reader_active_issues_count(p_reader_id integer)
    RETURNS integer
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_active_count integer;
    BEGIN
        SELECT COUNT(*)
        INTO v_active_count
        FROM issues
        WHERE
            reader_id = p_reader_id
            AND issue_status = 'активна'
            AND actual_return_date IS NULL;

        RETURN v_active_count;
    END;
    $$;
    """,
]
