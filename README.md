# NCBI-PubMed-ETL-Pipeline
This repository automates the end-to-end extraction, transformation, and loading (ETL) of the NCBI PubMed dataset into a Google Cloud Storage bucket. It downloads `.xml.gz` files from PubMed’s FTP server, decompresses and parses them, converts them to partitioned Parquet files (with an embedding column), and uploads them to the cloud. 
## Features 
- **Automated Download:** Fetches PubMed dataset XML files directly from NCBI FTP. 
- **Decompression:** Unzips downloaded `.xml.gz` files to plain XML. 
- **Parsing & Transformation:** Converts XML records to Parquet format, adds a placeholder for embeddings, and partitions data by year. 
- **Cloud Upload:** Uploads partitioned Parquet files to your specified Google Cloud Storage bucket. 
- **Environment Configuration:** All paths and secrets managed with a `.env` configuration file. 

## File Structure``
├── .env  
├── requirements.txt  
├── run_pubmed_pipeline.py  
├── download_pubmed.py  
├── decompress_xml.py  
├── parse_and_partition.py  
├── gcs_upload.py  
├── README.md

## Setup 1. Clone the repository`
git clone
cd

**Set up your `.env` file** (edit values for your environment):
LOCAL_DIR=./pubmed_xml_gz  
PARQUET_OUT=./pubmed_parquet/  
FTP_URL=ftp.ncbi.nlm.nih.gov  
FTP_DIR=pubmed/baseline  
GCS_BUCKET=your-bucket-name  
GCS_CREDENTIALS=path/to/your/gcs-creds.json

**Install requirements**
pip install -r requirements.txt

**Run the pipeline**
python run_pubmed_pipeline.py

## Usage Notes 
- The pipeline will download and process all PubMed baseline XML files unless you filter them in the scripts. 
- Each Parquet file includes an **embedding** column (initialized as `None`). You can populate these later for semantic search and indexing. 
- Data is partitioned per publication year for faster query and retrieval. 
- Google Cloud credentials (`GCS_CREDENTIALS`) require a service account JSON file with access to the target bucket. 

## Customization 
- **Year Filtering:** Edit `download_pubmed.py` or `parse_and_partition.py` to restrict by year or file name pattern. 
- **Embeddings:** Integrate your vectorization model to populate the `embedding` column for downstream ML or retrieval use. 

## Troubleshooting 
- Ensure all environment variables in `.env` are set correctly. 
- Install all packages from `requirements.txt`. 
- For large downloads, a stable network and sufficient disk/cloud storage are needed.