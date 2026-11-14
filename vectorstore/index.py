import logging
import uuid #each point has distinct id

from langchain_core.documents import Document
from qdrant_client.conversions.common_types import SparseVector
from qdrant_client.models import PointStruct

from core.load_settings import load_settings
from embedding.embed_texts import embed_texts
from ingestion.chunking.context import contextualize

settings = load_settings()
logger = logging.getLogger('vector_database')

def make_point_id(source: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{source}:{chunk_index}'))

def build_qdrant_points(chunks, sparse_embedder) -> list[PointStruct]:
    if not chunks:
        logger.warning("No chunks provided to build Qdrant points.")
        return []

    texts = [contextualize(c) for c in chunks]
    dense = embed_texts(texts)

    if len(dense) != len(chunks):
        raise ValueError(f"Embedding numbers {len(dense)} differ to the number of chunks {len(chunks)}.")

    points = []

    for chunk, text, dvec in zip(chunks, texts, dense):
        source = chunk.metadata.get('source', 'unknown')
        index = chunk.metadata.get('chunk_index')

        if index is None:
            raise ValueError("Missing required metadata field 'chunk_index' in chunk")

        idx, val = sparse_embedder.encode_document(text)

        points.append(
            PointStruct(
                id=make_point_id(source, index),
                vector={
                    'dense': dvec,
                    'sparse': SparseVector(indices=idx, values=val)
                },
                payload={
                    **chunk.metadata,
                    'text': chunk.page_content,
                },
            )

        )

    logger.info(f"Built {len(points)} Qdrant points.")

    return points