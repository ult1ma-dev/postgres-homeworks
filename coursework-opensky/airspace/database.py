"""Подключение к PostgreSQL и атомарная запись текущего снимка."""

import os
from contextlib import closing
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import make_dsn
from psycopg2.extras import execute_values

from .nominatim import Country
from .opensky import Aeroplane, Snapshot


def database_dsn() -> str:
    """Использует DATABASE_URL или параметры libpq и имя учебной базы."""
    return os.environ.get("DATABASE_URL") or make_dsn(
        dbname=os.environ.get("PGDATABASE", "opensky_coursework"),
        connect_timeout=8,
    )


def save_snapshot(dsn: str, countries: list[Country], snapshot: Snapshot) -> None:
    """Заменяет страны и борта одной транзакцией, сохраняя самый свежий снимок."""
    if not countries:
        raise ValueError("Невозможно записать снимок без выбранных стран.")
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    country_rows = [
        (c.code, c.name, c.latitude, c.longitude, *c.boundary.bounds, snapshot.observed_at)
        for c in countries
    ]
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('aviation.current_snapshot'))")
        cur.execute(schema)
        cur.execute("SELECT MAX(observed_at) FROM aviation.countries")
        previous_time = cur.fetchone()[0]
        if previous_time is not None and previous_time > snapshot.observed_at:
            raise ValueError("В базе уже есть более свежий снимок OpenSky.")
        cur.execute("DELETE FROM aviation.countries")
        execute_values(
            cur,
            """
            INSERT INTO aviation.countries
                (country_code, name, latitude, longitude, west, south, east, north, observed_at)
            VALUES %s
        """,
            country_rows,
        )
        columns = sql.SQL(", ").join(map(sql.Identifier, Aeroplane._fields))
        execute_values(
            cur,
            sql.SQL("INSERT INTO aviation.aeroplanes ({}) VALUES %s").format(columns),
            snapshot.aeroplanes,
        )
