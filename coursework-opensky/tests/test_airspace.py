"""Проверки границ стран, пустых результатов, отчётов и повторной загрузки."""

import os
import unittest
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from uuid import uuid4

import psycopg2
import requests
from psycopg2 import sql
from psycopg2.extensions import make_dsn
from shapely import MultiPolygon, Polygon, box
from shapely.geometry import mapping

from airspace.database import database_dsn, save_snapshot
from airspace.db_manager import DBManager
from airspace.nominatim import Country, get_countries
from airspace.opensky import STATES_URL, fetch_snapshot, select_airborne

TIME = 1_700_000_000
MAINLAND = Polygon(
    [(10, 0), (14, 0), (14, 4), (10, 4)],
    holes=[[(12, 2), (13, 2), (13, 3), (12, 3)]],
)
COUNTRIES = [
    Country("AA", "Alpha", 1, 11, MultiPolygon([MAINLAND, box(20, 3, 21, 4)])),
    Country("BB", "Beta", 1, 15, box(14, 0, 16, 2)),
]


def state(icao, *, lon=11, lat=1, speed=50, callsign="TEST", ground=False, contact=TIME):
    """Собирает одну синтетическую запись в формате /states/all."""
    return [
        icao,
        callsign,
        "Elsewhere",
        contact,
        contact,
        lon,
        lat,
        1000,
        ground,
        speed,
        90,
        0,
        None,
        1050,
        "1234",
        False,
        0,
        3,
    ]


class GeographyTests(unittest.TestCase):
    """Проверки географического отбора без доступа к сети и PostgreSQL."""

    def test_territory_and_latest_state(self):
        """Учитывает остров и общую границу, исключает анклав, чужие и наземные борта."""
        data = {
            "time": TIME,
            "states": [
                state("aaaa01", lon=20.5, lat=3.5, speed=None, callsign=" aCa12  "),
                state("aaaa02", lon=12.5, lat=2.5),  # отверстие в полигоне
                state("aaaa03", lon=18),  # между материком и островом
                state("aaaa04", lon=14),  # ровно на границе Alpha и Beta
                state("aaaa05", ground=True),
                state("aaaa06", lon=None),
                state("aaaa07", ground=True, contact=TIME),
                state("aaaa07", contact=TIME - 1),
                state("aaaa08", lon=15, callsign="   ")[:17],  # ответ без категории
            ],
        }
        planes = {p.icao24: p for p in select_airborne(data, COUNTRIES[::-1]).aeroplanes}
        self.assertEqual(set(planes), {"aaaa01", "aaaa04", "aaaa08"})
        self.assertEqual(
            (planes["aaaa01"].country_code, planes["aaaa01"].callsign), ("AA", "aCa12")
        )
        self.assertIsNone(planes["aaaa01"].speed_m_s)
        self.assertEqual(planes["aaaa04"].country_code, "AA")
        self.assertEqual(planes["aaaa08"].country_code, "BB")
        self.assertIsNone(planes["aaaa08"].category)
        self.assertIsNone(planes["aaaa08"].callsign)

    def test_empty_snapshot(self):
        """Сохраняет дату ответа, даже если OpenSky вернул пустую область."""
        for states in (None, []):
            with self.subTest(states=states):
                snapshot = select_airborne({"time": TIME, "states": states}, COUNTRIES)
                self.assertEqual(snapshot.observed_at.timestamp(), TIME)
                self.assertEqual(snapshot.aeroplanes, [])


class SourceTests(unittest.TestCase):
    """Проверяет кэш Nominatim и параметры запроса OpenSky без обращения к API."""

    @patch("airspace.nominatim.time.sleep")
    def test_cache_keeps_only_valid_boundaries(self, sleep):
        """После ошибочного ответа граница запрашивается ещё раз и затем читается из кэша."""
        place = {
            "address": {"country_code": "aa"},
            "name": "Alpha",
            "lat": "1",
            "lon": "11",
            "geojson": mapping(MAINLAND),
        }
        invalid = dict(place, geojson={"type": "Point", "coordinates": [11, 1]})
        session = Mock(spec=requests.Session)
        session.get.return_value.json.side_effect = [[invalid], [place]]
        with TemporaryDirectory() as folder:
            cache = Path(folder) / "places.sqlite3"
            with self.assertRaises(ValueError):
                get_countries(session, ["Alpha"], cache)
            first = get_countries(session, ["Alpha"], cache)
            self.assertEqual(get_countries(session, [" alpha "], cache), first)
            self.assertEqual(first[0].code, "AA")
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(sleep.call_count, 2)

    def test_one_request_covers_both_countries(self):
        """Проверяет порядок широты и долготы в едином запросе текущего снимка."""
        session = Mock(spec=requests.Session)
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {"time": TIME, "states": []}
        fetch_snapshot(session, COUNTRIES)
        session.post.assert_not_called()
        session.get.assert_called_once()
        self.assertEqual(session.get.call_args.args, (STATES_URL,))
        self.assertEqual(
            session.get.call_args.kwargs["params"],
            {
                "lomin": 10,
                "lamin": 0,
                "lomax": 21,
                "lamax": 4,
                "extended": 1,
            },
        )


@contextmanager
def temporary_database():
    """Создаёт отдельную тестовую БД и удаляет её после проверки."""
    admin_dsn = make_dsn(database_dsn(), dbname="postgres")
    name = "test_airspace_" + uuid4().hex
    with closing(psycopg2.connect(admin_dsn)) as admin:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            try:
                yield make_dsn(admin_dsn, dbname=name)
            finally:
                cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@unittest.skipUnless(os.getenv("AIRSPACE_TEST_POSTGRES") == "1", "нужен AIRSPACE_TEST_POSTGRES=1")
class DatabaseTests(unittest.TestCase):
    """Проверки настоящих SQL-запросов на известных данных во временной БД."""

    def test_reports_and_replacement(self):
        """Проверяет нули, NULL, строгий порог, буквальный поиск и откат при ошибке."""
        snapshot = select_airborne(
            {
                "time": TIME,
                "states": [
                    state("aaaa01", speed=0, callsign="aCa123"),
                    state("aaaa02", speed=50, callsign="TEST_%"),
                    state("aaaa03", speed=100, callsign="XACA45"),
                    state("aaaa04", speed=None, callsign=None),
                ],
            },
            COUNTRIES,
        )
        with temporary_database() as dsn:
            manager = DBManager(dsn)
            save_snapshot(dsn, COUNTRIES, snapshot)
            save_snapshot(dsn, COUNTRIES, snapshot)
            self.assertEqual(
                manager.get_countries_and_aeroplanes_count(),
                [
                    {"country": "Alpha", "aeroplanes_count": 4},
                    {"country": "Beta", "aeroplanes_count": 0},
                ],
            )
            rows = manager.get_all_aeroplanes()
            self.assertEqual(len(rows), 4)
            self.assertEqual(
                (rows[0]["airspace_country"], rows[0]["origin_country"]), ("Alpha", "Elsewhere")
            )
            self.assertEqual(manager.get_avg_speed(), 50)
            self.assertEqual(
                [r["icao24"] for r in manager.get_aeroplanes_with_higher_speed()], ["aaaa03"]
            )
            for keyword, expected in [("ACA", ["aaaa01", "aaaa03"]), ("_%", ["aaaa02"]), ("'", [])]:
                self.assertEqual(
                    [r["icao24"] for r in manager.get_aeroplanes_with_keyword(keyword)], expected
                )
            invalid = snapshot.aeroplanes[0]._replace(country_code="ZZ")
            with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
                save_snapshot(dsn, COUNTRIES, replace(snapshot, aeroplanes=[invalid]))
            self.assertEqual(manager.get_all_aeroplanes(), rows)

            empty = replace(
                snapshot, observed_at=snapshot.observed_at + timedelta(seconds=10), aeroplanes=[]
            )
            save_snapshot(dsn, COUNTRIES[:1], empty)
            with self.assertRaises(ValueError):
                save_snapshot(dsn, COUNTRIES, snapshot)
            self.assertEqual(
                manager.get_countries_and_aeroplanes_count(),
                [{"country": "Alpha", "aeroplanes_count": 0}],
            )
            self.assertEqual(manager.get_all_aeroplanes(), [])
            self.assertIsNone(manager.get_avg_speed())
            self.assertEqual(manager.get_aeroplanes_with_higher_speed(), [])
