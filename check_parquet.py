import pandas as pd
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_CREDENTIALS = os.environ.get("GCS_CREDENTIALS")
FILE_PATH = "gs://pcp-pubmed-articles-store/year=1800/pubmed25n0925_1800.parquet"

if GCS_CREDENTIALS and os.path.exists(GCS_CREDENTIALS):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(GCS_CREDENTIALS)

try:
    df = pd.read_parquet(FILE_PATH)
    print(f"File: {FILE_PATH}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"Error: {e}")
