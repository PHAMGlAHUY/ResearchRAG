import json
import logging
import time
from collections.abc import Iterator

from api.schemas import ChatResponse, Source
from chat import NO_DOCS_MESSAGE, answer_question, format_context, prepare_question
from llm.generator import LLMError, generate_answer, generate_answer_stream

logger = logging.getLogger('api')

def _section(metadata: dict) -> str:
    return " > ".join(x for x in (metadata.get("Header 1"), metadata.get("Header 2")) if x) or "?"

def _build_sources(documents) -> list[Source]:
    return [
        Source(index=i, section=_section(d.metadata), score=round(d.score, 4), text=d.text)
        for i, d in enumerate(documents, 1)
    ]

def ask(question: str) -> ChatResponse:
    start = time.perf_counter()
    answer, documents = answer_question(question)

    return ChatResponse(
        answer=answer,
        sources=_build_sources(documents),
        latency_ms=int((time.perf_counter() - start) * 1000),
    )

def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _classify(e: Exception) -> tuple[int, str]:
    if isinstance(e, ConnectionError):
        return 503, str(e)
    if isinstance(e, TimeoutError):
        return 504, str(e)
    if isinstance(e, LLMError):
        return 500, str(e)
    return 500, "Unexpected error occured"

def start_stream(question: str) -> Iterator[str]:
    """Chạy phần có thể lỗi (kiểm tra, truy xuất, token đầu) ngay tại đây,
        để lỗi nổi lên thành HTTP 400/503/504 trước khi luồng SSE bắt đầu."""
    start = time.perf_counter()
    question, documents = prepare_question(question)
    sources = _build_sources(documents)

    if documents:
        tokens = generate_answer_stream(context=format_context(documents), question=question)
    else:
        tokens = iter([NO_DOCS_MESSAGE])
    first = next(tokens, "")

    def events() -> Iterator[str]:
        yield _sse("sources", [s.model_dump() for s in sources])

        if first:
            yield _sse("token", {"t": first})
        try:
            for piece in tokens:
                yield _sse("token", {"t": piece})
        except Exception as e:
            logger.exception("Stream interrupted")
            status, msg = _classify(e)
            yield _sse("error", {"detail": msg, "status": status})
            return
        yield _sse("done", {"latency_ms": int((time.perf_counter() - start) * 1000)})

    return events()