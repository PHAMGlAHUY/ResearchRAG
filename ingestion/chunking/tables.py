import re
from html.parser import HTMLParser

_TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.DOTALL | re.IGNORECASE)


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._row, self._cell = [], [], []
        self._in_cell, self._span = False, 1

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell, self._in_cell = [], True
            try:
                self._span = min(max(int(dict(attrs).get("colspan") or 1), 1), 50)
            except ValueError:
                self._span = 1
        elif tag == "br" and self._in_cell:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._row.extend([""] * (self._span - 1))      # colspan: giữ đúng số cột
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


def table_to_text(html: str) -> str:
    """Bảng HTML -> bảng markdown (hàng đầu làm header, mỗi dòng bắt đầu bằng '|')."""
    p = _TableParser()
    p.feed(html)
    rows = [[c.replace("|", "\\|") for c in r] for r in p.rows if any(r)]
    if not rows:
        return ""
    w = max(map(len, rows))
    rows = [r + [""] * (w - len(r)) for r in rows]          # đệm hàng thiếu ô
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    lines.insert(1, "|" + " --- |" * w)
    return "\n".join(lines)


def extract_tables(text: str) -> tuple[str, list[str]]:
    """Thay mỗi <table> bằng marker, trả về (văn bản còn lại, danh sách bảng đã chuyển).
    Chưa file nào trong dự án gọi hàm này; xóa nếu bạn không dùng."""
    tables = []

    def _swap(m):
        tables.append(table_to_text(m.group(0)))
        return f"\n\n@@TABLE_{len(tables) - 1}@@\n\n"

    return _TABLE.sub(_swap, text), tables


def inline_tables(text: str) -> str:
    """Thay mỗi <table> bằng bảng markdown."""
    return _TABLE.sub(lambda m: "\n\n" + table_to_text(m.group(0)) + "\n\n", text)