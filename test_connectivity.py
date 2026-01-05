import socket
import sys
from urllib.parse import urlparse
import requests
from qdrant_client import QdrantClient
from google.cloud import storage
import vertexai

# Configuration
QDRANT_URL = "https://qdrant-581583863729.us-central1.run.app:443"
GCP_PROJECT_ID = "physicianscopilot"
GCS_BUCKET = "pcp-pubmed-articles-store"
GCS_CREDENTIALS = "./gcs_service_account.json"

def test_dns(url):
    print(f"--- Testing DNS for {url} ---")
    try:
        hostname = urlparse(url).hostname
        print(f"Hostname: {hostname}")
        # Test both IPv4 and IPv6
        info = socket.getaddrinfo(hostname, 443)
        for res in info:
            af, socktype, proto, canonname, sa = res
            ip = sa[0]
            family = "IPv4" if af == socket.AF_INET else "IPv6"
            print(f"Resolved to {ip} ({family})")
    except Exception as e:
        print(f"DNS Resolution failed: {e}")

def test_http(url):
    print(f"\n--- Testing HTTP GET to {url}/collections ---")
    try:
        resp = requests.get(f"{url}/collections", timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"HTTP GET failed: {e}")

def test_qdrant_rest(url):
    print(f"\n--- Testing Qdrant Client (REST) to {url} ---")
    try:
        client = QdrantClient(url=url, prefer_grpc=False, timeout=10)
        collections = client.get_collections()
        print(f"Successfully connected via REST! Collections: {collections}")
    except Exception as e:
        print(f"Qdrant REST Client failed: {e}")

def test_qdrant_grpc(url):
    print(f"\n--- Testing Qdrant Client (gRPC) to {url} ---")
    try:
        # For Cloud Run, gRPC often needs to happen on port 443
        client = QdrantClient(url=url, prefer_grpc=True, timeout=10)
        collections = client.get_collections()
        print(f"Successfully connected via gRPC! Collections: {collections}")
    except Exception as e:
        print(f"Qdrant gRPC Client failed: {e}")

if __name__ == "__main__":
    test_dns(QDRANT_URL)
    test_http(QDRANT_URL)
    test_qdrant_rest(QDRANT_URL)
    test_qdrant_grpc(QDRANT_URL)
