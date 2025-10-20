import os
from dotenv import load_dotenv

from download_pubmed import download_pubmed_files
from decompress_xml import decompress_gz_files
from parse_and_partition import parse_and_partition_xml
from gcs_upload import upload_to_gcs

# Load ENVs from .env (assumes it is in the same directory)
load_dotenv(dotenv_path='./.env')

def main():
    print("STEP 1: Downloading PubMed .xml.gz files from FTP...")
    download_pubmed_files()
    print("Download complete.\n")
    
    print("STEP 2: Decompressing .xml.gz files to .xml...")
    decompress_gz_files()
    print("Decompression complete.\n")
    
    print("STEP 3: Parsing XML, partitioning, converting to Parquet...")
    parse_and_partition_xml()
    print("Parsing and Parquet conversion complete.\n")
    
    print("STEP 4: Uploading Parquet files to Google Cloud Storage...")
    upload_to_gcs()
    print("Upload complete.\n")
    
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    main()
