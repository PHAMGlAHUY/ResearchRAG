import logging
from qdrant_client import QdrantClient
from qdrant_client.models import  SparseVectorParams, VectorParams, Distance, PayloadSchemaType


from core.load_settings import load_settings

settings = load_settings()
logger = logging.getLogger('vector_database')

_client = None

VECTOR_DB_SETTINGS = settings['vector_database']
VECTOR_DB_TYPE = VECTOR_DB_SETTINGS.get('type', 'qdrant')
VECTOR_DB_HOST = VECTOR_DB_SETTINGS.get('host', 'localhost')
VECTOR_DB_PORT = VECTOR_DB_SETTINGS.get('port', 6333)
VECTOR_DB_URL = VECTOR_DB_SETTINGS.get('url', f'http://{VECTOR_DB_HOST}:{VECTOR_DB_PORT}')
VECTOR_DB_API_KEY = VECTOR_DB_SETTINGS.get('api_key', None)
VECTOR_DB_COLLECTION = VECTOR_DB_SETTINGS.get('collection_name', 'default_collection')
VECTOR_DB_DISTANCE = VECTOR_DB_SETTINGS.get('distance', 'cosine')
VECTOR_DB_SIZE = VECTOR_DB_SETTINGS.get('vector_size', 384)
VECTOR_DB_TIMEOUT = VECTOR_DB_SETTINGS.get('timeout', 30)

def get_qdrant_client():
    global _client

    if _client is not None:
        return _client

    try:
        if VECTOR_DB_URL:
            logger.info("Connecting to Qdrant via url")
            client = QdrantClient(
                url=VECTOR_DB_URL,
                api_key=VECTOR_DB_API_KEY,
                timeout=VECTOR_DB_TIMEOUT,
            )
        else:
            logger.info(f"Connecting to Qdrant at {VECTOR_DB_HOST}:{VECTOR_DB_PORT}")
            client = QdrantClient(
                host=VECTOR_DB_HOST,
                port=VECTOR_DB_PORT,
                api_key=VECTOR_DB_API_KEY,
                timeout=VECTOR_DB_TIMEOUT,
            )

        client.get_collections()
        _client = client
        logger.info("Successfully connected to Qdrant")
        return _client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant server: {e}")
        raise ConnectionError(f"Failed to connect to Qdrant server: {e}")

def ensure_collection(client: QdrantClient):
    if client.collection_exists(VECTOR_DB_COLLECTION):
        params = client.get_collection(VECTOR_DB_COLLECTION).config.params
        has_dense = isinstance(params.vectors, dict) and "dense" in params.vectors
        has_sparse = bool(params.sparse_vectors) and "sparse" in params.sparse_vectors
        if not (has_dense and has_sparse):
            raise RuntimeError(
                f"Collection {VECTOR_DB_COLLECTION} thiếu vector 'dense'/'sparse'. "
                "Hãy xóa collection rồi chạy lại pipeline."
            )
        logger.info(f"Collection {VECTOR_DB_COLLECTION} already exists")
        return

    logger.info(f"Creating collection {VECTOR_DB_COLLECTION} ...")
    client.create_collection(
        collection_name=VECTOR_DB_COLLECTION,
        vectors_config={"dense": VectorParams(
            size=VECTOR_DB_SIZE,
            distance=Distance[VECTOR_DB_DISTANCE.upper()],
        )},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )

    client.create_payload_index(
        collection_name=VECTOR_DB_COLLECTION,
        field_name='source',
        field_schema=PayloadSchemaType.KEYWORD,
    )

    logger.info(f"Collection {VECTOR_DB_COLLECTION} created successfully")