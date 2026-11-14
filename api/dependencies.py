import logging

import httpx

from core.load_settings import load_settings
from embedding.embed_texts import embed_texts
from embedding.sparse_embedder import get_sparse_embedder
from vectorstore.qdrant import get_qdrant_client

logger = logging.getLogger('api')

settings = load_settings()
COLLECTION_NAME = settings['vector_database']['collection_name']
OLLAMA_URL = settings['llm'].get('base_url', "http://localhost:11434")
MODEL_NAME = settings['llm']['model_name']

def warmup() -> None:
    """Tải trước model embedding để câu hỏi đầu tiên không bị chậm."""
    embed_texts(['warmup'], is_query=True)
    get_sparse_embedder()
    logger.info("Embeddings models loaded")

def check_qdrant() -> tuple[bool, str]:
    try:
        names = [c.name for c in get_qdrant_client().get_collections().collections]
    except Exception as e:
        return False, f"Cannot connect to QDRANT: {e}"
    if COLLECTION_NAME not in names:
        return False, f"No collection {COLLECTION_NAME} in QDRANT, run Ingestion first"
    return True, ""

def check_ollama() -> tuple[bool, str]:
    try:
        r = httpx.get(f'{OLLAMA_URL}/api/tags', timeout=3)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception as e:
        return False, f"Cannot connect to OLLAMA: {e}"
    if MODEL_NAME not in models:
        return False , f"Model not pulled yet (ollama pull {MODEL_NAME})"
    return True, ""
