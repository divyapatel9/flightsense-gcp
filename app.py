import streamlit as st
import pandas as pd
from google.cloud import storage
import joblib
import io
import base64

# --- Configuration ---
PROJECT_ID = "flightsense-project"
GCS_BUCKET_NAME = "flightsense-project-artifacts-1234"
MODEL_FILE_NAME = "models/flight_delay_model.pkl"

# --- Styling and Design ---
# NOTE: This function uses a bit of CSS magic to apply styles.
@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def add_bg_and_styling():
    img = get_img_as_base64("assets/background.png")
    page_bg_img = f"""
    <style>
    /* Main background */
    [data-testid="stAppViewContainer"] > .main {{
        background-image: url("data:image/jpeg;base64,{img}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    /* Hide the header and toolbar to make it cleaner */
    [data-testid="stHeader"], [data-testid="stToolbar"] {{
        background: rgba(0,0,0,0);
    }}
    /* Apply a "glassmorphism" effect to the main content block */
    .st-emotion-cache-1y4p8pa {{
        background: rgba(20, 20, 40, 0.75);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        padding: 2rem;
    }}
    /* Style titles and headers */
    h1, h2, h3 {{
        color: #FFFFFF;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

# --- Caching and Model Loading ---
@st.cache_resource
def load_model():
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(MODEL_FILE_NAME)
    model_data = blob.download_as_bytes()
    model = joblib.load(io.BytesIO(model_data))
    return model

# --- Main App ---
st.set_page_config(layout="wide")
add_bg_and_styling() # Apply the new design

st.title("✈️ FlightSense Live Delay Predictor")

model = load_model()

callsign_input = st.text_input("Enter a Flight Callsign (e.g., UAL549, SWA1234)", "UAL549").upper()

if st.button("Get Prediction"):
    if not callsign_input:
        st.warning("Please enter a flight callsign.")
    else:
        with st.spinner(f"Tracking {callsign_input}..."):
            # (The rest of the data fetching and prediction logic is the same)
            # 1. Fetch Live Data
            live_sql = f"""
            SELECT
                latitude, longitude, altitude, velocity
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

            # 2. Fetch Historical/Schedule Data for Features
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
                
            # 3. Prepare Feature Vector for Prediction
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

            # 4. Make Prediction
            prediction_proba = model.predict_proba(feature_df)[0][1]
            delay_probability = round(prediction_proba * 100, 2)

            # 5. Display Results
            st.subheader(f"Live Status for {callsign_input}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Predicted Delay Probability", f"{delay_probability}%")
            col2.metric("Current Altitude (meters)", f"{live_df['altitude'].iloc[0]:,.0f}")
            col3.metric("Current Velocity (m/s)", f"{live_df['velocity'].iloc[0]:,.2f}")
            
            st.map(live_df, latitude='latitude', longitude='longitude')

            with st.expander("Show Raw Data and Features"):
                st.write("Live Data:", live_df)
                st.write("Schedule Data Used for Features:", schedule_df)
                st.write("Feature Vector Sent to Model:", feature_df)