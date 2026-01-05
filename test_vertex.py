import os
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VertexTester")

# Configuration
GCP_PROJECT_ID = "physicianscopilot"
GCP_LOCATION = "us-central1"
GCS_CREDENTIALS = "./gcs_service_account.json"

def test_vertex_ai():
    logger.info(f"Testing Vertex AI in project: {GCP_PROJECT_ID}, location: {GCP_LOCATION}")
    
    if os.path.exists(GCS_CREDENTIALS):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(GCS_CREDENTIALS)
        logger.info(f"Using credentials from {GCS_CREDENTIALS}")
    
    try:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        
        logger.info("Generating test embedding...")
        inputs = [TextEmbeddingInput(text="test", task_type="RETRIEVAL_DOCUMENT")]
        embeddings = model.get_embeddings(inputs)
        
        logger.info(f"Success! Generated {len(embeddings)} embeddings.")
        print("VERIFICATION_SUCCESS")
    except Exception as e:
        logger.error(f"Vertex AI Test Failed: {e}", exc_info=True)
        print(f"VERIFICATION_FAILURE: {e}")

if __name__ == "__main__":
    test_vertex_ai()
