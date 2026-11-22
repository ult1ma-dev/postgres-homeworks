"""Границы стран из Nominatim с локальным кэшем ответов."""

import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import requests
from shapely import MultiPolygon, Polygon, prepare
from shapely.geometry import shape

DEFAULT_COUNTRIES = (
    "Austria",
    "Belgium",
    "Czechia",
    "Germany",
    "Hungary",
    "Luxembourg",
    "Poland",
    "Slovakia",
    "Slovenia",
    "Switzerland",
)
DEFAULT_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "Skypro-Airspace-Coursework/1.0 (+https://github.com/ult1ma-dev/postgres-homeworks)"


@dataclass(frozen=True)
class Country:
    """Страна, её код ISO, координаты центра и граница в долготе и широте."""

    code: str
    name: str
    latitude: float
    longitude: float
    boundary: Polygon | MultiPolygon


def parse_country(place: dict) -> Country:
    """Преобразует один результат поиска Nominatim в проверенную границу."""
    geometry = shape(place["geojson"])
    if not isinstance(geometry, (Polygon, MultiPolygon)) or geometry.is_empty:
        raise ValueError(f"У страны {place['name']} отсутствует полигон границы.")
    prepare(geometry)
    return Country(
        place["address"]["country_code"].upper(),
        place["name"],
        float(place["lat"]),
        float(place["lon"]),
        geometry,
    )


def _fetch_place(session: requests.Session, url: str, name: str) -> dict:
    """Получает центр, код ISO и геометрию страны по её названию."""
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        params={
            "country": name,
            "featureType": "country",
            "format": "jsonv2",
            "addressdetails": 1,
            "polygon_geojson": 1,
            "accept-language": "en",
            "limit": 1,
        },
        timeout=(8, 60),
    )
    response.raise_for_status()
    places = response.json()
    if not places:
        raise ValueError(f"Nominatim не нашёл страну «{name}».")
    return places[0]


def get_countries(
    session: requests.Session,
    names: list[str] | tuple[str, ...],
    cache_path: Path,
    base_url: str = DEFAULT_URL,
) -> list[Country]:
    """Получает границы по названиям и повторно использует сохранённые ответы."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    url = base_url.rstrip("/") + "/search"
    countries = {}
    with closing(sqlite3.connect(cache_path, timeout=60)) as cache:
        cache.execute("""
            CREATE TABLE IF NOT EXISTS places (
                url TEXT, query TEXT, response TEXT NOT NULL, PRIMARY KEY (url, query)
            )
        """)
        for name in names:
            key = (url, name.strip().casefold())
            # Один кэш упорядочивает обращения даже при двух одновременных запусках.
            with cache:
                cache.execute("BEGIN IMMEDIATE")
                row = cache.execute(
                    "SELECT response FROM places WHERE url = ? AND query = ?", key
                ).fetchone()
                if row is None:
                    time.sleep(1.1)
                    place = _fetch_place(session, url, name.strip())
                    cache.execute(
                        "INSERT INTO places (url, query, response) VALUES (?, ?, ?)",
                        (*key, json.dumps(place, separators=(",", ":"))),
                    )
                else:
                    place = json.loads(row[0])
                country = parse_country(place)
            countries[country.code] = country
    if not countries:
        raise ValueError("Для загрузки нужна хотя бы одна страна.")
    return sorted(countries.values(), key=lambda country: country.code)
