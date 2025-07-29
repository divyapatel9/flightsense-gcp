import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

import pandas as pd
import joblib
from google.cloud import storage
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import classification_report
from xgboost import XGBClassifier

PROJECT_ID = "flightsense-project"
GCS_BUCKET_NAME = "flightsense-project-artifacts-1234" 
MODEL_FILE_NAME = "flight_delay_model.pkl"

def train_and_upload_model():
    """
    This function is now inside the DAG file.
    """
    print("--- Starting Model Training ---")

    sql = """
    SELECT
        departure_delay, airline, origin_airport, dest_airport, distance, flight_date
    FROM `flightsense_data_dbt.stg_flight_history`
    WHERE departure_delay IS NOT NULL AND airline IS NOT NULL
    LIMIT 200000
    """
    print("Loading data from BigQuery...")
    df = pd.read_gbq(sql, project_id=PROJECT_ID)

    print("Performing feature engineering...")
    df = df.dropna()
    df['is_delayed'] = (df['departure_delay'] > 15).astype(int)
    df['flight_date'] = pd.to_datetime(df['flight_date'])
    df['month'] = df['flight_date'].dt.month
    df['day_of_week'] = df['flight_date'].dt.dayofweek
    
    X = df[['airline', 'origin_airport', 'dest_airport', 'distance', 'month', 'day_of_week']]
    y = df['is_delayed']

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

    print("Evaluating the model...")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

    print(f"Saving model to /tmp/{MODEL_FILE_NAME}...")
    joblib.dump(pipeline, f"/tmp/{MODEL_FILE_NAME}")

    print(f"Uploading model to GCS bucket: {GCS_BUCKET_NAME}...")
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f'models/{MODEL_FILE_NAME}')
    blob.upload_from_filename(f"/tmp/{MODEL_FILE_NAME}")
    
    print("--- Model Training Complete ---")

with DAG(
    dag_id="model_training_pipeline",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    schedule=None,  
    catchup=False,
    tags=["flightsense", "ml"],
) as dag:
    
    train_model_task = PythonOperator(
        task_id="train_and_upload_model",
        python_callable=train_and_upload_model,
    )