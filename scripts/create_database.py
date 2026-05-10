from app.services.database_initializer import create_database_if_not_exists, create_schema


def main() -> None:
    database_created = create_database_if_not_exists()
    create_schema()

    if database_created:
        print("База данных успешно создана и схема инициализирована.")
    else:
        print("База данных уже существовала. Схема обновлена/проверена.")


if __name__ == "__main__":
    main()
