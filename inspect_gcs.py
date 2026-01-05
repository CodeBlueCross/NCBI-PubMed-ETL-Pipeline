from google.cloud import storage
import os
import json

GCS_CREDENTIALS = "./gcs_service_account.json"
GCS_BUCKET = "pcp-pubmed-articles-store"

def inspect_bucket():
    print(f"Inspecting bucket: {GCS_BUCKET}")
    if os.path.exists(GCS_CREDENTIALS):
        client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
    else:
        client = storage.Client()
    
    bucket = client.bucket(GCS_BUCKET)
    print("Listing first 20 blobs...")
    blobs = bucket.list_blobs(max_results=20)
    for blob in blobs:
        print(f"- {blob.name} ({blob.size} bytes)")

if __name__ == "__main__":
    inspect_bucket()
