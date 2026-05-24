"""Главное окно клиентского приложения библиотеки."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.services.client_repository import LibraryRepository

FieldSpec = dict[str, Any]
EntitySpec = dict[str, Any]

SORT_ROLE = Qt.ItemDataRole.UserRole.value + 1


class SortableTableItem(QTableWidgetItem):
    """Элемент таблицы с корректной сортировкой чисел, дат и строк."""

    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE)
        if left is None:
            left = (0, "")
        if right is None:
            right = (0, "")
        return left < right


class RecordDialog(QDialog):
    """Универсальная форма добавления или редактирования простой сущности."""

    def __init__(
        self,
        *,
        title: str,
        fields: list[FieldSpec],
        initial: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.fields = fields
        self.widgets: dict[str, Any] = {}
        self.setWindowTitle(title)
        self.resize(460, 260)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        initial = initial or {}

        for field in fields:
            name = field["name"]
            field_type = field.get("type", "text")
            value = initial.get(name, field.get("default"))

            if field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(self._to_qdate(value))
            elif field_type == "combo":
                widget = QComboBox()
                for item in field.get("choices", []):
                    widget.addItem(str(item), item)
                self._set_combo_value(widget, value)
            elif field_type == "lookup":
                widget = QComboBox()
                for row in field["items"]():
                    widget.addItem(field["text_factory"](row), int(row[field["id_key"]]))
                self._set_combo_value(widget, value)
            else:
                widget = QLineEdit()
                if value is not None:
                    widget.setText(str(value))
                if field.get("placeholder"):
                    widget.setPlaceholderText(field["placeholder"])

            self.widgets[name] = widget
            label = field["label"] + ("*:" if field.get("required") else ":")
            form.addRow(label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field in self.fields:
            name = field["name"]
            widget = self.widgets[name]
            field_type = field.get("type", "text")
            if field_type == "date":
                qdate = widget.date()
                data[name] = date(qdate.year(), qdate.month(), qdate.day())
            elif field_type in {"combo", "lookup"}:
                data[name] = widget.currentData()
            else:
                data[name] = widget.text()
        return data

    @staticmethod
    def _to_qdate(value: Any) -> QDate:
        if isinstance(value, date):
            return QDate(value.year, value.month, value.day)
        if value:
            try:
                parsed = date.fromisoformat(str(value))
                return QDate(parsed.year, parsed.month, parsed.day)
            except ValueError:
                pass
        return QDate.currentDate()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: Any) -> None:
        if value is None:
            return
        index = combo.findData(value)
        if index < 0:
            try:
                index = combo.findData(int(value))
            except Exception:
                index = -1
        if index >= 0:
            combo.setCurrentIndex(index)


class BookDialog(QDialog):
    """Форма добавления или редактирования книги с выбором справочников."""

    def __init__(
        self,
        *,
        repository: LibraryRepository,
        parent_window: "LibraryMainWindow",
        initial: dict[str, Any] | None = None,
        title: str = "Книга",
    ) -> None:
        super().__init__(parent_window)
        self.repository = repository
        self.parent_window = parent_window
        self.initial = initial or {}
        self.setWindowTitle(title)
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.isbn_input = QLineEdit(str(self.initial.get("isbn") or ""))
        self.title_input = QLineEdit(str(self.initial.get("title") or self.initial.get("book_title") or ""))
        self.year_input = QLineEdit(str(self.initial.get("publication_year") or ""))
        self.language_input = QLineEdit(str(self.initial.get("language") or "русский"))
        self.page_count_input = QLineEdit(str(self.initial.get("page_count") or ""))
        self.cover_path_input = QLineEdit(str(self.initial.get("cover_path") or ""))

        cover_row = QHBoxLayout()
        cover_button = QPushButton("Выбрать файл...")
        cover_button.clicked.connect(self.browse_cover)
        cover_row.addWidget(self.cover_path_input, stretch=1)
        cover_row.addWidget(cover_button)

        self.publisher_combo = QComboBox()
        self.genre_combo = QComboBox()
        self.author_list = QListWidget()
        self.author_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.author_list.setMinimumHeight(170)

        publisher_row = self._combo_with_add_button(
            self.publisher_combo,
            "Добавить издательство",
            lambda: self._add_lookup_record("publishers"),
        )
        genre_row = self._combo_with_add_button(
            self.genre_combo,
            "Добавить жанр",
            lambda: self._add_lookup_record("genres"),
        )
        author_button = QPushButton("Добавить автора")
        author_button.clicked.connect(lambda: self._add_lookup_record("authors"))

        form.addRow("ISBN*:", self.isbn_input)
        form.addRow("Название*:", self.title_input)
        form.addRow("Год издания*:", self.year_input)
        form.addRow("Издательство*:", publisher_row)
        form.addRow("Жанр*:", genre_row)
        form.addRow("Язык*:", self.language_input)
        form.addRow("Страниц*:", self.page_count_input)
        form.addRow("Путь к обложке:", cover_row)
        form.addRow("Авторы*:", self.author_list)
        form.addRow(author_button)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)
        self.reload_lookups()

    def browse_cover(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл обложки",
            str(self.parent_window.project_root),
            "Images (*.png *.jpg *.jpeg *.webp);;All files (*.*)",
        )
        if not filename:
            return
        path = Path(filename)
        try:
            relative = path.relative_to(self.parent_window.project_root)
            self.cover_path_input.setText(str(relative).replace("\\", "/"))
        except ValueError:
            self.cover_path_input.setText(str(path))

    def reload_lookups(self) -> None:
        publisher_id = self.publisher_combo.currentData() or self.initial.get("publisher_id")
        genre_id = self.genre_combo.currentData() or self.initial.get("genre_id")
        selected_authors = self.selected_author_ids() or list(self.initial.get("author_ids") or [])

        self.publisher_combo.clear()
        for row in self.repository.fetch_publishers():
            self.publisher_combo.addItem(f"{row['publisher_id']} – {row['name']} ({row['city']})", int(row["publisher_id"]))
        self._set_combo_value(self.publisher_combo, publisher_id)

        self.genre_combo.clear()
        for row in self.repository.fetch_genres():
            self.genre_combo.addItem(f"{row['genre_id']} – {row['name']}", int(row["genre_id"]))
        self._set_combo_value(self.genre_combo, genre_id)

        self.author_list.clear()
        for row in self.repository.fetch_authors():
            item = QListWidgetItem(f"{row['author_id']} – {row['author_full_name']}")
            author_id = int(row["author_id"])
            item.setData(Qt.ItemDataRole.UserRole, author_id)
            self.author_list.addItem(item)
            if author_id in selected_authors:
                item.setSelected(True)

    def selected_author_ids(self) -> list[int]:
        return [int(item.data(Qt.ItemDataRole.UserRole)) for item in self.author_list.selectedItems()]

    def get_data(self) -> dict[str, Any]:
        return {
            "isbn": self.isbn_input.text(),
            "title": self.title_input.text(),
            "publication_year": self.year_input.text(),
            "publisher_id": self.publisher_combo.currentData(),
            "genre_id": self.genre_combo.currentData(),
            "language": self.language_input.text(),
            "page_count": self.page_count_input.text(),
            "cover_path": self.cover_path_input.text(),
            "author_ids": self.selected_author_ids(),
        }

    def _add_lookup_record(self, entity_key: str) -> None:
        new_id = self.parent_window.add_entity_record(entity_key, show_success=False)
        if new_id is not None:
            self.reload_lookups()

    @staticmethod
    def _combo_with_add_button(combo: QComboBox, button_text: str, callback: Callable[[], None]) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton(button_text)
        button.clicked.connect(callback)
        layout.addWidget(combo, stretch=1)
        layout.addWidget(button)
        return widget

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: Any) -> None:
        if value is None:
            return
        try:
            value = int(value)
        except Exception:
            pass
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)


class ReceiptDialog(QDialog):
    """Форма поступления с обязательным составом."""

    def __init__(
        self,
        *,
        repository: LibraryRepository,
        initial: dict[str, Any] | None = None,
        title: str = "Поступление",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.initial = initial or {}
        self.setWindowTitle(title)
        self.resize(860, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.supplier_combo = QComboBox()
        self.employee_combo = QComboBox()
        self.receipt_date_input = QDateEdit()
        self.receipt_date_input.setCalendarPopup(True)
        self.receipt_date_input.setDate(RecordDialog._to_qdate(self.initial.get("receipt_date")))
        self.invoice_number_input = QLineEdit(str(self.initial.get("invoice_number") or ""))

        form.addRow("Поставщик*:", self.supplier_combo)
        form.addRow("Сотрудник*:", self.employee_combo)
        form.addRow("Дата поступления*:", self.receipt_date_input)
        form.addRow("Номер накладной*:", self.invoice_number_input)

        items_group = QGroupBox("Состав поступления")
        items_layout = QVBoxLayout(items_group)

        buttons_layout = QHBoxLayout()
        add_item_button = QPushButton("Добавить позицию")
        remove_item_button = QPushButton("Удалить позицию из формы")
        add_item_button.clicked.connect(lambda: self._append_item_row())
        remove_item_button.clicked.connect(self._remove_selected_item_row)
        buttons_layout.addWidget(add_item_button)
        buttons_layout.addWidget(remove_item_button)
        buttons_layout.addStretch(1)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["Книга", "Количество", "Цена за единицу"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.total_label = QLabel("Итого: 0.00")
        items_layout.addLayout(buttons_layout)
        items_layout.addWidget(self.items_table)
        items_layout.addWidget(self.total_label)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(items_group)
        layout.addWidget(dialog_buttons)

        self.reload_lookups()
        for item in self.initial.get("items") or []:
            self._append_item_row(item)
        if self.items_table.rowCount() == 0:
            self._append_item_row()
        self._update_total_label()

    def reload_lookups(self) -> None:
        supplier_id = self.initial.get("supplier_id")
        employee_id = self.initial.get("employee_id")

        self.supplier_combo.clear()
        for row in self.repository.fetch_suppliers():
            self.supplier_combo.addItem(f"{row['supplier_id']} – {row['name']}", int(row["supplier_id"]))
        RecordDialog._set_combo_value(self.supplier_combo, supplier_id)

        self.employee_combo.clear()
        for row in self.repository.fetch_employees():
            self.employee_combo.addItem(f"{row['employee_id']} – {row['employee_full_name']}", int(row["employee_id"]))
        RecordDialog._set_combo_value(self.employee_combo, employee_id)

    def get_data(self) -> dict[str, Any]:
        qdate = self.receipt_date_input.date()
        return {
            "supplier_id": self.supplier_combo.currentData(),
            "employee_id": self.employee_combo.currentData(),
            "receipt_date": date(qdate.year(), qdate.month(), qdate.day()),
            "invoice_number": self.invoice_number_input.text(),
            "items": self._collect_items(),
        }

    def _append_item_row(self, item: dict[str, Any] | None = None) -> None:
        item = item or {}
        row_index = self.items_table.rowCount()
        self.items_table.insertRow(row_index)

        book_combo = QComboBox()
        for book in self.repository.fetch_books_for_lookup():
            book_combo.addItem(f"{book['book_id']} – {book['book_title']}", int(book["book_id"]))
        RecordDialog._set_combo_value(book_combo, item.get("book_id"))
        book_combo.currentIndexChanged.connect(self._update_total_label)

        quantity_spin = QSpinBox()
        quantity_spin.setRange(1, 9999)
        quantity_spin.setValue(int(item.get("quantity") or 1))
        quantity_spin.valueChanged.connect(self._update_total_label)

        unit_price_spin = QDoubleSpinBox()
        unit_price_spin.setRange(0, 999999.99)
        unit_price_spin.setDecimals(2)
        unit_price_spin.setSingleStep(10.0)
        unit_price_spin.setValue(float(item.get("unit_price") or 0))
        unit_price_spin.valueChanged.connect(self._update_total_label)

        self.items_table.setCellWidget(row_index, 0, book_combo)
        self.items_table.setCellWidget(row_index, 1, quantity_spin)
        self.items_table.setCellWidget(row_index, 2, unit_price_spin)
        self._update_total_label()

    def _remove_selected_item_row(self) -> None:
        selected = self.items_table.selectionModel().selectedRows() if self.items_table.selectionModel() else []
        if selected:
            self.items_table.removeRow(selected[0].row())
            self._update_total_label()

    def _collect_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row_index in range(self.items_table.rowCount()):
            book_combo = self.items_table.cellWidget(row_index, 0)
            quantity_spin = self.items_table.cellWidget(row_index, 1)
            unit_price_spin = self.items_table.cellWidget(row_index, 2)
            if not isinstance(book_combo, QComboBox) or not isinstance(quantity_spin, QSpinBox) or not isinstance(unit_price_spin, QDoubleSpinBox):
                continue
            items.append(
                {
                    "book_id": book_combo.currentData(),
                    "quantity": quantity_spin.value(),
                    "unit_price": unit_price_spin.value(),
                }
            )
        return items

    def _update_total_label(self) -> None:
        total = 0.0
        for item in self._collect_items():
            total += float(item["quantity"]) * float(item["unit_price"])
        self.total_label.setText(f"Итого: {total:.2f}")


class LibraryMainWindow(QMainWindow):
    """Главное окно десктопного приложения автоматизированного ИПК библиотеки."""

    def __init__(self) -> None:
        super().__init__()
        self.repository = LibraryRepository()
        self.project_root = Path(__file__).resolve().parents[2]
        self.current_entity_key = "readers"
        self.current_entity_rows: list[dict[str, Any]] = []

        self.icon_path = self.project_root / "resources" / "img" / "icon.png"
        self.setWindowTitle("ИПК «Библиотека»")
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))
        self.resize(1480, 900)

        self.entity_specs = self._build_entity_specs()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._create_catalog_tab()
        self._create_issues_tab()
        self._create_readers_tab()
        self._create_receipts_tab()
        self._create_entities_tab()
        self._create_help_tab()

        self.statusBar().showMessage("Подключение к БД настроено. Для обновления данных используйте кнопки на вкладках.")
        self.refresh_all()

    # ----------------------------- Инициализация -----------------------------

    def _build_entity_specs(self) -> dict[str, EntitySpec]:
        return {
            "readers": {
                "title": "читателя",
                "id_key": "reader_id",
                "fetch": self.repository.fetch_readers,
                "create": self.repository.create_reader,
                "update": self.repository.update_reader,
                "columns": [
                    ("reader_id", "Код"), ("reader_full_name", "Ф.И.О."), ("phone", "Телефон"),
                    ("registration_date", "Дата регистрации"), ("category", "Категория"), ("status", "Статус"),
                ],
                "fields": [
                    {"name": "last_name", "label": "Фамилия", "required": True},
                    {"name": "first_name", "label": "Имя", "required": True},
                    {"name": "middle_name", "label": "Отчество"},
                    {"name": "phone", "label": "Телефон", "placeholder": "+7 (921) 000-00-01"},
                    {"name": "registration_date", "label": "Дата регистрации", "type": "date", "default": date.today()},
                    {"name": "category", "label": "Категория", "type": "combo", "choices": ["студент", "преподаватель", "аспирант", "читатель"], "default": "студент"},
                    {"name": "status", "label": "Статус", "type": "combo", "choices": ["активен", "неактивен"], "default": "активен"},
                ],
            },
            "employees": {
                "title": "сотрудника",
                "id_key": "employee_id",
                "fetch": self.repository.fetch_employees,
                "create": self.repository.create_employee,
                "update": self.repository.update_employee,
                "columns": [
                    ("employee_id", "Код"), ("employee_full_name", "Ф.И.О."), ("position", "Должность"), ("phone", "Телефон"),
                ],
                "fields": [
                    {"name": "last_name", "label": "Фамилия", "required": True},
                    {"name": "first_name", "label": "Имя", "required": True},
                    {"name": "middle_name", "label": "Отчество"},
                    {"name": "position", "label": "Должность", "required": True},
                    {"name": "phone", "label": "Телефон", "placeholder": "+7 (812) 000-00-01"},
                ],
            },
            "authors": {
                "title": "автора",
                "id_key": "author_id",
                "fetch": self.repository.fetch_authors,
                "create": self.repository.create_author,
                "update": self.repository.update_author,
                "columns": [("author_id", "Код"), ("author_full_name", "Ф.И.О."), ("birth_date", "Дата рождения")],
                "fields": [
                    {"name": "last_name", "label": "Фамилия", "required": True},
                    {"name": "first_name", "label": "Имя", "required": True},
                    {"name": "middle_name", "label": "Отчество"},
                    {"name": "birth_date", "label": "Дата рождения", "type": "date"},
                ],
            },
            "publishers": {
                "title": "издательство",
                "id_key": "publisher_id",
                "fetch": self.repository.fetch_publishers,
                "create": self.repository.create_publisher,
                "update": self.repository.update_publisher,
                "columns": [("publisher_id", "Код"), ("name", "Наименование"), ("city", "Город"), ("phone", "Телефон")],
                "fields": [
                    {"name": "name", "label": "Наименование", "required": True},
                    {"name": "city", "label": "Город", "required": True},
                    {"name": "phone", "label": "Телефон", "placeholder": "+7 (495) 000-00-01"},
                ],
            },
            "genres": {
                "title": "жанр",
                "id_key": "genre_id",
                "fetch": self.repository.fetch_genres,
                "create": self.repository.create_genre,
                "update": self.repository.update_genre,
                "columns": [("genre_id", "Код"), ("name", "Наименование"), ("description", "Описание")],
                "fields": [
                    {"name": "name", "label": "Наименование", "required": True},
                    {"name": "description", "label": "Описание"},
                ],
            },
            "suppliers": {
                "title": "поставщика",
                "id_key": "supplier_id",
                "fetch": self.repository.fetch_suppliers,
                "create": self.repository.create_supplier,
                "update": self.repository.update_supplier,
                "columns": [
                    ("supplier_id", "Код"), ("name", "Наименование"), ("address", "Адрес"),
                    ("phone", "Телефон"), ("contact_person", "Контактное лицо"),
                ],
                "fields": [
                    {"name": "name", "label": "Наименование", "required": True},
                    {"name": "address", "label": "Адрес", "required": True},
                    {"name": "phone", "label": "Телефон", "placeholder": "+7 (812) 000-00-01"},
                    {"name": "contact_person", "label": "Контактное лицо"},
                ],
            },
            "books": {
                "title": "книгу",
                "id_key": "book_id",
                "fetch": self.repository.fetch_books_catalog,
                "create": self.repository.create_book,
                "update": self.repository.update_book,
                "columns": [
                    ("book_id", "Код"), ("book_title", "Название"), ("authors", "Авторы"),
                    ("genre", "Жанр"), ("publisher", "Издательство"), ("isbn", "ISBN"),
                    ("total_copies", "Экз."),
                ],
                "special_dialog": "book",
            },
            "copies": {
                "title": "экземпляр",
                "id_key": "copy_id",
                "fetch": self.repository.fetch_copies,
                "create": self.repository.create_copy,
                "update": self.repository.update_copy,
                "columns": [
                    ("copy_id", "№ экземпляра"), ("book_title", "Книга"), ("receipt_id", "№ поступления"),
                    ("arrival_date", "Дата поступления"), ("condition_state", "Состояние"),
                    ("status", "Статус"), ("storage_location", "Место хранения"),
                ],
                "fields": [
                    {"name": "book_id", "label": "Книга", "type": "lookup", "id_key": "book_id", "items": self.repository.fetch_books_for_lookup, "text_factory": lambda row: f"{row['book_id']} – {row['book_title']}"},
                    {"name": "receipt_id", "label": "Поступление", "type": "lookup", "id_key": "receipt_id", "items": self.repository.fetch_receipts_for_lookup, "text_factory": lambda row: f"{row['receipt_id']} – {row['invoice_number']} от {row['receipt_date']}"},
                    {"name": "arrival_date", "label": "Дата поступления", "type": "date", "default": date.today()},
                    {"name": "condition_state", "label": "Состояние", "type": "combo", "choices": ["новое", "хорошее", "удовлетворительное", "повреждено"], "default": "новое"},
                    {"name": "status", "label": "Статус", "type": "combo", "choices": ["доступен", "выдан", "забронирован", "на реставрации", "списан"], "default": "доступен"},
                    {"name": "storage_location", "label": "Место хранения", "required": True},
                ],
            },
            "receipts": {
                "title": "поступление",
                "id_key": "receipt_id",
                "fetch": self.repository.fetch_receipts,
                "create": self.repository.create_receipt,
                "update": self.repository.update_receipt,
                "columns": [
                    ("receipt_id", "№"), ("supplier_name", "Поставщик"), ("employee_full_name", "Сотрудник"),
                    ("receipt_date", "Дата"), ("invoice_number", "Накладная"), ("total_amount", "Сумма"),
                ],
                "special_dialog": "receipt",
            },
        }

    def refresh_all(self) -> None:
        self.refresh_catalog()
        self.refresh_active_issues()
        self.refresh_readers()
        self.refresh_entity_table()
        self.refresh_issue_form_data()
        self.refresh_receipts()

    # ----------------------------- Вкладки -----------------------------

    def _create_catalog_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.catalog_search_input = QLineEdit()
        self.catalog_search_input.setPlaceholderText("Название, автор, жанр, издательство или ISBN")
        self.show_covers_checkbox = QCheckBox("Показывать обложки")
        self.show_covers_checkbox.setChecked(True)
        refresh_button = QPushButton("Обновить каталог")
        add_book_button = QPushButton("Добавить книгу")
        edit_book_button = QPushButton("Редактировать выбранную")
        refresh_button.clicked.connect(self.refresh_catalog)
        add_book_button.clicked.connect(lambda: self.add_entity_record("books"))
        edit_book_button.clicked.connect(self.edit_selected_catalog_book)
        self.catalog_search_input.returnPressed.connect(self.refresh_catalog)
        self.show_covers_checkbox.stateChanged.connect(self.refresh_catalog)

        controls.addWidget(QLabel("Поиск:"))
        controls.addWidget(self.catalog_search_input, stretch=1)
        controls.addWidget(self.show_covers_checkbox)
        controls.addWidget(add_book_button)
        controls.addWidget(edit_book_button)
        controls.addWidget(refresh_button)

        self.catalog_table = QTableWidget()
        self._prepare_table(self.catalog_table)
        self.catalog_table.doubleClicked.connect(self.edit_selected_catalog_book)

        layout.addLayout(controls)
        layout.addWidget(self.catalog_table)
        self.tabs.addTab(tab, "Каталог книг")

    def _create_issues_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.issues_search_input = QLineEdit()
        self.issues_search_input.setPlaceholderText("Читатель, книга или сотрудник")
        self.overdue_only_checkbox = QCheckBox("Только просроченные")
        refresh_button = QPushButton("Обновить выдачи")
        refresh_button.clicked.connect(self.refresh_active_issues)
        self.issues_search_input.returnPressed.connect(self.refresh_active_issues)
        self.overdue_only_checkbox.stateChanged.connect(self.refresh_active_issues)

        controls.addWidget(QLabel("Поиск:"))
        controls.addWidget(self.issues_search_input, stretch=1)
        controls.addWidget(self.overdue_only_checkbox)
        controls.addWidget(refresh_button)

        self.issues_table = QTableWidget()
        self._prepare_table(self.issues_table)

        issue_group = QGroupBox("Оформление выдачи")
        issue_layout = QFormLayout(issue_group)
        self.issue_reader_combo = QComboBox()
        self.issue_book_combo = QComboBox()
        self.issue_employee_combo = QComboBox()
        self.issue_date_input = QDateEdit(QDate.currentDate())
        self.issue_date_input.setCalendarPopup(True)
        self.planned_return_date_input = QDateEdit(QDate.currentDate().addDays(14))
        self.planned_return_date_input.setCalendarPopup(True)
        issue_button = QPushButton("Оформить выдачу")
        issue_button.clicked.connect(self.issue_book)

        issue_layout.addRow("Читатель:", self.issue_reader_combo)
        issue_layout.addRow("Книга с доступными экземплярами:", self.issue_book_combo)
        issue_layout.addRow("Сотрудник:", self.issue_employee_combo)
        issue_layout.addRow("Дата выдачи:", self.issue_date_input)
        issue_layout.addRow("Плановая дата возврата:", self.planned_return_date_input)
        issue_layout.addRow(issue_button)

        return_group = QGroupBox("Оформление возврата")
        return_layout = QFormLayout(return_group)
        self.return_issue_combo = QComboBox()
        self.return_date_input = QDateEdit(QDate.currentDate())
        self.return_date_input.setCalendarPopup(True)
        return_button = QPushButton("Оформить возврат")
        return_button.clicked.connect(self.return_book)
        return_layout.addRow("Активная выдача:", self.return_issue_combo)
        return_layout.addRow("Дата возврата:", self.return_date_input)
        return_layout.addRow(return_button)

        form_layout = QHBoxLayout()
        form_layout.addWidget(issue_group, stretch=2)
        form_layout.addWidget(return_group, stretch=1)

        reload_issue_data_button = QPushButton("Обновить списки для выдачи и возврата")
        reload_issue_data_button.clicked.connect(self.refresh_issue_form_data)

        layout.addLayout(controls)
        layout.addWidget(self.issues_table, stretch=1)
        layout.addLayout(form_layout)
        layout.addWidget(reload_issue_data_button)
        self.tabs.addTab(tab, "Выдача и возврат")

    def _create_readers_tab(self) -> None:
        tab = QWidget()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout = QVBoxLayout(tab)
        layout.addWidget(splitter)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        controls = QHBoxLayout()
        self.readers_search_input = QLineEdit()
        self.readers_search_input.setPlaceholderText("Ф.И.О., телефон, категория или статус")
        refresh_button = QPushButton("Обновить читателей")
        edit_button = QPushButton("Редактировать выбранного")
        refresh_button.clicked.connect(self.refresh_readers)
        edit_button.clicked.connect(lambda: self.edit_entity_record("readers", self._selected_row_data(self.readers_table)))
        self.readers_search_input.returnPressed.connect(self.refresh_readers)
        controls.addWidget(QLabel("Поиск:"))
        controls.addWidget(self.readers_search_input, stretch=1)
        controls.addWidget(edit_button)
        controls.addWidget(refresh_button)
        self.readers_table = QTableWidget()
        self._prepare_table(self.readers_table)
        self.readers_table.doubleClicked.connect(lambda: self.edit_entity_record("readers", self._selected_row_data(self.readers_table)))
        list_layout.addLayout(controls)
        list_layout.addWidget(self.readers_table)

        form_group = QGroupBox("Регистрация нового читателя")
        form_layout = QFormLayout(form_group)
        self.reader_last_name_input = QLineEdit()
        self.reader_first_name_input = QLineEdit()
        self.reader_middle_name_input = QLineEdit()
        self.reader_phone_input = QLineEdit()
        self.reader_phone_input.setPlaceholderText("+7 (921) 000-00-01")
        self.reader_category_input = QComboBox()
        self.reader_category_input.addItems(["студент", "преподаватель", "аспирант", "читатель"])
        self.reader_status_input = QComboBox()
        self.reader_status_input.addItems(["активен", "неактивен"])
        create_button = QPushButton("Зарегистрировать читателя")
        create_button.clicked.connect(self.create_reader)

        form_layout.addRow("Фамилия*:", self.reader_last_name_input)
        form_layout.addRow("Имя*:", self.reader_first_name_input)
        form_layout.addRow("Отчество:", self.reader_middle_name_input)
        form_layout.addRow("Телефон:", self.reader_phone_input)
        form_layout.addRow("Категория:", self.reader_category_input)
        form_layout.addRow("Статус:", self.reader_status_input)
        form_layout.addRow(create_button)

        splitter.addWidget(list_widget)
        splitter.addWidget(form_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.tabs.addTab(tab, "Читатели")

    def _create_entities_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.entity_combo = QComboBox()
        for key, title in [
            ("readers", "Читатели"), ("employees", "Сотрудники"), ("authors", "Авторы"),
            ("publishers", "Издательства"), ("genres", "Жанры"), ("suppliers", "Поставщики"),
            ("books", "Книги"), ("copies", "Экземпляры"), ("receipts", "Поступления"),
        ]:
            self.entity_combo.addItem(title, key)
        self.entity_combo.currentIndexChanged.connect(self.refresh_entity_table)
        self.entity_search_input = QLineEdit()
        self.entity_search_input.setPlaceholderText("Поиск по выбранному разделу")
        self.entity_search_input.returnPressed.connect(self.refresh_entity_table)
        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Редактировать выбранную запись")
        refresh_button = QPushButton("Обновить")
        add_button.clicked.connect(lambda: self.add_entity_record(self.current_entity_key))
        edit_button.clicked.connect(lambda: self.edit_entity_record(self.current_entity_key, self._selected_row_data(self.entity_table)))
        refresh_button.clicked.connect(self.refresh_entity_table)

        controls.addWidget(QLabel("Раздел:"))
        controls.addWidget(self.entity_combo)
        controls.addWidget(QLabel("Поиск:"))
        controls.addWidget(self.entity_search_input, stretch=1)
        controls.addWidget(add_button)
        controls.addWidget(edit_button)
        controls.addWidget(refresh_button)

        self.entity_table = QTableWidget()
        self._prepare_table(self.entity_table)
        self.entity_table.doubleClicked.connect(lambda: self.edit_entity_record(self.current_entity_key, self._selected_row_data(self.entity_table)))
        layout.addLayout(controls)
        layout.addWidget(self.entity_table)
        self.tabs.addTab(tab, "Администрирование")

    def _create_receipts_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        controls = QHBoxLayout()
        add_receipt_button = QPushButton("Добавить поступление")
        edit_receipt_button = QPushButton("Редактировать выбранное")
        refresh_button = QPushButton("Обновить сводку по поступлениям")
        add_receipt_button.clicked.connect(lambda: self.add_entity_record("receipts"))
        edit_receipt_button.clicked.connect(lambda: self.edit_entity_record("receipts", self._selected_row_data(self.receipts_table)))
        refresh_button.clicked.connect(self.refresh_receipts)
        controls.addWidget(add_receipt_button)
        controls.addWidget(edit_receipt_button)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        self.receipts_table = QTableWidget()
        self._prepare_table(self.receipts_table)
        self.receipts_table.doubleClicked.connect(lambda: self.edit_entity_record("receipts", self._selected_row_data(self.receipts_table)))
        layout.addLayout(controls)
        layout.addWidget(self.receipts_table)
        self.tabs.addTab(tab, "Поступления")

    def _create_help_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(False)
        help_text.setHtml(
            """
            <h2>ИПК «Библиотека»</h2>
            <p>Клиентское приложение предназначено для работы сотрудников библиотеки
            с базой данных библиотечного фонда, читателей, выдач, возвратов и поступлений.</p>

            <h3>Каталог книг</h3>
            <p>Вкладка используется для просмотра книжного фонда. <br>В таблице отображаются
            код книги, миниатюра обложки, название, авторы, жанр, издательство и сведения
            о количестве экземпляров. <br>Строку можно открыть для редактирования двойным щелчком
            или кнопкой редактирования.</p>

            <h3>Выдача и возврат</h3>
            <p>В верхней части вкладки отображаются активные выдачи. Ниже расположены формы
            оформления новой выдачи и возврата книги. <br>Для выдачи необходимо выбрать читателя,
            книгу с доступными экземплярами, сотрудника и даты. <br>Для возврата выбирается активная
            выдача и дата фактического возврата.</p>

            <h3>Читатели</h3>
            <p>Вкладка предназначена для просмотра, поиска, регистрации и редактирования
            данных читателей. <br>При сохранении выполняются проверки обязательных полей и номера телефона.</p>

            <h3>Поступления</h3>
            <p>Вкладка отображает сводку по поступлениям от поставщиков. <br>Через форму поступления
            можно указать поставщика, сотрудника, номер накладной, дату и состав поступления.</p>

            <h3>Администрирование</h3>
            <p>Вкладка предназначена для ведения основных справочников и сущностей базы данных:
            сотрудников, авторов, издательств, жанров, поставщиков, книг, экземпляров и поступлений.
            <br>Для изменения записи выберите строку и нажмите кнопку редактирования либо выполните
            двойной щелчок по строке.</p>

            <h3>Обновление данных</h3>
            <p>После добавления или изменения записей используйте кнопки обновления на соответствующих
            вкладках. <br>При запуске приложение автоматически подключается к базе данных PostgreSQL
            и использует ранее созданные таблицы, представления, функции, процедуру и триггер.</p>
            <p>Для сортировки данных щёлкните по заголовку нужного столбца таблицы. Повторный
            щелчок меняет направление сортировки.</p>
            """
        )

        layout.addWidget(help_text)
        self.tabs.addTab(tab, "Справка")

    # ----------------------------- Обновление таблиц -----------------------------

    def refresh_catalog(self) -> None:
        try:
            rows = self.repository.fetch_books_catalog(self.catalog_search_input.text())
            columns = [
                ("book_id", "Код"),
                ("book_title", "Название"),
                ("authors", "Авторы"),
                ("genre", "Жанр"),
                ("publisher", "Издательство"),
                ("publication_year", "Год"),
                ("isbn", "ISBN"),
                ("total_copies", "Всего"),
                ("available_copies", "Доступно"),
                ("issued_copies", "Выдано"),
                ("reserved_copies", "Забронировано"),
                ("restoration_copies", "На реставрации"),
                ("written_off_copies", "Списано"),
            ]
            if self.show_covers_checkbox.isChecked():
                columns.insert(1, ("cover_path", "Обложка", "image"))
            self._fill_table(self.catalog_table, rows, columns, compact=True)
            self.statusBar().showMessage(f"Каталог обновлён. Найдено книг: {len(rows)}")
        except Exception as exc:
            self._show_error("Ошибка обновления каталога", exc)

    def refresh_active_issues(self) -> None:
        try:
            rows = self.repository.fetch_active_issues(self.issues_search_input.text(), self.overdue_only_checkbox.isChecked())
            self._fill_table(
                self.issues_table,
                rows,
                [
                    ("issue_id", "№ выдачи"),
                    ("reader_full_name", "Ф.И.О. читателя"),
                    ("book_title", "Книга"),
                    ("copy_id", "№ экземпляра"),
                    ("employee_full_name", "Сотрудник"),
                    ("issue_date", "Дата выдачи"),
                    ("planned_return_date", "Плановая дата возврата"),
                    ("days_overdue", "Просрочка, дн."),
                    ("return_state", "Состояние"),
                ],
            )
            self._reload_return_issue_combo(rows)
            self.statusBar().showMessage(f"Активные выдачи обновлены. Записей: {len(rows)}")
        except Exception as exc:
            self._show_error("Ошибка обновления активных выдач", exc)

    def refresh_readers(self) -> None:
        try:
            rows = self.repository.fetch_readers(self.readers_search_input.text())
            self._fill_table(
                self.readers_table,
                rows,
                [
                    ("reader_id", "Код"), ("reader_full_name", "Ф.И.О."), ("phone", "Телефон"),
                    ("registration_date", "Дата регистрации"), ("category", "Категория"), ("status", "Статус"),
                ],
            )
            self.statusBar().showMessage(f"Список читателей обновлён. Записей: {len(rows)}")
        except Exception as exc:
            self._show_error("Ошибка обновления списка читателей", exc)

    def refresh_entity_table(self) -> None:
        try:
            if hasattr(self, "entity_combo"):
                self.current_entity_key = str(self.entity_combo.currentData() or "readers")
            spec = self.entity_specs[self.current_entity_key]
            rows = spec["fetch"](self.entity_search_input.text() if hasattr(self, "entity_search_input") else "")
            self.current_entity_rows = rows
            self._fill_table(self.entity_table, rows, spec["columns"])
            self.statusBar().showMessage(f"Раздел обновлён. Записей: {len(rows)}")
        except Exception as exc:
            self._show_error("Ошибка обновления раздела", exc)

    def refresh_issue_form_data(self) -> None:
        try:
            readers = self.repository.fetch_readers()
            books = self.repository.fetch_available_books()
            employees = self.repository.fetch_employees()
            active_issues = self.repository.fetch_active_issues()

            self._reload_combo(self.issue_reader_combo, readers, "reader_id", lambda row: f"{row['reader_id']} – {row['reader_full_name']} ({row['status']})")
            self._reload_combo(self.issue_book_combo, books, "book_id", lambda row: f"{row['book_id']} – {row['book_title']} ({row['available_copies']} доступно)")
            self._reload_combo(self.issue_employee_combo, employees, "employee_id", lambda row: f"{row['employee_id']} – {row['employee_full_name']} ({row['position']})")
            self._reload_return_issue_combo(active_issues)
        except Exception as exc:
            self._show_error("Ошибка обновления списков для выдачи", exc)

    def refresh_receipts(self) -> None:
        try:
            rows = self.repository.fetch_receipts_summary()
            self._fill_table(
                self.receipts_table,
                rows,
                [
                    ("receipt_id", "№ поступления"), ("receipt_date", "Дата"), ("invoice_number", "Накладная"),
                    ("supplier_name", "Поставщик"), ("employee_full_name", "Сотрудник"),
                    ("book_title_count", "Позиций"), ("total_quantity", "Экземпляров"),
                    ("receipt_composition", "Состав"), ("calculated_amount", "Расчётная сумма"),
                    ("document_amount", "Сумма документа"), ("amount_difference", "Разница"),
                ],
            )
            self.statusBar().showMessage(f"Сводка по поступлениям обновлена. Записей: {len(rows)}")
        except Exception as exc:
            self._show_error("Ошибка обновления поступлений", exc)

    # ----------------------------- Команды пользователя -----------------------------

    def create_reader(self) -> None:
        try:
            reader_id = self.repository.create_reader(
                last_name=self.reader_last_name_input.text(),
                first_name=self.reader_first_name_input.text(),
                middle_name=self.reader_middle_name_input.text(),
                phone=self.reader_phone_input.text(),
                category=self.reader_category_input.currentText(),
                status=self.reader_status_input.currentText(),
            )
            self.reader_last_name_input.clear()
            self.reader_first_name_input.clear()
            self.reader_middle_name_input.clear()
            self.reader_phone_input.clear()
            self.refresh_all()
            QMessageBox.information(self, "Читатель зарегистрирован", f"Создан читатель с кодом {reader_id}.")
        except Exception as exc:
            self._show_error("Ошибка регистрации читателя", exc)

    def add_entity_record(self, entity_key: str, show_success: bool = True) -> int | None:
        spec = self.entity_specs[entity_key]
        try:
            if spec.get("special_dialog") == "book":
                dialog = BookDialog(repository=self.repository, parent_window=self, title="Добавление книги")
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return None
                new_id = spec["create"](**dialog.get_data())
            elif spec.get("special_dialog") == "receipt":
                dialog = ReceiptDialog(repository=self.repository, title="Добавление поступления", parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return None
                new_id = spec["create"](**dialog.get_data())
            else:
                dialog = RecordDialog(title=f"Добавление: {spec['title']}", fields=spec["fields"], parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return None
                new_id = spec["create"](**dialog.get_data())

            self.refresh_all()
            if show_success:
                QMessageBox.information(self, "Запись добавлена", f"Создана новая запись с кодом {new_id}.")
            return int(new_id)
        except Exception as exc:
            self._show_error("Ошибка добавления записи", exc)
            return None

    def edit_entity_record(self, entity_key: str, row: dict[str, Any] | None) -> None:
        if not row:
            self._show_warning("Редактирование", "Выберите запись в таблице.")
            return
        spec = self.entity_specs[entity_key]
        id_key = spec["id_key"]
        try:
            record_id = int(row[id_key])
            if spec.get("special_dialog") == "book":
                initial = self.repository.fetch_book_details(record_id)
                dialog = BookDialog(repository=self.repository, parent_window=self, initial=initial, title="Редактирование книги")
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                spec["update"](record_id, **dialog.get_data())
            elif spec.get("special_dialog") == "receipt":
                initial = self.repository.fetch_receipt_details(record_id)
                dialog = ReceiptDialog(repository=self.repository, initial=initial, title="Редактирование поступления", parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                spec["update"](record_id, **dialog.get_data())
            else:
                dialog = RecordDialog(title=f"Редактирование: {spec['title']}", fields=spec["fields"], initial=row, parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                spec["update"](record_id, **dialog.get_data())

            self.refresh_all()
            QMessageBox.information(self, "Запись обновлена", "Изменения успешно сохранены.")
        except Exception as exc:
            self._show_error("Ошибка редактирования записи", exc)

    def edit_selected_catalog_book(self) -> None:
        row = self._selected_row_data(self.catalog_table)
        if not row:
            self._show_warning("Редактирование книги", "Выберите книгу в каталоге.")
            return
        self.edit_entity_record("books", {"book_id": row["book_id"]})

    def issue_book(self) -> None:
        try:
            reader_id = self._current_combo_id(self.issue_reader_combo)
            book_id = self._current_combo_id(self.issue_book_combo)
            employee_id = self._current_combo_id(self.issue_employee_combo)
            issue_date = self._qdate_to_date(self.issue_date_input.date())
            planned_return_date = self._qdate_to_date(self.planned_return_date_input.date())
            issue_id, copy_id = self.repository.issue_book(
                reader_id=reader_id,
                book_id=book_id,
                employee_id=employee_id,
                issue_date=issue_date,
                planned_return_date=planned_return_date,
            )
            self.refresh_all()
            QMessageBox.information(self, "Выдача оформлена", f"Создана выдача №{issue_id}. Читателю выдан экземпляр №{copy_id}.")
        except Exception as exc:
            self._show_error("Ошибка оформления выдачи", exc)

    def return_book(self) -> None:
        try:
            issue_id = self._current_combo_id(self.return_issue_combo)
            return_date = self._qdate_to_date(self.return_date_input.date())
            self.repository.return_book(issue_id, return_date)
            self.refresh_all()
            QMessageBox.information(self, "Возврат оформлен", f"Выдача №{issue_id} успешно закрыта.")
        except Exception as exc:
            self._show_error("Ошибка оформления возврата", exc)

    # ----------------------------- Служебные методы UI -----------------------------

    def _reload_return_issue_combo(self, rows: list[dict[str, Any]]) -> None:
        if hasattr(self, "return_issue_combo"):
            self._reload_combo(self.return_issue_combo, rows, "issue_id", lambda row: f"{row['issue_id']} – {row['reader_full_name']} – {row['book_title']}")

    @staticmethod
    def _prepare_table(table: QTableWidget) -> None:
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.setIconSize(QSize(58, 82))
        table.setSortingEnabled(True)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionsClickable(True)
        table.horizontalHeader().setSortIndicatorShown(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)

    def _fill_table(self, table: QTableWidget, rows: list[dict[str, Any]], columns: list[tuple], *, compact: bool = False) -> None:
        sorting_enabled = table.isSortingEnabled()
        sort_column = table.horizontalHeader().sortIndicatorSection()
        sort_order = table.horizontalHeader().sortIndicatorOrder()
        table.setSortingEnabled(False)
        table.clear()
        table.setColumnCount(len(columns))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels([column[1] for column in columns])
        has_images = False
        for row_index, row in enumerate(rows):
            for column_index, column in enumerate(columns):
                key = column[0]
                kind = column[2] if len(column) > 2 else "text"
                value = row.get(key)
                if kind == "image":
                    item = self._make_cover_item(value)
                    has_images = True
                else:
                    item = SortableTableItem("–" if value is None else str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(Qt.ItemDataRole.UserRole, row)
                item.setData(SORT_ROLE, self._sort_value(value))
                table.setItem(row_index, column_index, item)

        if compact:
            self._resize_table_to_view(table, columns)
        else:
            table.resizeColumnsToContents()
        table.resizeRowsToContents()
        if has_images:
            for row_index in range(table.rowCount()):
                table.setRowHeight(row_index, max(table.rowHeight(row_index), 92))
        table.setSortingEnabled(sorting_enabled)
        if sorting_enabled and table.rowCount() > 0 and 0 <= sort_column < table.columnCount():
            table.sortItems(sort_column, sort_order)

    @staticmethod
    def _resize_table_to_view(table: QTableWidget, columns: list[tuple]) -> None:
        header = table.horizontalHeader()
        image_columns = {index for index, column in enumerate(columns) if len(column) > 2 and column[2] == "image"}
        column_keys = {column[0] for column in columns}

        if {"book_title", "authors", "isbn"}.issubset(column_keys):
            header.setStretchLastSection(False)
            header.setMinimumSectionSize(58)
            catalog_widths = {
                "book_id": 70,
                "cover_path": 76,
                "book_title": 230,
                "authors": 320,
                "genre": 125,
                "publisher": 145,
                "publication_year": 82,
                "isbn": 155,
                "total_copies": 82,
                "available_copies": 92,
                "issued_copies": 82,
                "reserved_copies": 118,
                "restoration_copies": 128,
                "written_off_copies": 92,
            }
            for index, column in enumerate(columns):
                key = column[0]
                if index in image_columns:
                    header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
                else:
                    header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(index, catalog_widths.get(key, 120))
            return

        numeric_keys = {
            "book_id", "publication_year", "total_copies", "available_copies",
            "issued_copies", "reserved_copies", "restoration_copies", "written_off_copies",
        }

        for index, column in enumerate(columns):
            key = column[0]
            if index in image_columns:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(index, 76)
            elif key in numeric_keys:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
            else:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)

    def _make_cover_item(self, cover_path: Any) -> QTableWidgetItem:
        item = SortableTableItem()
        path_text = str(cover_path or "").strip()
        if not path_text:
            item.setText("–")
            return item

        path = Path(path_text)
        if not path.is_absolute():
            path = self.project_root / path
        if not path.exists():
            item.setText("нет файла")
            return item

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            item.setText("нет файла")
            return item
        item.setIcon(QIcon(pixmap.scaled(58, 82, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        return item

    @staticmethod
    def _sort_value(value: Any) -> tuple[int, Any]:
        if value is None:
            return (0, "")
        if isinstance(value, date):
            return (1, value.toordinal())
        if isinstance(value, Decimal):
            return (1, float(value))
        if isinstance(value, (int, float)):
            return (1, value)
        text = str(value).strip()
        try:
            parsed_date = date.fromisoformat(text)
            return (1, parsed_date.toordinal())
        except ValueError:
            pass
        return (1, text.lower())

    @staticmethod
    def _reload_combo(combo: QComboBox, rows: list[dict[str, Any]], id_key: str, text_factory: Callable[[dict[str, Any]], str]) -> None:
        combo.clear()
        for row in rows:
            combo.addItem(text_factory(row), int(row[id_key]))

    @staticmethod
    def _current_combo_id(combo: QComboBox) -> int:
        value = combo.currentData()
        if value is None:
            raise ValueError("Не выбрана запись в выпадающем списке.")
        return int(value)

    @staticmethod
    def _qdate_to_date(value: QDate) -> date:
        return date(value.year(), value.month(), value.day())

    @staticmethod
    def _selected_row_data(table: QTableWidget) -> dict[str, Any] | None:
        selected = table.selectionModel().selectedRows() if table.selectionModel() else []
        if not selected:
            return None
        item = table.item(selected[0].row(), 0)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, dict) else None

    def _show_error(self, title: str, error: Exception) -> None:
        QMessageBox.critical(self, title, str(error))
        self.statusBar().showMessage(f"{title}: {error}")

    def _show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
        self.statusBar().showMessage(message)


def run_application() -> int:
    app = QApplication([])
    icon_path = Path(__file__).resolve().parents[2] / "resources" / "img" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = LibraryMainWindow()
    window.show()
    return app.exec()
