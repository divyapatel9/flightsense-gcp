with source as (

    select * from {{ ref('stg_live_telemetry') }}

),

latest_positions as (

    select
        *,
        row_number() over (partition by callsign order by ingestion_timestamp desc) as row_num
    from source
    where callsign is not null

)

select
    icao24,
    callsign,
    longitude,
    latitude,
    altitude,
    velocity,
    on_ground,
    ingestion_timestamp
from latest_positions
where row_num = 1