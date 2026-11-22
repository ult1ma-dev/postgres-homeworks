"""Получение снимка OpenSky и привязка воздушных судов к границам стран."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NamedTuple

import requests
from shapely import Point

from .nominatim import Country

STATES_URL = "https://opensky-network.org/api/states/all"
TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)


class Aeroplane(NamedTuple):
    """Один вектор состояния OpenSky с кодом страны, над которой находится борт."""

    icao24: str
    country_code: str
    callsign: str | None
    origin_country: str | None
    position_at: datetime | None
    last_contact: datetime
    longitude: float
    latitude: float
    baro_altitude_m: float | None
    on_ground: bool
    speed_m_s: float | None
    true_track_deg: float | None
    vertical_rate_m_s: float | None
    sensors: list[int] | None
    geo_altitude_m: float | None
    squawk: str | None
    spi: bool | None
    position_source: int | None
    category: int | None

    @classmethod
    def from_state(cls, state: list, country_code: str) -> "Aeroplane":
        """Переводит поля массива /states/all в именованные поля с единицами измерения."""
        position_time = state[3]
        return cls(
            icao24=state[0].lower(),
            country_code=country_code,
            callsign=(state[1] or "").strip() or None,
            origin_country=state[2],
            position_at=(
                datetime.fromtimestamp(position_time, timezone.utc)
                if position_time is not None
                else None
            ),
            last_contact=datetime.fromtimestamp(state[4], timezone.utc),
            longitude=state[5],
            latitude=state[6],
            baro_altitude_m=state[7],
            on_ground=state[8],
            speed_m_s=state[9],
            true_track_deg=state[10],
            vertical_rate_m_s=state[11],
            sensors=state[12],
            geo_altitude_m=state[13],
            squawk=state[14],
            spi=state[15],
            position_source=state[16],
            category=state[17] if len(state) > 17 else None,
        )


@dataclass(frozen=True)
class Snapshot:
    """Время ответа OpenSky в UTC и воздушные суда в выбранных странах."""

    observed_at: datetime
    aeroplanes: list[Aeroplane]


def select_airborne(data: dict, countries: list[Country]) -> Snapshot:
    """Оставляет последнюю запись каждого борта в воздухе внутри границ стран."""
    observed_at = datetime.fromtimestamp(data["time"], timezone.utc)
    states = data["states"]
    if states is not None and not isinstance(states, list):
        raise ValueError("OpenSky вернул неожиданный формат списка бортов.")
    latest = {}
    for state in states or []:
        if len(state) < 17:
            raise ValueError("OpenSky вернул неполный вектор состояния.")
        icao24 = state[0].lower()
        if icao24 not in latest or state[4] > latest[icao24][4]:
            latest[icao24] = state

    aeroplanes = []
    by_code = sorted(countries, key=lambda country: country.code)
    for state in latest.values():
        longitude, latitude = state[5:7]
        on_ground = state[8]
        if on_ground is not False or longitude is None or latitude is None:
            continue
        point = Point(longitude, latitude)
        country = next((c for c in by_code if c.boundary.covers(point)), None)
        if country is not None:
            aeroplanes.append(Aeroplane.from_state(state, country.code))
    return Snapshot(observed_at, aeroplanes)


def fetch_snapshot(
    session: requests.Session,
    countries: list[Country],
    client_id: str | None = None,
    client_secret: str | None = None,
) -> Snapshot:
    """Запрашивает единый текущий снимок, при наличии ключей используя OAuth2."""
    if bool(client_id) != bool(client_secret):
        raise ValueError("Для OAuth2 нужны и OPENSKY_CLIENT_ID, и OPENSKY_CLIENT_SECRET.")
    headers = {}
    if client_id:
        token = session.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=(8, 30),
        )
        token.raise_for_status()
        headers["Authorization"] = "Bearer " + token.json()["access_token"]

    bounds = [country.boundary.bounds for country in countries]
    response = session.get(
        STATES_URL,
        headers=headers,
        params={
            "lomin": min(b[0] for b in bounds),
            "lamin": min(b[1] for b in bounds),
            "lomax": max(b[2] for b in bounds),
            "lamax": max(b[3] for b in bounds),
            "extended": 1,
        },
        timeout=(8, 60),
    )
    if response.status_code == 429:
        wait = response.headers.get("X-Rate-Limit-Retry-After-Seconds") or response.headers.get(
            "Retry-After"
        )
        suffix = f" Повторите через {wait} с." if wait and wait.isdigit() else ""
        raise RuntimeError("Исчерпан лимит запросов OpenSky." + suffix)
    response.raise_for_status()
    return select_airborne(response.json(), countries)
