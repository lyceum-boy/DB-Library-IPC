from app.services.seed_loader import load_seed_data


def main() -> None:
    load_seed_data()
    print("Начальные данные успешно загружены в базу данных.")


if __name__ == "__main__":
    main()
