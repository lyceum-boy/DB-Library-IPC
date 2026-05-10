import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "5432"))
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")
    database: str = os.getenv("PG_DATABASE", "library_db")
    admin_database: str = os.getenv("PG_ADMIN_DATABASE", "postgres")


SETTINGS = DatabaseSettings()
