# Use a specific version of the official Apache Airflow image for reproducibility
FROM apache/airflow:2.8.1

# Switch to the root user to install new packages
USER root

# Install system dependencies if needed (for this project, none are required)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Switch back to the airflow user before installing Python packages
USER airflow

# Install the required Python libraries for the FlightSense project
# --no-cache-dir ensures the image is smaller
RUN pip install --no-cache-dir \
    "apache-airflow-providers-google==10.13.0" \
    "pandas-gbq==0.22.0" \
    "google-cloud-storage==2.16.0" \
    "scikit-learn==1.5.0" \
    "xgboost==2.0.3" \
    "dbt-bigquery==1.8.0"