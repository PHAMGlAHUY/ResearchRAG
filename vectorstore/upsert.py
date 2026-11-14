import logging
from qdrant_client import QdrantClient

from langchain_core.documents import Document

from core.load_settings import load_settings
from vectorstore.qdrant import get_qdrant_client, ensure_collection
from vectorstore.index import build_qdrant_points

settings = load_settings()
logger = logging.getLogger('vector_database')

QDRANT_CONFIG = settings['vector_database']
COLLECTION_NAME = QDRANT_CONFIG['collection_name']
UPSERT_BATCH_SIZE = QDRANT_CONFIG['upsert_batch_size']


def upsert_chunks(chunks: list[Document]):
    if not chunks:
        logger.warning(f"No chunks provided to build Qdrant points")
        return []

    points = build_qdrant_points(chunks)

    if not points:
        logger.warning("No points were build from the provided chunks")
        return []

    client: QdrantClient = get_qdrant_client()
    ensure_collection(client)

    for start in range(0, len(points), UPSERT_BATCH_SIZE):
        batch = points[start:start + UPSERT_BATCH_SIZE]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)

    logger.info(f"Upserted {len(points)} points from collection {COLLECTION_NAME}.")