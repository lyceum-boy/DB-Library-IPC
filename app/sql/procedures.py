"""SQL-код создания хранимой процедуры базы данных библиотеки."""

PROCEDURES_STATEMENTS: list[str] = [
    """
    CREATE OR REPLACE PROCEDURE return_book(
        p_issue_id integer,
        p_return_date date DEFAULT CURRENT_DATE
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_issue issues%ROWTYPE;
    BEGIN
        SELECT *
        INTO v_issue
        FROM issues
        WHERE issue_id = p_issue_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Выдача с идентификатором % не найдена', p_issue_id;
        END IF;

        IF v_issue.issue_status <> 'активна' OR v_issue.actual_return_date IS NOT NULL THEN
            RAISE EXCEPTION 'Выдача с идентификатором % уже закрыта', p_issue_id;
        END IF;

        IF p_return_date < v_issue.issue_date THEN
            RAISE EXCEPTION 'Дата возврата % не может быть раньше даты выдачи %',
                p_return_date,
                v_issue.issue_date;
        END IF;

        UPDATE issues
        SET
            actual_return_date = p_return_date,
            issue_status = 'закрыта'
        WHERE issue_id = p_issue_id;
    END;
    $$;
    """,
]
