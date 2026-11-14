import logging
import os

from core.load_settings import load_settings
from core.setup_logging import setup_logging
from llm.generator import generate_answer
from retrieval.retriever import retrieve

settings = load_settings()
logger = logging.getLogger("chat")

MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "512"))
CONTEXT_DOCS = settings.get("reranking", {}).get("top_k", 5)   # số chunk thực sự đưa cho LLM


def _format_context(documents) -> str:
    blocks = []
    for i, d in enumerate(documents, 1):
        m = d.metadata
        section = " > ".join(x for x in (m.get("Header 1"), m.get("Header 2")) if x) or "?"
        blocks.append(f"[{i}] {section}\n{d.text}")
    return "\n\n".join(blocks)


def chat(question: str) -> str:
    question = (question or "").strip()
    if not question:
        logger.warning("Received empty question.")
        return "Question cannot be empty"
    if len(question) > MAX_QUERY_LENGTH:
        logger.warning("Question length %d exceeds limit %d", len(question), MAX_QUERY_LENGTH)
        return f"Question length exceeds maximum limit: {MAX_QUERY_LENGTH}"

    logger.info("Starting retrieval for the question: %s", question)
    try:
        documents = retrieve(question)[:CONTEXT_DOCS]
        if not documents:
            logger.warning("No documents retrieved for the question: %s", question)
            return "No documents retrieved for the question"

        logger.info("Retrieved %d docs: %s", len(documents),
                    [(d.metadata.get("Header 2") or d.metadata.get("Header 1"), round(d.score, 3))
                     for d in documents])
        return generate_answer(context=_format_context(documents), question=question)  # dùng keyword, tránh đảo tham số
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