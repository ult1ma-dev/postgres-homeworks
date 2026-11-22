"""Команды загрузки наблюдений и чтения отчётов."""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

import psycopg2
import requests

from .database import save_snapshot
from .db_manager import DBManager
from .nominatim import DEFAULT_COUNTRIES, DEFAULT_URL, get_countries
from .opensky import fetch_snapshot


def load(names: list[str] | tuple[str, ...], dsn: str) -> dict:
    """Получает границы и наблюдения, сохраняет снимок и возвращает его размер."""
    cache = Path(__file__).resolve().parent.parent / ".cache" / "places.sqlite3"
    with requests.Session() as session:
        countries = get_countries(
            session, names, cache, os.environ.get("NOMINATIM_URL", DEFAULT_URL)
        )
        snapshot = fetch_snapshot(
            session,
            countries,
            os.environ.get("OPENSKY_CLIENT_ID"),
            os.environ.get("OPENSKY_CLIENT_SECRET"),
        )
    save_snapshot(dsn, countries, snapshot)
    return {
        "observed_at": snapshot.observed_at.isoformat(),
        "countries": len(countries),
        "aeroplanes": len(snapshot.aeroplanes),
    }


def main() -> int:
    """Выполняет выбранную команду и печатает результат в формате JSON."""
    parser = argparse.ArgumentParser(
        description="Самолёты в воздушном пространстве выбранных стран"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    loader = commands.add_parser("load", help="получить текущий снимок и записать его в PostgreSQL")
    loader.add_argument(
        "--countries",
        nargs="+",
        default=DEFAULT_COUNTRIES,
        metavar="COUNTRY",
        help="названия стран через пробел, составные названия в кавычках",
    )
    commands.add_parser("counts", help="количество бортов по странам")
    commands.add_parser("all", help="полные записи всех бортов")
    commands.add_parser("avg", help="средняя путевая скорость, м/с")
    commands.add_parser("faster", help="борта со скоростью выше средней")
    finder = commands.add_parser("find", help="найти подстроку в позывном")
    finder.add_argument("keyword", help="например, ACA")
    args = parser.parse_args()
    manager = DBManager()
    reports = {
        "counts": manager.get_countries_and_aeroplanes_count,
        "all": manager.get_all_aeroplanes,
        "avg": manager.get_avg_speed,
        "faster": manager.get_aeroplanes_with_higher_speed,
    }
    try:
        if args.command == "load":
            result = load(args.countries, manager.dsn)
        elif args.command == "find":
            result = manager.get_aeroplanes_with_keyword(args.keyword)
        else:
            result = reports[args.command]()
    except (psycopg2.errors.UndefinedTable, psycopg2.errors.InvalidSchemaName):
        print("Сначала загрузите снимок командой python -m airspace load.", file=sys.stderr)
        return 1
    except (
        requests.RequestException,
        psycopg2.Error,
        sqlite3.Error,
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
    ) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
