import streamlit as st
import pandas as pd
from google.cloud import storage
import joblib
import io
from geopy.geocoders import Nominatim

PROJECT_ID = "flightsense-project"
GCS_BUCKET_NAME = "flightsense-project-artifacts-1234"
MODEL_FILE_NAME = "models/flight_delay_model.pkl"

@st.cache_resource
def load_model():
    """
    Downloads and loads the trained model from GCS.
    """
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(MODEL_FILE_NAME)
    
    model_data = blob.download_as_bytes()
    model = joblib.load(io.BytesIO(model_data))
    return model


def get_city_from_coords(lat, lon):
    """
    Performs a reverse geocode lookup to find a city for coordinates.
    """
    try:
        geolocator = Nominatim(user_agent="flightsense_app")
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en', timeout=10)
        if location and location.raw.get('address'):
            address = location.raw['address']
            city = address.get('city', address.get('town', address.get('village', '')))
            country = address.get('country', '')
            return f"{city}, {country}".strip(", ")
        return "Over an unknown area"
    except Exception:
        return "Location lookup unavailable"

st.set_page_config(layout="wide")
st.title("✈️ FlightSense Live Delay Predictor")

model = load_model()

callsign_input = st.text_input("Enter a Flight Callsign (e.g., UAL549, SWA1234)", "AAL2391").upper()

if st.button("Get Prediction"):
    if not callsign_input:
        st.warning("Please enter a flight callsign.")
    else:
        with st.spinner(f"Tracking {callsign_input}..."):
            live_sql = f"""
            SELECT
                latitude, longitude, altitude, velocity, ingestion_timestamp
            FROM `flightsense_data_dbt.fct_flight_latest_positions`
            WHERE callsign = '{callsign_input}'
            """
            try:
                live_df = pd.read_gbq(live_sql, project_id=PROJECT_ID)
            except Exception as e:
                st.error(f"Could not fetch live data. Error: {e}")
                st.stop()
            
            if live_df.empty:
                st.error(f"Could not find live tracking data for flight {callsign_input}.")
                st.stop()

            airline_code = callsign_input[:3]
            schedule_sql = f"""
            SELECT
                origin_airport, dest_airport, distance, flight_date
            FROM `flightsense_data_dbt.stg_flight_history`
            WHERE airline = '{airline_code}'
            ORDER BY flight_date DESC
            LIMIT 1
            """
            try:
                schedule_df = pd.read_gbq(schedule_sql, project_id=PROJECT_ID)
            except Exception as e:
                st.error(f"Could not fetch schedule data for airline {airline_code}. Error: {e}")
                st.stop()

            if schedule_df.empty:
                st.error(f"Could not find any historical flight data for airline {airline_code} to make a prediction.")
                st.stop()
                
            latest_schedule = schedule_df.iloc[0]
            latest_schedule['flight_date'] = pd.to_datetime(latest_schedule['flight_date'])

            features = {
                'airline': airline_code,
                'origin_airport': latest_schedule['origin_airport'],
                'dest_airport': latest_schedule['dest_airport'],
                'distance': latest_schedule['distance'],
                'month': latest_schedule['flight_date'].month,
                'day_of_week': latest_schedule['flight_date'].dayofweek,
            }
            feature_df = pd.DataFrame([features])

          
            prediction_proba = model.predict_proba(feature_df)[0][1]
            delay_probability = round(prediction_proba * 100, 2)

            latest_data = live_df.iloc[0]
            location_name = get_city_from_coords(latest_data['latitude'], latest_data['longitude'])
            
            st.subheader(f"Live Status for {callsign_input}")
            
   
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Predicted Delay Probability", f"{delay_probability}%")
            col2.metric("Current Altitude (meters)", f"{latest_data['altitude']:,}" if pd.notna(latest_data['altitude']) else "N/A")
            col3.metric("Current Velocity (m/s)", f"{latest_data['velocity']:.2f}")
            col4.metric("Last Update (UTC)", latest_data['ingestion_timestamp'].strftime('%H:%M:%S'))

            
            st.write(f"**Currently Flying Over:** {location_name}")
            st.map(live_df, latitude='latitude', longitude='longitude')

            with st.expander("Show Raw Data and Features Used for Prediction"):
                st.write("**Live Telemetry Data:**")
                st.dataframe(live_df)
                st.write("**Representative Historical Data Used for Features:**")
                st.dataframe(schedule_df)
                st.write("**Feature Vector Sent to Model:**")
                st.dataframe(feature_df)