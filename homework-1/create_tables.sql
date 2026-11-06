-- Выполнить в Query Tool pgAdmin, подключившись к базе north.
BEGIN;

CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    birth_date DATE NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(5) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id VARCHAR(5) NOT NULL REFERENCES customers (customer_id),
    employee_id INTEGER NOT NULL REFERENCES employees (employee_id),
    order_date DATE NOT NULL,
    ship_city VARCHAR(100) NOT NULL
);

COMMIT;
