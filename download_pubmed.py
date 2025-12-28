# /data/NCBI-PubMed-ETL-Pipeline/download_pubmed.py
import os
import logging
from ftplib import FTP
import time



MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

logger = logging.getLogger(__name__)

def connect_ftp():
    FTP_URL = os.environ.get("FTP_URL", "ftp.ncbi.nlm.nih.gov")
    FTP_DIR = os.environ.get("FTP_DIR", "pubmed/baseline")
    logger.debug(f"Connecting to FTP: {FTP_URL}")
    ftp = FTP(FTP_URL)
    ftp.login()
    ftp.cwd(FTP_DIR)
    return ftp

def download_with_retry(fname, local_path):
    """
    Downloads a file with retry logic. 
    Establishes a NEW connection for each attempt to ensure reliability,
    or handles reconnection if we wanted to be more persistent.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        ftp = None
        try:
            logger.info(f"Downloading {fname} (attempt {attempt})")
            
            # Connect FRESH for this attempt (robust against timeouts)
            ftp = connect_ftp()
            
            with open(local_path, 'wb') as fp:
                ftp.retrbinary(f'RETR {fname}', fp.write)
            
            logger.info(f"Success: {fname}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed {fname}: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"PERMANENT FAILURE: {fname}", exc_info=True)
                return False
        finally:
            # Always close the connection for this attempt
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    try:
                        ftp.close()
                    except:
                        pass
    return False

def list_pubmed_files():
    logger.info("Connecting to FTP to list files...")
    ftp = connect_ftp()
    try:
        filenames = ftp.nlst()
        xml_gz_files = [f for f in filenames if f.endswith('.xml.gz')]
        logger.info(f"Found {len(xml_gz_files)} .xml.gz files on FTP.")
        return xml_gz_files
    finally:
        ftp.quit()

def download_batch(filenames):
    LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    if not filenames:
        return
    
    # download_with_retry now handles its own connection management per file
    for fname in filenames:
        local_path = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(local_path):
            logger.info(f"Skipping (already exists): {fname}")
            continue
        
        if not download_with_retry(fname, local_path):
            logger.warning(f"SKIPPING {fname} after {MAX_RETRIES} retries")

# Preserve original entry point for backward compatibility
def download_pubmed_files():
    files = list_pubmed_files()
    files = files[:10] 
    download_batch(files)