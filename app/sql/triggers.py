"""SQL-код создания триггеров и триггерных функций базы данных библиотеки."""

TRIGGER_STATEMENTS: list[str] = [
    """
    CREATE OR REPLACE FUNCTION sync_copy_status_after_issue_change()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF TG_OP = 'UPDATE' AND OLD.copy_id <> NEW.copy_id THEN
            UPDATE copies
            SET status = 'доступен'
            WHERE
                copy_id = OLD.copy_id
                AND status <> 'списан';
        END IF;

        IF NEW.issue_status = 'активна' AND NEW.actual_return_date IS NULL THEN
            UPDATE copies
            SET status = 'выдан'
            WHERE copy_id = NEW.copy_id;
        ELSIF NEW.issue_status = 'закрыта' AND NEW.actual_return_date IS NOT NULL THEN
            UPDATE copies
            SET status = 'доступен'
            WHERE
                copy_id = NEW.copy_id
                AND status <> 'списан';
        END IF;

        RETURN NEW;
    END;
    $$;
    """,
    "DROP TRIGGER IF EXISTS trg_sync_copy_status_after_issue_change ON issues;",
    """
    CREATE TRIGGER trg_sync_copy_status_after_issue_change
    AFTER INSERT OR UPDATE OF copy_id, issue_status, actual_return_date
    ON issues
    FOR EACH ROW
    EXECUTE FUNCTION sync_copy_status_after_issue_change();
    """,
]
