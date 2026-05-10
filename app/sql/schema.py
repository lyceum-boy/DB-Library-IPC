SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS publishers (
        publisher_id integer GENERATED ALWAYS AS IDENTITY,
        name varchar(50) NOT NULL,
        city varchar(30) NOT NULL,
        phone varchar(18),
        CONSTRAINT pk_publishers PRIMARY KEY (publisher_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS genres (
        genre_id integer GENERATED ALWAYS AS IDENTITY,
        name varchar(30) NOT NULL,
        description varchar(100),
        CONSTRAINT pk_genres PRIMARY KEY (genre_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS readers (
        reader_id integer GENERATED ALWAYS AS IDENTITY,
        last_name varchar(30) NOT NULL,
        first_name varchar(20) NOT NULL,
        middle_name varchar(30),
        phone varchar(18),
        registration_date date NOT NULL,
        category varchar(20) NOT NULL,
        status varchar(15) NOT NULL,
        CONSTRAINT pk_readers PRIMARY KEY (reader_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id integer GENERATED ALWAYS AS IDENTITY,
        last_name varchar(30) NOT NULL,
        first_name varchar(20) NOT NULL,
        middle_name varchar(30),
        position varchar(30) NOT NULL,
        phone varchar(18),
        CONSTRAINT pk_employees PRIMARY KEY (employee_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authors (
        author_id integer GENERATED ALWAYS AS IDENTITY,
        last_name varchar(30) NOT NULL,
        first_name varchar(20) NOT NULL,
        middle_name varchar(30),
        birth_date date,
        CONSTRAINT pk_authors PRIMARY KEY (author_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id integer GENERATED ALWAYS AS IDENTITY,
        name varchar(60) NOT NULL,
        address varchar(255) NOT NULL,
        phone varchar(18),
        contact_person varchar(127),
        CONSTRAINT pk_suppliers PRIMARY KEY (supplier_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS books (
        book_id integer GENERATED ALWAYS AS IDENTITY,
        isbn varchar(17) NOT NULL,
        title varchar(100) NOT NULL,
        publication_year integer NOT NULL,
        publisher_id integer NOT NULL,
        genre_id integer NOT NULL,
        language varchar(20) NOT NULL,
        page_count integer NOT NULL,
        cover_path varchar(255),
        CONSTRAINT pk_books PRIMARY KEY (book_id),
        CONSTRAINT fk_books_publisher
            FOREIGN KEY (publisher_id) REFERENCES publishers (publisher_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT fk_books_genre
            FOREIGN KEY (genre_id) REFERENCES genres (genre_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT chk_books_publication_year CHECK (publication_year >= 0),
        CONSTRAINT chk_books_page_count CHECK (page_count > 0)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS receipts (
        receipt_id integer GENERATED ALWAYS AS IDENTITY,
        supplier_id integer NOT NULL,
        employee_id integer NOT NULL,
        receipt_date date NOT NULL,
        invoice_number varchar(20) NOT NULL,
        total_amount numeric(8,2) NOT NULL,
        CONSTRAINT pk_receipts PRIMARY KEY (receipt_id),
        CONSTRAINT fk_receipts_supplier
            FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT fk_receipts_employee
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT chk_receipts_total_amount CHECK (total_amount >= 0)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS copies (
        copy_id integer GENERATED ALWAYS AS IDENTITY,
        book_id integer NOT NULL,
        receipt_id integer NOT NULL,
        arrival_date date NOT NULL,
        condition_state varchar(20) NOT NULL,
        status varchar(20) NOT NULL,
        storage_location varchar(30) NOT NULL,
        CONSTRAINT pk_copies PRIMARY KEY (copy_id),
        CONSTRAINT fk_copies_book
            FOREIGN KEY (book_id) REFERENCES books (book_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT fk_copies_receipt
            FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS issues (
        issue_id integer GENERATED ALWAYS AS IDENTITY,
        reader_id integer NOT NULL,
        copy_id integer NOT NULL,
        employee_id integer NOT NULL,
        issue_date date NOT NULL,
        planned_return_date date NOT NULL,
        actual_return_date date,
        issue_status varchar(20) NOT NULL,
        CONSTRAINT pk_issues PRIMARY KEY (issue_id),
        CONSTRAINT fk_issues_reader
            FOREIGN KEY (reader_id) REFERENCES readers (reader_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT fk_issues_copy
            FOREIGN KEY (copy_id) REFERENCES copies (copy_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT fk_issues_employee
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT chk_issues_dates
            CHECK (actual_return_date IS NULL OR actual_return_date >= issue_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS book_authors (
        book_id integer NOT NULL,
        author_id integer NOT NULL,
        CONSTRAINT pk_book_authors PRIMARY KEY (book_id, author_id),
        CONSTRAINT fk_book_authors_book
            FOREIGN KEY (book_id) REFERENCES books (book_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        CONSTRAINT fk_book_authors_author
            FOREIGN KEY (author_id) REFERENCES authors (author_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS receipt_items (
        receipt_id integer NOT NULL,
        book_id integer NOT NULL,
        quantity integer NOT NULL,
        unit_price numeric(8,2) NOT NULL,
        CONSTRAINT pk_receipt_items PRIMARY KEY (receipt_id, book_id),
        CONSTRAINT fk_receipt_items_receipt
            FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        CONSTRAINT fk_receipt_items_book
            FOREIGN KEY (book_id) REFERENCES books (book_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        CONSTRAINT chk_receipt_items_quantity CHECK (quantity > 0),
        CONSTRAINT chk_receipt_items_unit_price CHECK (unit_price >= 0)
    );
    """,
    "CREATE INDEX IF NOT EXISTS id_publisher_b ON books(publisher_id);",
    "CREATE INDEX IF NOT EXISTS id_genre_b ON books(genre_id);",
    "CREATE INDEX IF NOT EXISTS id_book_c ON copies(book_id);",
    "CREATE INDEX IF NOT EXISTS id_receipt_c ON copies(receipt_id);",
    "CREATE INDEX IF NOT EXISTS id_supplier_r ON receipts(supplier_id);",
    "CREATE INDEX IF NOT EXISTS id_employee_r ON receipts(employee_id);",
    "CREATE INDEX IF NOT EXISTS id_reader_i ON issues(reader_id);",
    "CREATE INDEX IF NOT EXISTS id_copy_i ON issues(copy_id);",
    "CREATE INDEX IF NOT EXISTS id_employee_i ON issues(employee_id);",
    "CREATE INDEX IF NOT EXISTS id_book_ba ON book_authors(book_id);",
    "CREATE INDEX IF NOT EXISTS id_author_ba ON book_authors(author_id);",
    "CREATE INDEX IF NOT EXISTS id_receipt_ri ON receipt_items(receipt_id);",
    "CREATE INDEX IF NOT EXISTS id_book_ri ON receipt_items(book_id);",
]
