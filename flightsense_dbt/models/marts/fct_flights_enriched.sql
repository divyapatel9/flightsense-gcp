with live_flights as (

    select * from {{ ref('fct_flight_latest_positions') }}

),

historical_flights as (

    select * from {{ ref('stg_flight_history') }}

)

select
    live_flights.callsign,
    live_flights.longitude,
    live_flights.latitude,
    live_flights.altitude,
    live_flights.velocity,
    live_flights.on_ground,
    live_flights.ingestion_timestamp,

    historical_flights.origin_airport,
    historical_flights.dest_airport,
    historical_flights.departure_delay,
    historical_flights.arrival_delay

from live_flights
left join historical_flights

    on left(live_flights.callsign, 3) = historical_flights.airline 
    and historical_flights.flight_date = date(live_flights.ingestion_timestamp)