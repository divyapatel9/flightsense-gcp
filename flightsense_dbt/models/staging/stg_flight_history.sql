select
    flight_date,
    case 
        when airline = 'Southwest Airlines Co.' then 'SWA'
        when airline = 'Endeavor Air Inc.' then 'EDV'
        when airline = 'JetBlue Airways' then 'JBU'
        when airline = 'SkyWest Airlines Inc.' then 'SKW'
        when airline = 'United Airlines Inc.' then 'UAL'
        when airline = 'American Airlines Inc.' then 'AAL'
        when airline = 'Delta Air Lines Inc.' then 'DAL'
        else airline
    end as airline,
    origin_airport,
    dest_airport,
    is_cancelled,
    is_diverted,
    departure_delay,
    arrival_delay,
    air_time,
    distance
from {{ source('flightsense', 'flight_history') }}