CREATE SCHEMA IF NOT EXISTS aviation;

CREATE TABLE IF NOT EXISTS aviation.countries (
    country_code text PRIMARY KEY CHECK (country_code ~ '^[A-Z]{2}$'),
    name text NOT NULL,
    latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    west double precision NOT NULL,
    south double precision NOT NULL,
    east double precision NOT NULL,
    north double precision NOT NULL,
    observed_at timestamptz NOT NULL,
    CHECK (west <= east AND south <= north)
);

CREATE TABLE IF NOT EXISTS aviation.aeroplanes (
    icao24 text PRIMARY KEY CHECK (icao24 ~ '^[0-9a-f]{6}$'),
    country_code text NOT NULL REFERENCES aviation.countries ON DELETE CASCADE,
    callsign text,
    origin_country text,
    position_at timestamptz,
    last_contact timestamptz NOT NULL,
    longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    baro_altitude_m double precision,
    on_ground boolean NOT NULL CHECK (on_ground IS FALSE),
    speed_m_s double precision,
    true_track_deg double precision,
    vertical_rate_m_s double precision,
    sensors integer[],
    geo_altitude_m double precision,
    squawk text,
    spi boolean,
    position_source smallint,
    category smallint
);

CREATE INDEX IF NOT EXISTS aeroplanes_country_idx ON aviation.aeroplanes (country_code);
