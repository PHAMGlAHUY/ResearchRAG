import logging
import re

logger = logging.getLogger('ingestion')

# Heading cần bỏ cả mục: References, Acknowledgments (Appendices được giữ lại)
_CUT_HEADING = re.compile(
    r"^#{1,6}\s*[*_]*\s*(?:[\dA-Z]{1,3}[.\s]+)?"
    r"(references?|bibliography|acknowledg(?:e)?ments?)\b",
    re.IGNORECASE,
)
_NUM_HEADING = re.compile(r"^#{1,6}\s*(\d+(?:\.\d+)*)[.\s]")        # "2.1 Models"
_APPENDIX_TITLE = re.compile(r"^#{1,6}\s+appendices?\b", re.IGNORECASE)
_APPENDIX_ITEM = re.compile(r"^#{1,6}\s+[A-Z]\s+\S")                # "A Implementation Details"
_MERMAID = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_MERMAID_LABEL = re.compile(r'\["(.*?)"\]')


def clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\u00ad", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.MULTILINE)   # dòng chỉ có số trang
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def simplify_mermaid(text: str) -> str:
    """Biến khối ```mermaid thành một câu liệt kê nhãn, bỏ cú pháp mũi tên/subgraph."""
    def _labels(m: re.Match) -> str:
        labels = []
        for label in _MERMAID_LABEL.findall(m.group(1)):
            label = label.replace("#quot;", '"').strip()
            if re.search(r"[A-Za-z]{2,}", label):        # bỏ nhãn kiểu q, z1, d(z), pθ
                labels.append(label)
        labels = list(dict.fromkeys(labels))              # bỏ trùng, giữ thứ tự
        return "Figure (diagram) components: " + "; ".join(labels) if labels else ""

    return _MERMAID.sub(_labels, text)


def normalize_headings(text: str) -> str:
    """Chuẩn hóa heading:
    - bỏ dấu * (in đậm/nghiêng) để metadata và text embed sạch;
    - đặt cấp theo số mục: '2' -> #, '2.1' -> ##, '2.1.3' -> ###;
    - phụ lục: 'Appendices for ...' -> '# Appendices', 'A Title' -> '## A Title'.
    """
    out, in_appendix = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            line = re.sub(r"\s{2,}", " ", line.replace("*", "")).rstrip()
            body = re.sub(r"^#{1,6}\s*", "", line)
            if _APPENDIX_TITLE.match(line):
                in_appendix = True
                line = "# Appendices"
            elif in_appendix and _APPENDIX_ITEM.match(line):
                line = "## " + body
            elif (m := _NUM_HEADING.match(line)):
                line = "#" * min(m.group(1).count(".") + 1, 3) + " " + body
        out.append(line)
    return "\n".join(out)


def remove_sections(text: str) -> str:
    """Bỏ các mục References/Acknowledgments (đến heading kế tiếp); giữ Appendices."""
    kept, skipping, removed = [], False, 0
    for line in text.splitlines(keepends=True):
        if line.startswith("#"):
            skipping = bool(_CUT_HEADING.match(line))
        if skipping:
            removed += len(line)
        else:
            kept.append(line)
    logger.info("Removed %d chars from References/Acknowledgments", removed)
    return "".join(kept).strip()