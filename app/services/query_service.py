from app.db import get_connection
from app.sql.queries import iter_queries


def run_configured_queries() -> None:
    for query_name, query_sql in iter_queries():
        print(f"\n=== {query_name} ===")
        if not query_sql:
            print("Запрос пока не задан преподавателем.")
            continue

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_sql)
                rows = cursor.fetchall()
                for row in rows:
                    print(row)
