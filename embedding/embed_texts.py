import logging
from sentence_transformers import SentenceTransformer
from core.load_settings import load_settings

settings = load_settings()
logger = logging.getLogger('embedding')

EMBEDDING_MODEL = settings['embedding']['model']
EMBEDDING_DEVICE = settings['embedding'].get('device', 'cpu')
EMBEDDING_BATCH_SIZE = settings['embedding'].get('batch_size', 32)

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model {EMBEDDING_MODEL}.")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
    return _model

def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    if not texts:
        logger.warning("No texts provided for embedding.")
        return []

    prefix = "query: " if is_query else "passage:"
    prefixed = [prefix + t for t in texts]

    embeddings = get_model().encode(
        prefixed,
        batch_size=EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_tensor=True,
        show_progress_bar=False,
    ).tolist()

    logger.info(f"Completed embedding {len(texts)} texts.")
    return embeddings