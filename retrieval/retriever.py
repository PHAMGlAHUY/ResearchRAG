import logging

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, ScoredPoint
from qdrant_client.http.exceptions import ResponseHandlingException

from core.load_settings import load_settings
from core.schema import RetrievedDocument
from embedding.embed_texts import embed_texts
from vectorstore.qdrant import get_qdrant_client

settings = load_settings()
logger = logging.getLogger('retrieval')

RETRIEVAL_CONFIG = settings['retrieval']
COLLECTION_NAME = settings['vector_database']['collection_name']
RETRIEVAL_TOP_K = RETRIEVAL_CONFIG.get('top_k', 5)
RETRIEVAL_SCORE_THRESHOLD = RETRIEVAL_CONFIG.get('score_threshold', 0.0)
EXCLUDE_LAYERS = RETRIEVAL_CONFIG.get('exclude_layers', [])      # ví dụ: ["tests"]


def retrieve(query: str, exclude_layers: list[str] | None = None) -> list[RetrievedDocument]:
    if not query or not query.strip():
        logger.warning('No query provided for retrieval')
        return []

    exclude = EXCLUDE_LAYERS if exclude_layers is None else exclude_layers
    query_filter = None
    if exclude:
        query_filter = Filter(must_not=[FieldCondition(key="layer", match=MatchAny(any=list(exclude)))])

    try:
        client: QdrantClient = get_qdrant_client()
        vectors = embed_texts([query], is_query=True)  # tiền tố "query: "
        if len(vectors) == 0:
            logger.error("Failed to generate embedding for the query")
            return []

        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vectors[0],
            limit=RETRIEVAL_TOP_K,
            with_payload=True,
            score_threshold=RETRIEVAL_SCORE_THRESHOLD,
            query_filter=query_filter,
        )

        points: list[ScoredPoint] = response.points
        documents = []
        for point in points:
            payload = point.payload or {}
            documents.append(
                RetrievedDocument(
                    id=str(point.id),
                    score=point.score,
                    text=payload.get('text', ''),
                    metadata={k: v for k, v in payload.items() if k != 'text'},
                )
            )

        logger.info("Retrieved %d documents (excluded layers: %s)", len(documents), exclude or "none")
        return documents                            # thay cho khối "return [... res.points]"

    except ResponseHandlingException as e:
        logger.error("Qdrant connection error: %s", e)
        raise ConnectionError("Cannot connect to vector database") from e
    except Exception:
        logger.exception("Error during retrieval")
        return []