from app.services.server_objects_initializer import create_server_objects


def main() -> None:
    create_server_objects()
    print("Серверные объекты базы данных успешно созданы.")


if __name__ == "__main__":
    main()
