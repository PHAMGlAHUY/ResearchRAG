import logging
import re

logger = logging.getLogger('ingestion')

_HEAD = re.compile(r"^(#{1,6})\s")
_NUM_HEADING = re.compile(r"^#{1,6}\s*(\d+(?:\.\d+)*)[.\s]")        # "2.1 Models"
_APPENDIX_TITLE = re.compile(r"^#{1,6}\s+appendices?\b", re.IGNORECASE)
_APPENDIX_ITEM = re.compile(r"^#{1,6}\s+[A-Z]\s+\S")                # "A Implementation Details"

_MERMAID = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_MERMAID_BRACKET = re.compile(r'[\[\(\{]+"?([^\[\]\(\)\{\}"]+)"?[\]\)\}]+')   # A["x"], A[x], A(x), A{x}
_MERMAID_EDGE = re.compile(r"\|([^|\n]+)\|")                                  # A -->|nhãn| B
_HAS_WORD = re.compile(r"[^\W\d_]{2,}")      # có ít nhất 2 chữ cái (kể cả tiếng Việt)

# Mục bị bỏ mặc định (phụ lục được giữ lại)
DEFAULT_DROP = (
    "references", "reference", "bibliography",
    "acknowledgments", "acknowledgements", "acknowledgment", "acknowledgement",
    "tài liệu tham khảo", "lời cảm ơn",
)


# ───────────── tiện ích: bỏ qua code block ─────────────

def iter_lines(text: str):
    """Yield (dòng, đang_trong_code). Dòng mở và đóng fence cũng tính là code."""
    fence = None
    for line in text.splitlines(keepends=True):
        s = line.lstrip()
        if fence is None and s.startswith(("```", "~~~")):
            fence = s[:3]
            yield line, True
        elif fence is not None:
            if s.startswith(fence):
                fence = None
            yield line, True
        else:
            yield line, False


def _split_code(text: str) -> list[tuple[str, bool]]:
    """Gộp các dòng liên tiếp cùng loại thành đoạn: [(đoạn, là_code)]."""
    segs, buf, cur = [], [], False
    for line, in_code in iter_lines(text):
        if buf and in_code != cur:
            segs.append(("".join(buf), cur))
            buf = []
        cur = in_code
        buf.append(line)
    if buf:
        segs.append(("".join(buf), cur))
    return segs


# ───────────── làm sạch chung ─────────────

def clean_markdown(text: str, join_hyphen: bool = True) -> str:
    """Làm sạch văn xuôi; code block giữ nguyên.
    join_hyphen: nối 'inter-\\nnational' -> 'international' (đúng với văn bản từ PDF,
    nên tắt với markdown gốc vì 'end-\\nto-end' sẽ thành 'endto-end')."""
    text = text.replace("\r\n", "\n").replace("\u00ad", "")
    parts = []
    for seg, is_code in _split_code(text):
        if not is_code:
            if join_hyphen:
                seg = re.sub(r"(\w)-\n(\w)", r"\1\2", seg)
            seg = re.sub(r"^[ \t]*\d{1,3}[ \t]*$", "", seg, flags=re.MULTILINE)  # dòng chỉ có số trang
            seg = re.sub(r"[ \t]+\n", "\n", seg)
            seg = re.sub(r"\n{3,}", "\n\n", seg)
        parts.append(seg)
    return "".join(parts).strip()


# ───────────── mermaid ─────────────

def simplify_mermaid(text: str) -> str:
    """Biến khối ```mermaid thành một câu liệt kê nhãn.
    Không rút được nhãn nào thì GIỮ NGUYÊN khối (không làm mất hình)."""
    def _labels(m: re.Match) -> str:
        body = m.group(1)
        found = _MERMAID_BRACKET.findall(body) + _MERMAID_EDGE.findall(body)
        labels = []
        for label in found:
            label = label.replace("#quot;", '"').strip()
            if _HAS_WORD.search(label):              # bỏ nhãn kiểu q, z1, d(z)
                labels.append(label)
        labels = list(dict.fromkeys(labels))          # bỏ trùng, giữ thứ tự
        if not labels:
            logger.warning("Mermaid block: không rút được nhãn nào, giữ nguyên khối")
            return m.group(0)
        return "Figure (diagram) components: " + "; ".join(labels)

    return _MERMAID.sub(_labels, text)


# ───────────── heading ─────────────

def normalize_headings(text: str, numbered="auto") -> str:
    """Chuẩn hóa heading (bỏ qua code block):
    - bỏ dấu * (in đậm/nghiêng);
    - numbered: đặt cấp theo số mục ('2' -> #, '2.1' -> ##, '2.1.3' -> ###) và xử lý phụ lục.
        True   : luôn áp dụng
        False  : không áp dụng
        "auto" : chỉ áp dụng khi >= 3 heading đánh số mà TẤT CẢ cùng một cấp
                 (dấu hiệu bộ chuyển đổi PDF đã làm phẳng cấp); nếu tài liệu đã có
                 cấu trúc cấp thì tin cấu trúc đó.
    """
    items = []                                        # (dòng, là_heading)
    for line, in_code in iter_lines(text):
        line = line.rstrip("\n")
        if not in_code and _HEAD.match(line):
            line = re.sub(r"\s{2,}", " ", line.replace("*", "")).rstrip()
            items.append((line, True))
        else:
            items.append((line, False))

    num_levels = [len(_HEAD.match(l).group(1)) for l, h in items if h and _NUM_HEADING.match(l)]
    if numbered == "auto":
        apply = len(num_levels) >= 3 and len(set(num_levels)) == 1
    else:
        apply = bool(numbered)
    logger.debug("normalize_headings: numbered=%s, heading đánh số=%d, áp dụng=%s",
                 numbered, len(num_levels), apply)

    out, in_appendix = [], False
    for line, is_head in items:
        if is_head and apply:
            body = re.sub(r"^#{1,6}\s*", "", line)
            if _APPENDIX_TITLE.match(line):
                in_appendix = True
                line = "# Appendices"
            elif in_appendix and _APPENDIX_ITEM.match(line):
                line = "## " + body
            elif (m := _NUM_HEADING.match(line)):
                line = "#" * min(m.group(1).count(".") + 1, 6) + " " + body
        out.append(line)
    return "\n".join(out)


# ───────────── cắt mục ─────────────

def _cut_regex(names) -> re.Pattern:
    alt = "|".join(re.escape(n) for n in names)
    # Khớp TOÀN BỘ tiêu đề: '## 6. References' hoặc '## **Tài liệu tham khảo**' có,
    # '## API Reference' hoặc '## References to prior work' không.
    return re.compile(
        rf"^#{{1,6}}\s*[*_]*\s*(?:(?:\d+|[IVX]+|[A-Z])[.)]?\s+)?(?i:{alt})\s*[*_:]*\s*$"
    )


def remove_sections(text: str, drop=None) -> str:
    """Bỏ mục References/Acknowledgments cho tới heading cùng cấp hoặc cao hơn;
    mục con của nó cũng bị bỏ. Phụ lục được giữ. `drop`: tên mục bổ sung."""
    cut_re = _cut_regex(tuple(DEFAULT_DROP) + tuple(drop or ()))
    kept, cut_level, removed = [], None, 0
    for line, in_code in iter_lines(text):
        if not in_code and (m := _HEAD.match(line)):
            level = len(m.group(1))
            if cut_level is not None and level <= cut_level:
                cut_level = None
            if cut_level is None and cut_re.match(line.rstrip("\n")):
                cut_level = level
        if cut_level is None:
            kept.append(line)
        else:
            removed += len(line)
    logger.info("Removed %d chars from dropped sections", removed)
    return "".join(kept).strip()