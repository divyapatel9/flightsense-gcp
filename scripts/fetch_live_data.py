import os
import requests
import pandas as pd
from datetime import datetime

# Define the project and table details for BigQuery
PROJECT_ID = "flightsense-project"
TABLE_ID = "flightsense_data.live_telemetry"

# Define the columns based on the OpenSky Network API response
# and our BigQuery schema.
COLUMN_NAMES = [
    'icao24', 'callsign', 'origin_country', 'time_position', 'last_contact',
    'longitude', 'latitude', 'baro_altitude', 'on_ground', 'velocity',
    'true_track', 'vertical_rate', 'sensors', 'geo_altitude', 'spi',
    'position_source', 'category'
]

def fetch_and_load_live_data():
    """
    Fetches live flight data from the OpenSky Network API and appends it
    to a BigQuery table.
    """
    print("Starting live data fetch...")
    
    try:
        # Make a GET request to the OpenSky Network API
        url = "https://opensky-network.org/api/states/all"
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()

        if not data or not data.get('states'):
            print("No flight data received from API.")
            return

        # Create a Pandas DataFrame from the raw data
        df = pd.DataFrame(data['states'], columns=COLUMN_NAMES)
        print(f"Fetched {len(df)} flight records.")

        # --- Data Cleaning and Transformation ---
        # Select only the columns we need for our table
        df = df[['icao24', 'callsign', 'longitude', 'latitude', 'baro_altitude', 'velocity', 'on_ground']]

        # Clean up data: trim whitespace from callsigns and filter out nulls
        df['callsign'] = df['callsign'].str.strip()
        df = df[df['callsign'] != '']
        df = df.dropna(subset=['callsign'])
        
        # Add the ingestion timestamp
        df['ingestion_timestamp'] = datetime.utcnow()

        # --- Load to BigQuery ---
        print(f"Loading {len(df)} cleaned records into BigQuery...")
        df.to_gbq(
            destination_table=TABLE_ID,
            project_id=PROJECT_ID,
            if_exists='append',
            progress_bar=False 
        )
        
        print("Successfully loaded live data into BigQuery.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from OpenSky API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_and_load_live_data()