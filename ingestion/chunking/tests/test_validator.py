import pytest

from validator import (
    Issue, check_or_raise, main, validate_chunks, validate_markdown,
)


def codes(text, **kw):
    return {i.code for i in validate_markdown(text, **kw)}


# ── lỗi chặn ──
def test_empty():
    assert codes("   \n") == {"EMPTY"}

def test_null_byte():
    assert "NULL_BYTE" in codes("# A\nabc\x00def " * 5)

def test_unclosed_fence_is_error_and_hides_later_checks():
    src = "# Hướng dẫn\n### Cài đặt\n```bash\npip install foo\n| A | B |\n|---|---|\n| 1 | 2 | 3 |\n"
    c = codes(src)
    assert "UNCLOSED_FENCE" in c
    assert "TABLE_COLS" not in c          # nằm trong fence chưa đóng

def test_html_table_unbalanced():
    assert "HTML_TABLE_UNBALANCED" in codes("# A\n<table><tr><td>1</td></tr>\ntext text text text text text text text\n")

def test_check_or_raise():
    with pytest.raises(ValueError, match="UNCLOSED_FENCE"):
        check_or_raise("# A\n```\ncode\n", "x.md")
    assert check_or_raise("# A\n" + "nội dung dài đủ dùng " * 5, "x.md") is not None


# ── cảnh báo ──
def test_heading_skip():
    assert "HEADING_SKIP" in codes("# A\n### C\n" + "x" * 80)

def test_no_headings():
    assert "NO_HEADINGS" in codes("chỉ có văn bản thường, không heading nào cả")

def test_setext():
    assert "SETEXT" in codes("Tiêu đề\n=======\n" + "nội dung " * 20)

def test_hash_in_code_not_heading():
    c = codes("# A\n```bash\n# comment\n#### sâu\n```\n" + "x" * 80)
    assert "HEADING_SKIP" not in c

def test_table_cols():
    assert "TABLE_COLS" in codes("# A\n| a | b |\n|---|---|\n| 1 | 2 | 3 |\n" + "x" * 80)

def test_table_ok():
    assert "TABLE_COLS" not in codes("# A\n| a | b |\n|---|---|\n| 1 | 2 |\n" + "x" * 80)

def test_front_matter_unclosed():
    assert "FRONT_MATTER" in codes("---\ntitle: x\n# A\n" + "x" * 80)

def test_front_matter_closed_not_setext():
    c = codes("---\ntitle: x\n---\n# A\n" + "nội dung " * 20)
    assert "FRONT_MATTER" not in c and "SETEXT" not in c

def test_repeated_lines():
    assert "REPEATED_LINES" in codes("# A\n" + "Journal of Things 2020\ntext\n" * 6)

def test_noisy():
    assert "NOISY" in codes("# A\n" + "@#$%^&*()_+ " * 30)

def test_long_and_short_sections():
    c = codes("# A\nngắn\n# B\n" + "x" * 200, max_section_chars=100)
    assert {"SHORT_SECTION", "LONG_SECTION"} <= c


# ── tài liệu sạch ──
def test_clean_document_has_no_error_or_warn():
    src = "# Guide\n## Install\n" + "Chạy lệnh sau để cài đặt. " * 5 + "\n```bash\npip install x\n```\n"
    assert all(i.level == "info" for i in validate_markdown(src))


# ── validate_chunks ──
class Doc:
    def __init__(self, text, **meta):
        self.page_content, self.metadata = text, meta

def test_chunks_checks():
    chunks = [
        Doc("a " * 400, **{"Header 1": "A"}, chunk_id="1", section_path="A"),
        Doc("ngắn", **{"Header 1": "A"}, chunk_id="2", section_path="A"),
        Doc("bình thường " * 3, chunk_id="2"),
    ]
    c = {i.code for i in validate_chunks(chunks, limit=100, min_len=10, length_fn=lambda s: len(s.split()))}
    assert {"CHUNK_TOO_BIG", "CHUNK_TINY", "DUP_CHUNK_ID", "NO_HEADER_META"} <= c

def test_no_chunks():
    assert validate_chunks([])[0].code == "NO_CHUNKS"


# ── CLI ──
def test_cli_exit_codes(tmp_path, capsys):
    (tmp_path / "ok.md").write_text("# A\n" + "nội dung dài đủ dùng " * 6, encoding="utf-8")
    (tmp_path / "bad.md").write_text("# A\n```\ncode\n", encoding="utf-8")
    assert main([str(tmp_path / "ok.md")]) == 0
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "UNCLOSED_FENCE" in out and "2 file | 1 có lỗi" in out

def test_cli_strict(tmp_path):
    (tmp_path / "w.md").write_text("không có heading nào cả, chỉ văn bản thường dài dài dài", encoding="utf-8")
    assert main([str(tmp_path)]) == 0
    assert main([str(tmp_path), "--strict"]) == 1