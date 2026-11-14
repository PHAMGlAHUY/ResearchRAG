import logging
import time

import httpx
import ollama

from core.load_settings import load_settings
from llm.prompt import build_messages

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


def generate_answer(context: str, question: str) -> str:
    if not context or not context.strip():
        raise ValueError("Context data cannot be empty.")
    if not question or not question.strip():
        raise ValueError("Question data cannot be empty.")
    if PROVIDER != "ollama":
        raise ValueError(f"Unsupported provider: {PROVIDER}")

    start = time.perf_counter()
    logger.info("Generating answer using model: %s", MODEL_NAME)
    try:
        response = _client.chat(model=MODEL_NAME,
                                messages=build_messages(context, question),
                                options=_options)
        answer = response["message"]["content"].strip()
        logger.info("Answer generated in %.1fs (%d ký tự)", time.perf_counter() - start, len(answer))
        return answer
    except ollama.ResponseError as e:           # ví dụ: model chưa pull (404)
        logger.error("Ollama API error: %s", e)
        raise LLMError(f"Ollama trả về lỗi. Kiểm tra model đã được pull chưa (ollama pull {MODEL_NAME}).") from e
    except (ConnectionError, httpx.ConnectError) as e:   # Ollama không chạy / sai base_url
        logger.error("Cannot connect to Ollama: %s", e)
        raise ConnectionError("Không kết nối được tới Ollama. Kiểm tra dịch vụ đã chạy và base_url trong settings.") from e
    except httpx.TimeoutException as e:
        logger.error("Ollama request timed out after %ss.", TIMEOUT)
        raise TimeoutError("Yêu cầu quá thời gian chờ, thử lại hoặc tăng llm.timeout.") from e
    except Exception as e:
        logger.exception("Unexpected error while generating answer")
        raise LLMError("Đã xảy ra lỗi không mong muốn, thử lại.") from e