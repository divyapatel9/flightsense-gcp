import pandas as pd
import joblib
from google.cloud import storage
from google.oauth2 import service_account
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import classification_report
from xgboost import XGBClassifier

# --- Configuration ---
PROJECT_ID = "flightsense-project"
GCS_BUCKET_NAME = "flightsense-project-artifacts-1234" 
MODEL_FILE_NAME = "flight_delay_model.pkl"
KEYFILE_PATH = "/home/divya330369/flightsense-project-322a9e60bbe8.json"

def train_and_upload_model():
    """
    Trains a flight delay prediction model and uploads it to GCS.
    """
    print("--- Starting Model Training ---")

    credentials = service_account.Credentials.from_service_account_file(KEYFILE_PATH)

    # 1. Load Data from BigQuery - CORRECTED SQL QUERY
    sql = """
    SELECT
        departure_delay,
        airline,
        origin_airport,
        dest_airport,
        distance,
        flight_date
    FROM `flightsense_data_dbt.stg_flight_history`
    WHERE
        departure_delay IS NOT NULL
        AND airline IS NOT NULL
        AND origin_airport IS NOT NULL
        AND dest_airport IS NOT NULL
    LIMIT 200000
    """
    print("Loading data from BigQuery...")
    df = pd.read_gbq(sql, project_id=PROJECT_ID, credentials=credentials)

    # 2. Feature Engineering - UPDATED LOGIC
    print("Performing feature engineering...")
    df = df.dropna()
    df['is_delayed'] = (df['departure_delay'] > 15).astype(int)
    
    # Create time-based features from flight_date
    df['flight_date'] = pd.to_datetime(df['flight_date'])
    df['month'] = df['flight_date'].dt.month
    df['day_of_week'] = df['flight_date'].dt.dayofweek
    
    # Define features (hour_of_day is removed)
    X = df[['airline', 'origin_airport', 'dest_airport', 'distance', 'month', 'day_of_week']]
    y = df['is_delayed']

    # 3. Model Training Pipeline
    categorical_features = ['airline', 'origin_airport', 'dest_airport']
    numerical_features = ['distance', 'month', 'day_of_week']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])

    pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                               ('classifier', XGBClassifier(use_label_encoder=False, eval_metric='logloss'))])
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training the XGBoost model...")
    pipeline.fit(X_train, y_train)

    # 4. Model Evaluation
    print("Evaluating the model...")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

    # 5. Serialize and Save Model
    print(f"Saving model to {MODEL_FILE_NAME}...")
    joblib.dump(pipeline, MODEL_FILE_NAME)

    # 6. Upload to GCS
    print(f"Uploading model to GCS bucket: {GCS_BUCKET_NAME}...")
    storage_client = storage.Client(credentials=credentials, project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f'models/{MODEL_FILE_NAME}')
    blob.upload_from_filename(MODEL_FILE_NAME)
    
    print("--- Model Training Complete ---")

if __name__ == "__main__":
    train_and_upload_model()