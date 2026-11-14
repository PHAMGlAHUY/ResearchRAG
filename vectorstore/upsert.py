import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from langchain_core.documents import Document

from core.load_settings import load_settings
from vectorstore.qdrant import get_qdrant_client, ensure_collection
from vectorstore.index import build_qdrant_points

from embedding.sparse_embedder import new_sparse_embedder, SPARSE_STATS_PATH, reset_sparse_embedder
from ingestion.chunking.context import contextualize

settings = load_settings()
logger = logging.getLogger('vector_database')

QDRANT_CONFIG = settings['vector_database']
COLLECTION_NAME = QDRANT_CONFIG['collection_name']
UPSERT_BATCH_SIZE = QDRANT_CONFIG['upsert_batch_size']

SPARSE_STATS_PATH = settings['embedding']['sparse_stats_path']

def delete_by_source(client: QdrantClient, source: str) -> None:
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key='source',
                                 match=MatchValue(value=source))]
        ),
    )

    logger.info(f"Deleted old points of source {source}.")

def upsert_chunks(chunks: list[Document]) -> int:
    if not chunks:
        logger.warning(f"No chunks provided to build Qdrant points")
        return 0

    sparse = new_sparse_embedder().fit([contextualize(c) for c in chunks])
    points = build_qdrant_points(chunks, sparse)

    if not points:
        logger.warning("No points were build from the provided chunks")
        return 0

    client: QdrantClient = get_qdrant_client()
    ensure_collection(client)

    for source in {c.metadata.get('source', 'unknown') for c in chunks}:
        delete_by_source(client, source)

    for start in range(0, len(points), UPSERT_BATCH_SIZE):
        client.upsert(collection_name=COLLECTION_NAME, points=points[start:start + UPSERT_BATCH_SIZE])

    sparse.save(SPARSE_STATS_PATH)  # sau khi nạp xong
    reset_sparse_embedder()

    logger.info(f"Upserted {len(points)} points into collection {COLLECTION_NAME}")
    return len(points)