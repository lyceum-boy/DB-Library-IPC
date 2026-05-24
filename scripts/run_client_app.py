from app.services.server_objects_initializer import create_server_objects
from app.ui.main_window import run_application


def main() -> int:
    # Создание серверных объектов не удаляет пользовательские данные и позволяет
    # запустить приложение после развёртывания БД без ручного шага в pgAdmin 4.
    create_server_objects()
    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
