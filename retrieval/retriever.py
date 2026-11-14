import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector, ScoredPoint
from qdrant_client.http.exceptions import ResponseHandlingException

from core.load_settings import load_settings
from core.schema import RetrievedDocument
from embedding.embed_texts import embed_texts
from embedding.sparse_embedder import get_sparse_embedder
from vectorstore.qdrant import get_qdrant_client

settings = load_settings()
logger = logging.getLogger('retrieval')

COLLECTION_NAME = settings['vector_database']['collection_name']
RETRIEVAL_TOP_K = settings['retrieval'].get('top_k', 5)
PREFETCH_LIMIT = RETRIEVAL_TOP_K * 2          # mỗi nhánh lấy nhiều hơn để RRF có chỗ gộp

FUSION_MODE = settings['retrieval'].get('fusion', 'rrf').lower()
FUSION = Fusion.DBSF if FUSION_MODE == 'dbsf' else Fusion.RRF

def retrieve(query: str) -> list[RetrievedDocument]:
    if not query or not query.strip():
        logger.warning('No query provided for retrieval')
        return []

    try:
        client: QdrantClient = get_qdrant_client()

        dense_vec = embed_texts([query], is_query=True)[0]               # nhánh dense
        s_idx, s_val = get_sparse_embedder().encode_query(query)         # nhánh sparse (BM25)

        prefetch = [Prefetch(query=dense_vec, using="dense", limit=PREFETCH_LIMIT)]
        if s_idx:                                                        # câu hỏi có từ nằm trong vocab
            prefetch.append(
                Prefetch(query=SparseVector(indices=s_idx, values=s_val),
                         using="sparse", limit=PREFETCH_LIMIT)
            )

        response = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=prefetch,
            query=FusionQuery(fusion=FUSION),
            limit=RETRIEVAL_TOP_K,
            with_payload=True,
        )

        points: list[ScoredPoint] = response.points
        documents = [
            RetrievedDocument(
                id=str(p.id),
                score=p.score,
                text=(p.payload or {}).get('text', ''),
                metadata={k: v for k, v in (p.payload or {}).items() if k != 'text'},
            )
            for p in points
        ]
        logger.info("Retrieved %d documents", len(documents))
        return documents

    except ConnectionError:
        raise
    except ResponseHandlingException as e:
        logger.error("Qdrant connection error: %s", e)
        raise ConnectionError("Cannot connect to vector database") from e
    except Exception:
        logger.exception("Error during retrieval")
        return []