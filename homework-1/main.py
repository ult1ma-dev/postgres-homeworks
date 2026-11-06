"""Загрузка CSV из north_data в таблицы базы north через psycopg2."""

import csv
import os
from getpass import getpass
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


DATA_DIR = Path(__file__).resolve().parent / "north_data"

# Родительские таблицы загружаются до orders из-за внешних ключей.
TABLES = (
    (
        "employees",
        ("employee_id", "first_name", "last_name", "title", "birth_date", "notes"),
        """
        INSERT INTO employees
            (employee_id, first_name, last_name, title, birth_date, notes)
        VALUES %s
        ON CONFLICT (employee_id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            title = EXCLUDED.title,
            birth_date = EXCLUDED.birth_date,
            notes = EXCLUDED.notes
        """,
    ),
    (
        "customers",
        ("customer_id", "company_name", "contact_name"),
        """
        INSERT INTO customers (customer_id, company_name, contact_name)
        VALUES %s
        ON CONFLICT (customer_id) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            contact_name = EXCLUDED.contact_name
        """,
    ),
    (
        "orders",
        ("order_id", "customer_id", "employee_id", "order_date", "ship_city"),
        """
        INSERT INTO orders
            (order_id, customer_id, employee_id, order_date, ship_city)
        VALUES %s
        ON CONFLICT (order_id) DO UPDATE SET
            customer_id = EXCLUDED.customer_id,
            employee_id = EXCLUDED.employee_id,
            order_date = EXCLUDED.order_date,
            ship_city = EXCLUDED.ship_city
        """,
    ),
)


def read_csv(table_name, columns):
    """Прочитать CSV с заголовком, сохранив порядок колонок в INSERT."""
    file_path = DATA_DIR / f"{table_name}_data.csv"
    with file_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(f"Неверные заголовки CSV: {file_path.name}")

        rows = []
        for row in reader:
            if None in row or any(row[column] is None for column in columns):
                raise ValueError(
                    f"Неверное число полей: {file_path.name}, строка {reader.line_num}"
                )
            rows.append(tuple(row[column] or None for column in columns))
        return rows


def main():
    # Пути отсчитываются от main.py, поэтому запуск возможен из любой папки.
    data = [(name, query, read_csv(name, columns)) for name, columns, query in TABLES]

    password = os.getenv("PGPASSWORD")
    if password is None:
        password = getpass("Пароль пользователя PostgreSQL: ")

    connection = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "north"),
        user=os.getenv("PGUSER", "postgres"),
        password=password,
        connect_timeout=10,
    )
    try:
        # При ошибке в любой таблице откатывается вся загрузка.
        with connection:
            with connection.cursor() as cursor:
                for _, query, rows in data:
                    if rows:
                        execute_values(cursor, query, rows)
    finally:
        connection.close()

    for name, _, rows in data:
        print(f"{name}: загружено {len(rows)} строк")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error, psycopg2.Error) as error:
        raise SystemExit(f"Ошибка загрузки: {error}") from error
