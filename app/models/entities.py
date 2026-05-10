from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Reader:
    reader_id: int
    last_name: str
    first_name: str
    middle_name: str | None
    phone: str | None
    registration_date: date
    category: str
    status: str


@dataclass(slots=True)
class Employee:
    employee_id: int
    last_name: str
    first_name: str
    middle_name: str | None
    position: str
    phone: str | None


@dataclass(slots=True)
class Author:
    author_id: int
    last_name: str
    first_name: str
    middle_name: str | None
    birth_date: date | None


@dataclass(slots=True)
class Publisher:
    publisher_id: int
    name: str
    city: str
    phone: str | None


@dataclass(slots=True)
class Genre:
    genre_id: int
    name: str
    description: str | None


@dataclass(slots=True)
class Book:
    book_id: int
    isbn: str
    title: str
    publication_year: int
    publisher_id: int
    genre_id: int
    language: str
    page_count: int
    cover_path: str | None


@dataclass(slots=True)
class Copy:
    copy_id: int
    book_id: int
    receipt_id: int
    arrival_date: date
    condition_state: str
    status: str
    storage_location: str


@dataclass(slots=True)
class Supplier:
    supplier_id: int
    name: str
    address: str
    phone: str | None
    contact_person: str | None


@dataclass(slots=True)
class Receipt:
    receipt_id: int
    supplier_id: int
    employee_id: int
    receipt_date: date
    invoice_number: str
    total_amount: float


@dataclass(slots=True)
class Issue:
    issue_id: int
    reader_id: int
    copy_id: int
    employee_id: int
    issue_date: date
    planned_return_date: date
    actual_return_date: date | None
    issue_status: str


@dataclass(slots=True)
class BookAuthor:
    book_id: int
    author_id: int


@dataclass(slots=True)
class ReceiptItem:
    receipt_id: int
    book_id: int
    quantity: int
    unit_price: float
