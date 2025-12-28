import os
import logging
from google.cloud import storage
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GCS_TEST")

def test_upload():
    load_dotenv()
    
    bucket_name = os.environ.get("GCS_BUCKET")
    credentials_path = os.environ.get("GCS_CREDENTIALS")
    
    logger.info(f"Checking configuration...")
    if not bucket_name:
        logger.error("GCS_BUCKET is not set in .env")
        return
    else:
        logger.info(f"GCS_BUCKET is set to: {bucket_name}")
        
    if credentials_path and credentials_path.strip().startswith('{'):
        logger.error("GCS_CREDENTIALS appears to be raw JSON content, not a file path.")
        logger.info("Trying to use local 'gcs_service_account.json' instead for verification...")
        if os.path.exists("gcs_service_account.json"):
            credentials_path = "gcs_service_account.json"
            logger.info(f"Using fallback credentials: {credentials_path}")
        else:
            logger.error("Local 'gcs_service_account.json' not found.")
            return

    if not credentials_path:
        # separate check if it wasn't set at all
        logger.error("GCS_CREDENTIALS is not set in .env")
        if os.path.exists("gcs_service_account.json"):
             credentials_path = "gcs_service_account.json"
             logger.info(f"Using fallback credentials: {credentials_path}")
        else:
             return
    else:
        logger.info(f"GCS_CREDENTIALS is set to: {credentials_path}")

    if not os.path.exists(credentials_path):
        logger.error(f"Credentials file not found at: {credentials_path}")
        return
    else:
        logger.info("Credentials file exists.")

    # Create a dummy file
    dummy_filename = "test_upload_dummy.txt"
    with open(dummy_filename, "w") as f:
        f.write("This is a test file for GCS upload verification.")
    
    try:
        logger.info("Attempting to connect to GCS...")
        storage_client = storage.Client.from_service_account_json(credentials_path)
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(dummy_filename)
        
        logger.info(f"Uploading {dummy_filename} to GCS bucket {bucket_name}...")
        blob.upload_from_filename(dummy_filename)
        
        logger.info("Upload successful!")
        
        # Verify it exists
        if blob.exists():
            logger.info("Verification: File exists in bucket.")
        else:
            logger.warning("Verification: File NOT found in bucket immediately after upload.")
            
    except Exception as e:
        logger.error(f"GCS Upload Failed: {e}", exc_info=True)
    finally:
        # Cleanup
        if os.path.exists(dummy_filename):
            os.remove(dummy_filename)
            logger.info("Local dummy file cleaned up.")

if __name__ == "__main__":
    test_upload()
