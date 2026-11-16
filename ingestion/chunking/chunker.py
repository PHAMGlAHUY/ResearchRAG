import argparse
import hashlib
import logging
import re
import shutil
from collections import Counter
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import Language, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from transformers import AutoTokenizer

from ingestion.chunking.cleaner import clean_markdown, simplify_mermaid, normalize_headings, remove_sections
from ingestion.chunking.context import section_path
from ingestion.chunking.validator import check_or_raise, validate_chunks

from ingestion.chunking.tables import inline_tables
from core.load_settings import load_settings
from core.setup_logging import setup_logging

setup_logging()
settings = load_settings()
logger = logging.getLogger('ingestion')

OUTPUT_PATH = Path(settings['data']['processed_dir'])

# tokenizer and measurement

@lru_cache(maxsize=2)
def _load_tokenizer(model: str):
    token = AutoTokenizer.from_pretrained(model)
    token.model_max_length = 10**9
    return token

def _get_tokenizer(model: str | None = None):
    return _load_tokenizer(model or settings['embedding']['model'])

def _is_token_mode(cfg: dict) -> bool:
    return cfg.get('mode', 'char') == 'token'

def _length_fn(cfg: dict):
    if _is_token_mode(cfg):
        token = _get_tokenizer()
        return lambda t: len(token.encode(t, add_special_tokens=False))
    return len

# header

_ATX = re.compile(r'^(#{1,6})\s+\S')

def count_heading_levels(text: str) -> Counter:
    # count heading by level
    counts, fence = Counter(), None

    for line in text.splitlines():
        s = line.lstrip()
        if fence is None and s.startswith(('```', '~~~')):
            fence = s[:3]
        elif fence is not None:
            if s.startswith(fence):
                fence = None
        elif (m := _ATX.match(line)):
            counts[len(m.group(1))] += 1

    return counts

def _build_headers(text: str | None = None, cfg: dict | None = None) -> list[tuple[str, str]]:
    cfg = cfg or settings['chunking']
    cfg_levels = cfg.get('header_levels', 2)
    found = count_heading_levels(text) if text else Counter()
    max_found = max(found, default=0)

    if cfg_levels == 'auto':
        levels = max(max_found, 1)
    else:
        levels = int(cfg_levels)
        if not 1 <= levels <= 6:
            raise ValueError(f"header_levels needs to be between 1 and 6. Got {levels}")

    logger.debug("Heading in document: %s | header_levels=%s -> use %d", dict(sorted(found.items())), cfg_levels, levels)

    lost = {f"H{k}": v for k, v in sorted(found.items()) if k > levels}

    if lost:
        logger.warning("Heading is deeper than header_levels=%d, not add to metadata: %s. Put header_levels='auto' to keep it", levels, lost)

    return [('#' * n, f"Header {n}") for n in range(1, levels + 1)]

# handling

def preprocess(text: str, cfg: dict) -> str:
    text = inline_tables(text)
    text = clean_markdown(text)
    text = simplify_mermaid(text)
    text = normalize_headings(text)

    return remove_sections(text)

def split_markdown(text: str, cfg: dict) -> list[Document]:
    tier1 = MarkdownHeaderTextSplitter(
        headers_to_split_on=_build_headers(text, cfg),
        strip_headers=False,
    )

    if _is_token_mode(cfg):
        size, overlap = cfg['token_chunk_size'], cfg['token_chunk_overlap']
    else:
        size, overlap = cfg['chunk_size'], cfg['chunk_overlap']

    tier2 = RecursiveCharacterTextSplitter.from_language(
        Language.MARKDOWN,
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=_length_fn(cfg),
        add_start_index=True,
    )

    return tier2.split_documents(tier1.split_text(text))

def postprocess(chunks: list[Document], source: str, cfg: dict) -> list[Document]:
    length = _length_fn(cfg)
    min_len = cfg.get('min_chunk_size', 20)

    merged: list[Document] = []
    for c in chunks:
        body = c.page_content.strip()
        if not body:
            continue

        same_parent = bool(merged) and all(
            merged[-1].metadata.get(k) == c.metadata.get(k)
            for k in ('Header 1', 'Header 2')
        )

        if length(body) < min_len and same_parent:
            merged[-1].page_content += '\n\n' + body
        else:
            merged.append(c)

    unit = 'n_tokens' if _is_token_mode(cfg) else 'n_chars'
    for i, c in enumerate(merged):
        c.metadata.update({"source": source, "chunk_index": i, unit: length(c.page_content)})
        c.metadata["section_path"] = section_path(c)  # thêm dòng này
        key = f"{source}|{i}|{c.page_content}".encode()
        c.metadata["chunk_id"] = hashlib.sha1(key).hexdigest()[:16]
    return merged

def dump_chunks(chunks: list[Document], source: str, root: Path) -> None:
    out = root / Path(source).stem
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for c in chunks:
        deepest = next(
            (c.metadata[k] for k in ("Header 6", "Header 5", "Header 4",
                                     "Header 3", "Header 2", "Header 1")
             if c.metadata.get(k)),
            "chunk",
        )
        name = "".join(ch for ch in deepest if ch.isalnum() or ch in " _-") \
            .strip().replace(" ", "_")[:40]
        (out / f"{c.metadata['chunk_index'] + 1}_{name}.md").write_text(
            c.page_content, encoding="utf-8")
    logger.info("Dumped %d chunks to %s", len(chunks), out)

# coordination

def split_text_into_chunks(markdown_content: str, source: str = 'unknown', cfg: dict | None = None) -> list[Document]:
    cfg = cfg or settings['chunking']
    check_or_raise(markdown_content, source, logger)

    if not markdown_content or not markdown_content.strip():
        raise ValueError(f"{source}: Document empty")

    try:
        text = preprocess(markdown_content, cfg)
        chunks = postprocess(split_markdown(text, cfg), source, cfg)
        for it in validate_chunks(chunks, limit=512, length_fn=_length_fn(cfg)):
            logger.warning("[%s] %s", it.code, it.msg)
    except Exception:
        logger.exception("Chunking failed for %s", source)
        raise

    logger.info("%s -> %d chunks", source, len(chunks))

    if cfg.get('dump_chunks'):
        dump_chunks(chunks, source, OUTPUT_PATH)
    return chunks

if __name__ == "__main__":
    from ingestion.load_data import load_data

    ap = argparse.ArgumentParser(description="Chunk một tài liệu markdown")
    ap.add_argument("name", help="tên file, ví dụ 2005.11401v4.md")
    ap.add_argument("--dump", action="store_true", help="ghi chunk ra thư mục processed")
    args = ap.parse_args()

    cfg = {**settings['chunking'], 'dump_chunks': args.dump or settings['chunking'].get('dump_chunks', False)}
    result = split_text_into_chunks(load_data(args.name), source=args.name, cfg=cfg)
    print(f"{len(result)} chunks")