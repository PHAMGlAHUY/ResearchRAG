import logging
import time

import httpx
import ollama

from core.load_settings import load_settings
from llm.prompt import build_messages

from contextlib import contextmanager

logger = logging.getLogger("llm")

_cfg = load_settings()["llm"]
PROVIDER = _cfg.get("provider", "ollama")
MODEL_NAME = _cfg["model_name"]
TIMEOUT = _cfg.get("timeout", 60)

# tạo client một lần, dùng lại cho mọi câu hỏi
_client = ollama.Client(host=_cfg.get("base_url", "http://localhost:11434"), timeout=TIMEOUT)
_options = {
    "temperature": _cfg.get("temperature", 0.2),
    "num_predict": _cfg.get("max_tokens", 1024),   # đúng tên key: max_tokens
    "num_ctx": _cfg.get("num_ctx", 8192),
}

class LLMError(RuntimeError):
    """Ollama trả lỗi (ví dụ model chưa pull) hoặc lỗi không mong muốn khi sinh câu trả lời."""

def _check_inputs(context: str, question: str) -> None:
    if not context or not context.strip():
        raise ValueError("Context data cannot be empty.")
    if not question or not question.strip():
        raise ValueError("Question data cannot be empty.")
    if PROVIDER != "ollama":
        raise ValueError(f"Unsupported provider: {PROVIDER}")

@contextmanager
def _translate_errors():
    try:
        yield
    except ollama.ResponseError as e:
        logger.error("Ollama API error: %s", e)
        raise LLMError(f"Ollama return error. Is ollama pulled ? (ollama pull {MODEL_NAME})") from e
    except(ConnectionError, httpx.ConnectError) as e:
        logger.error("Cannot connect to Ollama: %s", e)
        raise ConnectionError("Cannot connect to Ollama") from e
    except httpx.TimeoutException as e:
        logger.error("Ollama request timed out after %ss.", TIMEOUT)
        raise TimeoutError("Request timed out, try again or chage llm.timeout.") from e
    except Exception as e:
        logger.exception("Unexpected error while generating answer")
        raise LLMError("Unexpected error while generating answer") from e

def generate_answer(context: str, question: str) -> str:
    _check_inputs(context, question)
    start = time.perf_counter()
    logger.info("Generating answer using model: %s", MODEL_NAME)
    with _translate_errors():
        response = _client.chat(model=MODEL_NAME,
                                messages=build_messages(context=context, question=question),
                                options=_options)
        answer = response['message']['content'].strip()
    logger.info("Answer generated in %.1fs (%d character)", time.perf_counter() - start, len(answer))
    return answer

def generate_answer_stream(context: str, question: str):
    """Generator trả về từng đoạn văn bản khi Ollama sinh ra."""
    _check_inputs(context, question)
    start = time.perf_counter()
    logger.info("Streaming answer using model: %s", MODEL_NAME)
    total = 0
    with _translate_errors():
        for chunk in _client.chat(model=MODEL_NAME,
                                  messages=build_messages(context=context, question=question),
                                  options=_options,
                                  stream=True):
            piece = chunk['message']['content']
            if piece:
                total += len(piece)
                yield piece
    logger.info("Stream finished in %.1fs (%d character)", time.perf_counter() - start, total)