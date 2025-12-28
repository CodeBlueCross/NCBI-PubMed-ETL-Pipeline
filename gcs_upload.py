import os
from google.cloud import storage
import logging


PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")

logger = logging.getLogger(__name__)

def upload_to_gcs():
    GCS_BUCKET = os.environ.get("GCS_BUCKET")
    GCS_CREDENTIALS = os.environ.get("GCS_CREDENTIALS")
    # Re-fetch PARQUET_OUT just in case too, though the default is usually fine
    PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")
    
    try:
        if not GCS_BUCKET or not GCS_CREDENTIALS:
            logger.error("GCS_BUCKET or GCS_CREDENTIALS not set in .env")
            return

        if not os.path.exists(PARQUET_OUT):
            logger.warning(f"Parquet directory {PARQUET_OUT} does not exist. Nothing to upload.")
            return

        storage_client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
        logger.info(f"Connected to GCS bucket: {GCS_BUCKET}")
        
        for root_dir, dirs, files in os.walk(PARQUET_OUT):
            for file in files:
                if file.endswith('.parquet'):
                    local_path = os.path.join(root_dir, file)
                    # Create a relative path for GCS (e.g., year=2020/file.parquet)
                    gcs_path = os.path.relpath(local_path, PARQUET_OUT)
                    # Ensure unified separator for GCS
                    gcs_path = gcs_path.replace("\\", "/")
                    
                    try:
                        blob = storage_client.bucket(GCS_BUCKET).blob(gcs_path)
                        logger.info(f'Uploading {gcs_path} to GCS')
                        blob.upload_from_filename(local_path)
                    except Exception as e:
                        logger.error(f"Failed to upload {local_path}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Critical error in upload_to_gcs: {e}", exc_info=True)
