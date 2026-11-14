import sys
import logging
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from ingestion.chunking.cleaner import clean_markdown, simplify_mermaid, normalize_headings, remove_sections
from ingestion.chunking.tables import inline_tables

from core.load_settings import load_settings
from core.setup_logging import setup_logging

from transformers import AutoTokenizer

setup_logging()
settings = load_settings()
logger = logging.getLogger('ingestion')

OUTPUT_PATH = Path(settings['data']['processed_dir'])

_tokenizer = None

def _get_tokenizer():
    """Tokenizer của chính model embedding, nạp một lần."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(settings['embedding']['model'])
        _tokenizer.model_max_length = 10**9      # tắt cảnh báo "sequence longer than 512"
    return _tokenizer

def _build_headers() -> list[tuple[str, str]]:
    levels = settings['chunking'].get('header_levels', 2)
    return [("#" * n, f"Header {n}") for n in range(1, levels + 1)]

def _build_text_splitter() -> RecursiveCharacterTextSplitter:
    cfg = settings['chunking']
    if cfg.get('mode', 'char') == 'token':
        return RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            _get_tokenizer(),
            chunk_size=cfg['token_chunk_size'],
            chunk_overlap=cfg['token_chunk_overlap'],
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=cfg['chunk_size'],
        chunk_overlap=cfg['chunk_overlap'],
    )

def split_text_into_chunks(markdown_content: str, source: str = "unknown") -> list[Document]:
    """Chunking 2 tầng: Markdown Headers + Recursive Character."""
    if not markdown_content:
        logger.warning("Input content is empty. Unable to perform chunking!.")
        return []

    try:
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

        # clean mark down before chunking
        markdown_content = clean_markdown(markdown_content)
        markdown_content = inline_tables(markdown_content)
        markdown_content = simplify_mermaid(markdown_content)
        markdown_content = normalize_headings(markdown_content)
        markdown_content = remove_sections(markdown_content)

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_build_headers(),
            strip_headers=False,
        )
        md_header_splits = markdown_splitter.split_text(markdown_content)

        # Tầng 2: chuẩn hóa kích thước
        text_splitter = _build_text_splitter()

        # 1) GÁN final_chunks trước
        final_chunks = text_splitter.split_documents(md_header_splits)

        # 2) RỒI mới lọc chunk ngắn
        final_chunks = [c for c in final_chunks if len(c.page_content.strip()) >= 50]
        logger.info(f"Content split into {len(final_chunks)} complete chunks.")

        # 3) Dọn file cũ rồi lưu file mới
        for old in OUTPUT_PATH.glob("*.md"):
            old.unlink()

        final_chunks = text_splitter.split_documents(md_header_splits)
        final_chunks = [c for c in final_chunks if len(c.page_content.strip()) >= 50]

        for i, chunk in enumerate(final_chunks):
            chunk.metadata.update({
                "source": source,
                "chunk_index": i,
                "n_chars": len(chunk.page_content),
            })

        logger.info(f"Content split into {len(final_chunks)} complete chunks.")

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
    name = "2005.11401v4.md"
    split_text_into_chunks(load_data(name), source=name)