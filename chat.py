import logging
import os

from core.load_settings import load_settings
from core.setup_logging import setup_logging
from retrieval.retriever import retrieve

from llm.generator import generate_answer, LLMError

settings = load_settings()
logger = logging.getLogger("chat")

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "512"))
CONTEXT_DOCS = settings.get("reranking", {}).get("top_k", 5)   # số chunk thực sự đưa cho LLM

NO_DOCS_MESSAGE = "Tôi không tìm thấy thông tin này trong tài liệu đã nạp."

class InvalidQuestion(ValueError):
    """Câu hỏi rỗng hoặc quá dài. API sẽ map sang HTTP 400."""


def format_context(documents) -> str:
    blocks = []
    for i, d in enumerate(documents, 1):
        m = d.metadata
        section = " > ".join(x for x in (m.get("Header 1"), m.get("Header 2")) if x) or "?"
        blocks.append(f"[{i}] {section}\n{d.text}")
    return "\n\n".join(blocks)

def prepare_question(question: str) ->tuple[str, list]:
    """Kiểm tra câu hỏi + truy xuất tài liệu (chưa gọi LLM).

    Trả về (câu hỏi đã strip, documents). Ném InvalidQuestion hoặc ConnectionError.
    """
    question = (question or "").strip()
    if not question:
        raise InvalidQuestion("Question is required")
    if len(question) > MAX_QUERY_LENGTH:
        raise InvalidQuestion(f"Question length exceeds maximum limit: {MAX_QUERY_LENGTH}")

    logger.info("Starting retrieval for the question: %s", question)
    documents = retrieve(question)[:CONTEXT_DOCS]

    if documents:
        logger.info("Retrieved %d documents: %s", len(documents),
                    [(d.metadata.get("Header 1") or d.metadata.get("Header 2"), round(d.score, 3))
                     for d in documents])
    else:
        logger.warning("No documents retrieved for the question: %s", question)
    return question, documents

def answer_question(question: str) -> tuple[str, list]:
    question, documents = prepare_question(question)
    if not documents:
        return NO_DOCS_MESSAGE, []

    answer = generate_answer(context=format_context(documents), question=question)
    return answer, documents


def chat(question: str) -> str:
    """Dành cho CLI: luôn trả về chuỗi, lỗi được đổi thành thông báo."""
    try:
        answer, _ = answer_question(question)
        return answer
    except InvalidQuestion as e:
        logger.warning("%s", e)
        return str(e)
    except (ConnectionError, TimeoutError, LLMError) as e:
        return str(e)
    except Exception:
        logger.exception("Unexpected error in chat pipeline")
        return "Unexpected error occurred while processing the question"


def main():
    setup_logging()
    while True:
        try:
            question = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if question.strip().lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        print(f"Bot: {chat(question)}")


if __name__ == "__main__":
    main()