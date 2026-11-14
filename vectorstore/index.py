import logging
import uuid #each point has distinct id

from langchain_core.documents import Document
from qdrant_client.models import PointStruct

from core.load_settings import load_settings
from embedding.embed_texts import embed_texts

settings = load_settings()
logger = logging.getLogger('vector_database')

def build_qdrant_points(chunks: list[Document]) -> list[PointStruct]:
    if not chunks:
        logger.warning("No chunks provided to build Qdrant points.")
        return []

    texts = [chunk.page_content for chunk in chunks]

    if not texts:
        logger.warning("No texts found in the provided chunks.")
        return []

    embeddings = embed_texts(texts)
    if not embeddings:
        logger.warning("No embeddings generated for the provided texts.")
        return []

    if len(embeddings) != len(chunks):
        raise ValueError(
            f"Number of embeddings {len(embeddings)} does not match the number of chunks {len(chunks)}."
        )

    points = []

    for chunk, vector in zip(chunks, embeddings):

        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.page_content))

        if hasattr(vector, 'tolist'):
            vector = vector.tolist()

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    **chunk.metadata,
                    'text': chunk.page_content,
                },
            )

        )

    logger.info(f"Built {len(points)} Qdrant points.")

    return points