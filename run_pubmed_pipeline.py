import os
import logging
import math
import hashlib
import json

import pandas as pd
from google.cloud import storage
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from dotenv import load_dotenv

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions as google_exceptions


# Load env vars
load_dotenv(dotenv_path="./.env")


# Config
GCS_BUCKET = os.environ.get("GCS_BUCKET")
QDRANT_URL = os.environ.get("QDRANT_URL")
# QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
GCS_CREDENTIALS = os.environ.get("GCS_CREDENTIALS")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

COLLECTION_NAME = "pubmed_articles"

BATCH_TASK_INDEX = int(os.environ.get("BATCH_TASK_INDEX", 0))
BATCH_TASK_COUNT = int(os.environ.get("BATCH_TASK_COUNT", 1))


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(task_idx)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.task_idx = BATCH_TASK_INDEX
        return record

    logging.setLogRecordFactory(record_factory)


logger = logging.getLogger("VectorizationPipeline")


def init_resources():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is required")

    # GenAI client uses API key, no ADC or project needed
    genai_client = genai.Client(api_key=GOOGLE_API_KEY)

    qdrant_client = QdrantClient(
        url=QDRANT_URL
    )

    try:
        qdrant_client.get_collection(COLLECTION_NAME)
        logger.info(f"Collection '{COLLECTION_NAME}' exists")
    except Exception:
        logger.info(f"Creating collection '{COLLECTION_NAME}'")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE,
            ),
        )

    return genai_client, qdrant_client


def get_embedding_model_name():
    return "gemini-embedding-001"


def list_gcs_parquet_files(bucket_name):
    if GCS_CREDENTIALS and os.path.exists(GCS_CREDENTIALS):
        storage_client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
    else:
        storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    return sorted(
        f"gs://{bucket_name}/{blob.name}"
        for blob in blobs
        if blob.name.endswith(".parquet")
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(
        (
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
            google_exceptions.TooManyRequests,
        )
    ),
)
def generate_embeddings_batch(client, model_name, texts):
    # Batch embedding call, keep batch size well below hard limits
    response = client.models.embed_content(
        model=model_name,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )

    return [e.values for e in response.embeddings]


def process_file(file_path, qdrant_client, genai_client, embed_model_name):
    logger.info(f"Processing file: {file_path}")

    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Failed to read parquet {file_path}: {e}")
        return

    # Normalise missing fields
    df["title"] = df["title"].fillna("")
    df["abstract"] = df["abstract"].fillna("")

    # Combined embedding text
    df["text_to_embed"] = "Title: " + df["title"] + "\nAbstract: " + df["abstract"]

    df = df[df["text_to_embed"].str.strip() != "Title: \nAbstract:"]

    if df.empty:
        logger.warning(f"No valid rows in {file_path}")
        return

    BATCH_SIZE = 50
    points_to_upsert = []

    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i : i + BATCH_SIZE].copy()
        texts = batch["text_to_embed"].tolist()

        embeddings = generate_embeddings_batch(
            genai_client,
            embed_model_name,
            texts,
        )

        for idx, row in enumerate(batch.itertuples(index=False)):
            if idx >= len(embeddings):
                break

            try:
                point_id = int(row.pmid)
            except (ValueError, TypeError):
                point_id = hashlib.md5(str(row.pmid).encode()).hexdigest()

            payload = {
                "pmid": row.pmid,
                "title": row.title,
                "publication_year": row.publication_year,
                "journal": row.journal,
                "authors": row.authors,
                "doi": row.doi,
                "abstract": row.abstract[:1000],
            }

            points_to_upsert.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[idx],
                    payload=payload,
                )
            )

    if not points_to_upsert:
        return

    try:
        UPSERT_CHUNK_SIZE = 100
        for k in range(0, len(points_to_upsert), UPSERT_CHUNK_SIZE):
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points_to_upsert[k : k + UPSERT_CHUNK_SIZE],
            )

        logger.info(f"Upserted {len(points_to_upsert)} points from {file_path}")
    except Exception as e:
        logger.error(f"Qdrant upsert failed: {e}")


def main():
    setup_logging()
    logger.info("Starting vectorisation pipeline")

    if not GCS_BUCKET:
        logger.error("GCS_BUCKET env var missing")
        return

    try:
        genai_client, qdrant_client = init_resources()
        embed_model_name = get_embedding_model_name()
    except Exception as e:
        logger.critical(f"Initialisation failed: {e}", exc_info=True)
        return

    all_files = list_gcs_parquet_files(GCS_BUCKET)
    total_files = len(all_files)

    logger.info(f"Found {total_files} parquet files")

    if BATCH_TASK_COUNT > 1:
        files_per_task = math.ceil(total_files / BATCH_TASK_COUNT)
        start_idx = BATCH_TASK_INDEX * files_per_task
        end_idx = start_idx + files_per_task
        my_files = all_files[start_idx:end_idx]

        logger.info(
            f"Task {BATCH_TASK_INDEX}/{BATCH_TASK_COUNT} processing {len(my_files)} files"
        )
    else:
        my_files = all_files

    for fpath in my_files:
        process_file(
            fpath,
            qdrant_client,
            genai_client,
            embed_model_name,
        )

    logger.info("Pipeline task completed")


if __name__ == "__main__":
    main()
