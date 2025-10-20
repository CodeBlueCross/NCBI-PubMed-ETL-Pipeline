import os
from google.cloud import storage

PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_CREDENTIALS = os.environ.get("GCS_CREDENTIALS")

def upload_to_gcs():
    storage_client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
    for root_dir, dirs, files in os.walk(PARQUET_OUT):
        for file in files:
            if file.endswith('.parquet'):
                local_path = os.path.join(root_dir, file)
                gcs_path = os.path.relpath(local_path, PARQUET_OUT)
                blob = storage_client.bucket(GCS_BUCKET).blob(gcs_path)
                print(f'Uploading {gcs_path} to GCS')
                blob.upload_from_filename(local_path)
