import sys
import logging
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core.load_settings import load_settings
from core.setup_logging import setup_logging

setup_logging()
settings = load_settings()
logger = logging.getLogger('ingestion')

OUTPUT_PATH = Path(settings['data']['processed_dir'])


def split_text_into_chunks(markdown_content: str) -> list[Document]:
    """Chunking 2 tầng: Markdown Headers + Recursive Character."""
    if not markdown_content:
        logger.warning("Input content is empty. Unable to perform chunking!.")
        return []

    try:
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

        # Tầng 1: tách theo heading
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        md_header_splits = markdown_splitter.split_text(markdown_content)

        # Tầng 2: chuẩn hóa kích thước
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings['chunking']['chunk_size'],
            chunk_overlap=settings['chunking']['chunk_overlap'],
        )

        # 1) GÁN final_chunks trước
        final_chunks = text_splitter.split_documents(md_header_splits)

        # 2) RỒI mới lọc chunk ngắn
        final_chunks = [c for c in final_chunks if len(c.page_content.strip()) >= 50]
        logger.info(f"Content split into {len(final_chunks)} complete chunks.")

        # 3) Dọn file cũ rồi lưu file mới
        for old in OUTPUT_PATH.glob("*.md"):
            old.unlink()

        for i, chunk in enumerate(final_chunks):
            header_val = (
                chunk.metadata.get("Header 2")
                or chunk.metadata.get("Header 1")
                or f"chunk_{i + 1}"
            )
            safe_filename = "".join(
                c for c in header_val if c.isalnum() or c in (' ', '_', '-')
            ).strip().replace(" ", "_")[:40]

            output_file = OUTPUT_PATH / f"{i + 1}_{safe_filename}.md"
            output_file.write_text(chunk.page_content, encoding="utf-8")
            logger.info(f"Saved chunkm {i + 1} to {output_file.name}")

        return final_chunks

    except Exception:
        logger.exception("An error occurred while chunking the content")
        return []


if __name__ == "__main__":
    from ingestion.load_data import load_data
    split_text_into_chunks(load_data("2005.11401v4.md"))