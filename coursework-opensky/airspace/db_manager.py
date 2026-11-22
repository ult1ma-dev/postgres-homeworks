"""Пять запросов курсовой к последнему сохранённому снимку."""

from contextlib import closing

import psycopg2
from psycopg2.extras import RealDictCursor

from .database import database_dsn

AIRCRAFT_SELECT = """
    SELECT a.*, c.name AS airspace_country, c.observed_at
    FROM aviation.aeroplanes AS a
    JOIN aviation.countries AS c ON c.country_code = a.country_code
"""


class DBManager:
    """Читает статистику и полные записи воздушных судов из PostgreSQL."""

    def __init__(self, dsn: str | None = None) -> None:
        """Принимает строку подключения или читает настройки из окружения."""
        self.dsn = database_dsn() if dsn is None else dsn

    def _rows(self, query: str, params: tuple = ()) -> list[dict]:
        """Выполняет параметризованный запрос и возвращает строки по именам полей."""
        with closing(psycopg2.connect(self.dsn)) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def get_countries_and_aeroplanes_count(self) -> list[dict]:
        """Возвращает все выбранные страны, включая страны с нулём бортов."""
        return self._rows("""
            SELECT c.name AS country, COUNT(a.icao24) AS aeroplanes_count
            FROM aviation.countries AS c
            LEFT JOIN aviation.aeroplanes AS a ON a.country_code = c.country_code
            GROUP BY c.country_code, c.name
            ORDER BY c.name
        """)

    def get_all_aeroplanes(self) -> list[dict]:
        """Возвращает все поля каждого борта, страну наблюдения и время снимка."""
        return self._rows(AIRCRAFT_SELECT + " ORDER BY a.icao24")

    def get_avg_speed(self) -> float | None:
        """Возвращает среднюю известную путевую скорость в м/с или None."""
        return self._rows("SELECT AVG(speed_m_s) AS average FROM aviation.aeroplanes")[0]["average"]

    def get_aeroplanes_with_higher_speed(self) -> list[dict]:
        """Возвращает борта со скоростью строго выше средней по всему снимку."""
        return self._rows(AIRCRAFT_SELECT + """
            WHERE a.speed_m_s > (SELECT AVG(speed_m_s) FROM aviation.aeroplanes)
            ORDER BY a.speed_m_s DESC, a.icao24
        """)

    def get_aeroplanes_with_keyword(self, keyword: str) -> list[dict]:
        """Ищет буквальную подстроку в позывном без учёта регистра."""
        return self._rows(
            AIRCRAFT_SELECT + """
            WHERE strpos(upper(a.callsign), upper(%s)) > 0
            ORDER BY a.icao24
        """,
            (keyword,),
        )
