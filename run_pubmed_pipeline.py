import os
import shutil
import math
import logging
from dotenv import load_dotenv

from download_pubmed import list_pubmed_files, download_batch
from decompress_xml import decompress_gz_files
from parse_and_partition import parse_and_partition_xml
from gcs_upload import upload_to_gcs

# Load ENVs from .env
load_dotenv(dotenv_path='./.env')

LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
PARQUET_OUT = os.environ.get("PARQUET_OUT", "./pubmed_parquet/")

# Setup Logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("pipeline_execution.log"),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger("MainPipeline")

def cleanup_intermediate_files():
    """Deletes downloaded XML/GZ and generated Parquet files to save space."""
    # Clean LOCAL_DIR (xml.gz and xml)
    if os.path.exists(LOCAL_DIR):
        for f in os.listdir(LOCAL_DIR):
            file_path = os.path.join(LOCAL_DIR, f)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}", exc_info=True)

    # Clean PARQUET_OUT
    if os.path.exists(PARQUET_OUT):
        for root, dirs, files in os.walk(PARQUET_OUT):
            for f in files:
                file_path = os.path.join(root, f)
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}", exc_info=True)
            # Try to remove empty directories
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    pass # Directory might not be empty, acceptable

def main():
    setup_logging()
    logger.info("Pipeline started.")
    
    logger.info("STEP 0: Connecting to FTP to list all available files...")
    all_files = list_pubmed_files()
    
    # === CLOUD BATCH SLICING ===
    # Get batch info from environment variables (defaults to 0/1 for local run)
    task_index = int(os.environ.get("BATCH_TASK_INDEX", 0))
    task_count = int(os.environ.get("BATCH_TASK_COUNT", 1))

    # Log batch info
    if task_count > 1:
        logger.info(f"Running in Cloud Batch: Task {task_index}/{task_count}")

    # total files found
    total_files_count = len(all_files)

    # Calculate slice
    files_per_task = math.ceil(total_files_count / task_count)
    start_idx = task_index * files_per_task
    end_idx = start_idx + files_per_task
    
    # Slice the list
    my_files = all_files[start_idx:end_idx]
    
    logger.info(f"Task {task_index} processing files from index {start_idx} to {end_idx} (Total: {len(my_files)} files)")

    # Update main list to just this slice
    all_files = my_files

    BATCH_SIZE = 5
    if not all_files:
        logger.warning(f"Task {task_index} has no files to process.")
        return

    total_batches = math.ceil(len(all_files) / BATCH_SIZE)

    for i in range(total_batches):
        batch_files = all_files[i*BATCH_SIZE : (i+1)*BATCH_SIZE]
        batch_num = i + 1
        logger.info(f"=== STARTING BATCH {batch_num}/{total_batches} ({len(batch_files)} files) ===")
        
        logger.info(f"Batch {batch_num}: Downloading...")
        download_batch(batch_files)
        
        logger.info(f"Batch {batch_num}: Decompressing...")
        decompress_gz_files()
        
        logger.info(f"Batch {batch_num}: Parsing and Partitioning...")
        parse_and_partition_xml()
        
        logger.info(f"Batch {batch_num}: Uploading to GCS...")
        upload_to_gcs()
        
        logger.info(f"Batch {batch_num}: Cleaning up local files...")
        cleanup_intermediate_files()
        
        logger.info(f"=== COMPLETED BATCH {batch_num}/{total_batches} ===")
    
    logger.info("Pipeline completed successfully!")

if __name__ == "__main__":
    main()
