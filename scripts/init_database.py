# -*- coding: utf-8 -*-

from app.services.database_initializer import create_database_if_not_exists, create_schema
from app.services.seed_loader import load_seed_data


def main() -> None:
    database_created = create_database_if_not_exists()
    create_schema()
    load_seed_data()

    if database_created:
        print("База данных создана, схема и начальные данные загружены.")
    else:
        print("База данных уже существовала. Схема проверена и данные перезагружены.")


if __name__ == "__main__":
    main()
