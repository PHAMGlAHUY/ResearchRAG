import re

from langchain_core.documents import Document

_HEADER_KEY = re.compile(r"Header (\d+)")


def _clean(h: str) -> str:
    return h.replace("*", "").strip()


def section_path(chunk: Document) -> str:
    """'H1 > H2 > ... > Hn' theo đúng các cấp có trong metadata."""
    keys = sorted(
        (k for k in chunk.metadata if _HEADER_KEY.fullmatch(k)),
        key=lambda k: int(k.split()[1]),
    )
    return " > ".join(_clean(chunk.metadata[k]) for k in keys if chunk.metadata[k])


def contextualize(chunk: Document) -> str:
    """Chuỗi dùng để embed: breadcrumb + nội dung (page_content vẫn giữ sạch)."""
    path = section_path(chunk)
    return f"{path}\n{chunk.page_content}" if path else chunk.page_content