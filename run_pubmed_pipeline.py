
import os
import logging
import math
import hashlib
import json
import time

import pandas as pd
import gcsfs
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions as google_exceptions
# Load env vars
load_dotenv(dotenv_path='./.env')

# --- CONFIGURATION ---
GCS_BUCKET = os.environ.get("GCS_BUCKET")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)
GCS_CREDENTIALS = os.environ.get("GCS_CREDENTIALS")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
COLLECTION_NAME = "pubmed_articles"

# Cloud Batch Indexing
BATCH_TASK_INDEX = int(os.environ.get("BATCH_TASK_INDEX", 0))
BATCH_TASK_COUNT = int(os.environ.get("BATCH_TASK_COUNT", 1))

# Setup Logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(task_idx)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    # Add task index to log record
    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.task_idx = BATCH_TASK_INDEX
        return record
    logging.setLogRecordFactory(record_factory)

logger = logging.getLogger("VectorizationPipeline")

def init_resources():
    """Initialize Vertex AI and Qdrant."""
    global GCP_PROJECT_ID
    
    # Try to extract project ID from credentials if missing
    if not GCP_PROJECT_ID and GCS_CREDENTIALS and os.path.exists(GCS_CREDENTIALS):
        try:
            with open(GCS_CREDENTIALS, 'r') as f:
                creds_data = json.load(f)
                GCP_PROJECT_ID = creds_data.get("project_id")
                logger.info(f"Extracted Project ID from credentials: {GCP_PROJECT_ID}")
        except Exception as e:
            logger.error(f"Failed to extract Project ID from credentials: {e}")

    if not GCP_PROJECT_ID:
        logger.error("GCP_PROJECT_ID not set and could not be extracted.")
        raise ValueError("GCP_PROJECT_ID is required.")
    
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    
    # Qdrant Client
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    
    # Ensure collection exists
    try:
        qdrant_client.get_collection(COLLECTION_NAME)
        logger.info(f"Collection '{COLLECTION_NAME}' exists.")
    except Exception:
        logger.info(f"Collection '{COLLECTION_NAME}' does not exist. Creating...")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    return qdrant_client

def get_embedding_model():
    """Returns the latest SOTA Gemini Embedding Model."""
    return TextEmbeddingModel.from_pretrained("gemini-embedding-001")

def list_gcs_parquet_files(bucket_name):
    """Lists all parquet files in the bucket using GCS Client."""
    if GCS_CREDENTIALS and os.path.exists(GCS_CREDENTIALS):
        storage_client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
    else:
        storage_client = storage.Client()
        
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    
    parquet_files = []
    for blob in blobs:
        if blob.name.endswith(".parquet"):
            parquet_files.append(f"gs://{bucket_name}/{blob.name}")
    
    return sorted(parquet_files)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((
        google_exceptions.ResourceExhausted, 
        google_exceptions.ServiceUnavailable,
        google_exceptions.TooManyRequests
    ))
)
def generate_embeddings_batch(model, texts):
    """Generates embeddings using Gemini-001, resized to 768 dims."""
    try:
        # wrap in TextEmbeddingInput with 'RETRIEVAL_DOCUMENT' task_type
        inputs = [
            TextEmbeddingInput(text=text, task_type="RETRIEVAL_DOCUMENT") 
            for text in texts
        ]
        embeddings = model.get_embeddings(inputs, output_dimensionality=768)
        
        return [embedding.values for embedding in embeddings]
        
    except Exception as e:
        logger.warning(f"Error generating embeddings (will retry if transient): {e}")
        raise


def process_file(file_path, qdrant_client, embed_model):
    """Reads a parquet file, vectorizes, and upserts to Qdrant."""
    logger.info(f"Processing file: {file_path}")
    
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Failed to read parquet {file_path}: {e}")
        return

    # Filter out rows with empty titles or abstracts
    df['title'] = df['title'].fillna('')
    df['abstract'] = df['abstract'].fillna('')
    
    # Create combined text for embedding
    # Format: "Title: <title>\nAbstract: <abstract>"
    df['text_to_embed'] = "Title: " + df['title'] + "\nAbstract: " + df['abstract']
    
    # Remove empty texts (if both title and abstract were empty)
    df = df[df['text_to_embed'].str.strip() != "Title: \nAbstract:"]
    
    if df.empty:
        logger.warning(f"No valid articles in {file_path}")
        return

    # Process in batches
    BATCH_SIZE = 50 # Vertex AI limit suggestion
    total_rows = len(df)
    
    points_to_upsert = []
    
    for i in range(0, total_rows, BATCH_SIZE):
        batch = df.iloc[i : i+BATCH_SIZE].copy()
        texts = batch['text_to_embed'].tolist()
        
        embeddings = generate_embeddings_batch(embed_model, texts)
        
        if not embeddings:
            continue
            
        # Create Qdrant Points
        for idx, row in enumerate(batch.itertuples(index=False)):
            if idx >= len(embeddings):
                break
                
            vector = embeddings[idx]
            
            # Metadata
            payload = {
                "pmid": row.pmid,
                "title": row.title,
                "publication_year": row.publication_year,
                "journal": row.journal,
                "authors": row.authors,
                "doi": row.doi,
                 # Truncate abstract to save space if needed, keeping full for now
                "abstract": row.abstract[:1000] 
            }
            
            # Use PMID as ID if integer, else hash it
            try:
                point_id = int(row.pmid)
            except (ValueError, TypeError):
                point_id = hashlib.md5(str(row.pmid).encode()).hexdigest()

            points_to_upsert.append(
                PointStruct(id=point_id, vector=vector, payload=payload)
            )

    # Upsert to Qdrant
    if points_to_upsert:
        try:
            # Upsert in chunks to avoid request size limits
            UPSERT_CHUNK_SIZE = 100
            for k in range(0, len(points_to_upsert), UPSERT_CHUNK_SIZE):
                chunk = points_to_upsert[k : k+UPSERT_CHUNK_SIZE]
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=chunk
                )
            logger.info(f"Upserted {len(points_to_upsert)} points from {file_path}")
        except Exception as e:
            logger.error(f"Failed to upsert to Qdrant: {e}")

def main():
    setup_logging()
    logger.info("Starting Vectorization Pipeline...")

    if not GCS_BUCKET:
        logger.error("GCS_BUCKET env var missing.")
        return

    # Initialize Resources
    try:
        qdrant_client = init_resources()
        embed_model = get_embedding_model()
    except Exception as e:
        logger.critical(f"Initialization failed: {e}", exc_info=True)
        return

    # List Files
    logger.info(f"Listing files in gs://{GCS_BUCKET}...")
    all_files = list_gcs_parquet_files(GCS_BUCKET)
    
    total_files = len(all_files)
    logger.info(f"Total Parquet files found: {total_files}")

    # Slicing for Batch
    if BATCH_TASK_COUNT > 1:
        files_per_task = math.ceil(total_files / BATCH_TASK_COUNT)
        start_idx = BATCH_TASK_INDEX * files_per_task
        end_idx = start_idx + files_per_task
        my_files = all_files[start_idx:end_idx]
        logger.info(f"Task {BATCH_TASK_INDEX}/{BATCH_TASK_COUNT}: Processing files {start_idx} to {end_idx} ({len(my_files)} files)")
    else:
        my_files = all_files
        logger.info(f"Running locally/single-task. Processing all {len(my_files)} files.")

    # Process
    for fpath in my_files:
        process_file(fpath, qdrant_client, embed_model)

    logger.info("Pipeline Task Completed.")

if __name__ == "__main__":
    main()
