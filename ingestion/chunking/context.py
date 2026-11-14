from langchain_core.documents import Document

HEADER_KEYS = ("Header 1", "Header 2", "Header 3")

def section_path(chunk: Document) -> str:
    return " > ".join(chunk.metadata[k] for k in HEADER_KEYS if chunk.metadata.get(k))

def contextualize(chunk: Document) -> str:
    path = section_path(chunk)
    return f"{path}\n{chunk.page_content}" if path else chunk.page_content

def _clean(h: str) -> str:
    return h.replace("**", "").replace("*", "").strip()

def section_path(chunk):
    return " > ".join(_clean(chunk.metadata[k]) for k in HEADER_KEYS if chunk.metadata.get(k))