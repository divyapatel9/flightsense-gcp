select
    icao24,
    callsign,
    longitude,
    latitude,
    baro_altitude as altitude,
    velocity,
    on_ground,
    ingestion_timestamp

from {{ source('flightsense', 'live_telemetry') }}