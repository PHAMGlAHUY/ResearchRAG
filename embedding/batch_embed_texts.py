import logging

from core.load_settings import load_settings
from embedding.embed_texts import embed_texts

settings = load_settings()
logger = logging.getLogger('embedding')

EMBEDDING_BATCH_SIZE = settings['embedding'].get('batch_size', 32)

def batch_embed_texts(texts: list[str]) -> list[list[str]]:
    if not texts:
        logger.warning("No texts provided for embedding")
        return []

    all_emddings = []

    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start: start + EMBEDDING_BATCH_SIZE]

        batch_embeddings = embed_texts(batch)

        # thay append thanh extend
        all_emddings.extend(batch_embeddings)

        logger.info(f"Embedded batch {start // EMBEDDING_BATCH_SIZE + 1} with {len(batch)} texts.")

    return all_emddings