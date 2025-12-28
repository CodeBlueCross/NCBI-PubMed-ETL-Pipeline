# PubMed Articles Vectorization Pipeline

This repository contains a specialized pipeline for vectorizing processed PubMed articles and storing them in a Qdrant vector database using Gemini embeddings.

## Overview

The pipeline:
1.  **Lists** Parquet files from a Google Cloud Storage (GCS) bucket.
2.  **Slices** the work across multiple Google Cloud Batch tasks (supporting horizontal scaling).
3.  **Embeds** article titles and abstracts using the Gemini `text-embedding-004` model via Vertex AI.
4.  **Upserts** the resulting vectors and metadata (PMID, Year, Journal, Authors, DOI) into **Qdrant**.

## Configuration

Required Environment Variables (see `.env` or `job_config.json`):
- `GCS_BUCKET`: The bucket containing the processed Parquet files (e.g., `pcp-pubmed-articles-store`).
- `QDRANT_URL`: The URL of your Qdrant instance.
- `GCS_CREDENTIALS`: Path to your service account key (e.g., `./gcs_service_account.json`).
- `GCP_PROJECT_ID`: (Optional) Derived from credentials if not provided.
- `GCP_LOCATION`: Location for Vertex AI (e.g., `us-central1`).


## Deployment

### 1. Build & Push Image
```bash
gcloud builds submit --config cloudbuild.yaml .
```

### 2. Submit Cloud Batch Job
```bash
gcloud batch jobs submit vectorization-job --location us-central1 --config job_config.json
```

## Robustness Features

- **Batching**: Multi-level batching for API efficiency (Gemini texts and Qdrant points).
- **Retries**: Uses `tenacity` with exponential backoff to handle transient Google API errors (e.g., rate limits).
- **Parallelism**: Designed to run as a partitioned job in Cloud Batch.