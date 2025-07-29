from __future__ import annotations

import pendulum
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from datetime import timedelta

from scripts.fetch_live_data import fetch_and_load_live_data

with DAG(
    dag_id="live_telemetry_pipeline",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    schedule_interval="*/20 * * * *", 
    catchup=False,
    tags=["flightsense"],
    default_args={
        "owner": "airflow",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    }
) as dag:

    fetch_live_data_task = PythonOperator(
        task_id="fetch_and_load_live_data",
        python_callable=fetch_and_load_live_data,
    )