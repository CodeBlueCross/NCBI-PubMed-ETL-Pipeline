# /data/NCBI-PubMed-ETL-Pipeline/download_pubmed.py
import os
from ftplib import FTP
import time

LOCAL_DIR = os.environ.get("LOCAL_DIR", "./pubmed_xml_gz")
FTP_URL = os.environ.get("FTP_URL", "ftp.ncbi.nlm.nih.gov")
FTP_DIR = os.environ.get("FTP_DIR", "pubmed/baseline")

MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds

def download_with_retry(ftp, fname, local_path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Downloading {fname} (attempt {attempt})")
            with open(local_path, 'wb') as fp:
                ftp.retrbinary(f'RETR {fname}', fp.write)
            print(f"Success: {fname}")
            return True
        except Exception as e:
            print(f"Failed {fname}: {e}")
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"PERMANENT FAILURE: {fname}")
                return False
    return False

def download_pubmed_files():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    ftp = FTP(FTP_URL)
    ftp.login()
    ftp.cwd(FTP_DIR)
    filenames = ftp.nlst()
    xml_gz_files = [f for f in filenames if f.endswith('.xml.gz')]

    # === 500 GB SAFETY: Only 10 files per batch ===
    xml_gz_files = xml_gz_files[:10]

    for fname in xml_gz_files:
        local_path = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(local_path):
            print(f"Skipping (already exists): {fname}")
            continue
        if not download_with_retry(ftp, fname, local_path):
            print(f"SKIPPING {fname} after {MAX_RETRIES} retries")
    ftp.quit()