import logging
import threading
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from core.load_settings import load_settings

settings = load_settings()
logger = logging.getLogger('embedding')

EMBEDDING_MODEL = settings['embedding']['model']
EMBEDDING_DEVICE = settings['embedding'].get('device', 'cpu')
EMBEDDING_BATCH_SIZE = settings['embedding'].get('batch_size', 32)

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "          # có dấu cách, đúng định dạng huấn luyện của e5

_model = None
_lock = threading.Lock()              # tránh nhiều luồng cùng encode / cùng nạp model


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:        # kiểm tra lần hai trong khóa
                logger.info("Loading embedding model %s on %s.", EMBEDDING_MODEL, EMBEDDING_DEVICE)
                _model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
    return _model


def warmup() -> None:
    """Gọi một lần khi khởi động server để lần hỏi đầu không bị chậm."""
    embed_texts(["warmup"], is_query=True)


def _warn_if_truncated(texts: list[str]) -> None:
    model = get_model()
    limit = model.max_seq_length
    lengths = [len(ids) for ids in model.tokenizer(texts, truncation=False)["input_ids"]]
    too_long = [n for n in lengths if n > limit]
    if too_long:
        logger.warning("%d/%d texts exceed %d tokens and will be truncated (max %d).",
                       len(too_long), len(texts), limit, max(too_long))


def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    if not texts:
        logger.warning("No texts provided for embedding.")
        return []

    prefix = QUERY_PREFIX if is_query else PASSAGE_PREFIX
    prefixed = [prefix + t for t in texts]

    model = get_model()
    if not is_query:                  # kiểm tra khi nạp tài liệu, không cần cho từng câu hỏi
        _warn_if_truncated(prefixed)

    with _lock:
        embeddings = model.encode(
            prefixed,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()

    logger.log(logging.INFO if len(texts) > 1 else logging.DEBUG,
               "Completed embedding %d texts.", len(texts))
    return embeddings


@lru_cache(maxsize=256)
def _embed_query_cached(query: str) -> tuple[float, ...]:
    return tuple(embed_texts([query], is_query=True)[0])


def embed_query(query: str) -> list[float]:
    """Nhúng một câu hỏi, có bộ nhớ đệm cho câu lặp lại."""
    return list(_embed_query_cached(query))