# Заглушки для трёх запросов.

QUERY_1_NAME = "Запрос 1"
QUERY_1_SQL = None

QUERY_2_NAME = "Запрос 2"
QUERY_2_SQL = None

QUERY_3_NAME = "Запрос 3"
QUERY_3_SQL = None


def iter_queries() -> list[tuple[str, str | None]]:
    return [
        (QUERY_1_NAME, QUERY_1_SQL),
        (QUERY_2_NAME, QUERY_2_SQL),
        (QUERY_3_NAME, QUERY_3_SQL),
    ]
