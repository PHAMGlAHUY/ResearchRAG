import re
from html.parser import HTMLParser

from langchain_core.documents import Document

_TABLE = re.compile(r"<table>.*?</table>", re.DOTALL)

class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell, self._in_cell = [], [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell, self._in_cell = [], True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)

def table_to_text(html: str) -> str:
    """Mỗi hàng một dòng, các ô cách nhau bằng ' | '."""
    p = _TableParser()
    p.feed(html)
    return "\n".join(" | ".join(c for c in row) for row in p.rows if any(row))

def extract_tables(text: str) -> tuple[str, list[str]]:
    """Thay mỗi <table> bằng marker, trả về (văn bản còn lại, danh sách bảng đã chuyển)."""
    tables = []

    def _swap(m):
        tables.append(table_to_text(m.group(0)))
        return f"\n\n@@TABLE_{len(tables) - 1}@@\n\n"

    return _TABLE.sub(_swap, text), tables

def inline_tables(text: str) -> str:
    """Thay mỗi <table> bằng văn bản: mỗi hàng một dòng, các ô cách nhau bằng ' | '."""
    return _TABLE.sub(lambda m: "\n\n" + table_to_text(m.group(0)) + "\n\n", text)