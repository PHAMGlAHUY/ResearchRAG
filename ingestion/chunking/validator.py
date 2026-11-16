"""Kiểm tra tài liệu markdown TRƯỚC khi chunk, và kiểm tra chunk SAU khi tách.

Chỉ phát hiện vấn đề, không sửa gì. Mỗi vấn đề có mức:
    error : dữ liệu hỏng, nên dừng (check_or_raise sẽ raise)
    warn  : chạy được nhưng chất lượng chunk sẽ kém
    info  : thông tin tham khảo

Dùng trong pipeline:
    from ingestion.chunking.validator import check_or_raise, validate_chunks
    check_or_raise(markdown, source, logger)           # đầu split_text_into_chunks

Dùng như CLI (quét file hoặc thư mục):
    python -m ingestion.chunking.validator data/raw            # bảng tổng hợp
    python -m ingestion.chunking.validator a.md --details      # liệt kê từng vấn đề
    python -m ingestion.chunking.validator data/raw --strict   # warn cũng tính là lỗi
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

LEVELS = ("error", "warn", "info")


@dataclass
class Issue:
    level: str            # "error" | "warn" | "info"
    code: str
    line: int | None
    msg: str


_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_ATX = re.compile(r"^\s{0,3}(#{1,6})(?:\s+(.*?))?\s*#*\s*$")
_SETEXT = re.compile(r"^\s{0,3}(=+|-{2,})\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_HTML_TABLE_OPEN = re.compile(r"<table\b", re.IGNORECASE)
_HTML_TABLE_CLOSE = re.compile(r"</table\s*>", re.IGNORECASE)


def _ncols(line: str) -> int:
    return len(re.split(r"(?<!\\)\|", line.strip().strip("|")))


def _front_matter_end(lines: list[str]) -> int:
    """Chỉ số dòng cuối của front-matter YAML (0 nếu không có, -1 nếu mở mà không đóng)."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, min(len(lines), 80)):
        if lines[i].strip() in ("---", "..."):
            return i + 1
    return -1


def validate_markdown(
    text: str,
    max_section_chars: int = 8000,
    min_section_chars: int = 50,
    repeat_threshold: int = 5,
) -> list[Issue]:
    issues: list[Issue] = []

    def add(level, code, line, msg):
        issues.append(Issue(level, code, line, msg))

    if not text or not text.strip():
        add("error", "EMPTY", None, "Tài liệu rỗng")
        return issues
    if "\x00" in text:
        add("error", "NULL_BYTE", None, "Có ký tự NULL, file có thể bị hỏng")
    if (n := text.count("\ufffd")):
        add("warn", "BAD_ENCODING", None, f"{n} ký tự thay thế '\\ufffd', nghi sai encoding")
    if "\r" in text:
        add("info", "CRLF", None, "Có xuống dòng kiểu Windows (clean_markdown sẽ chuẩn hóa)")

    lines = text.replace("\r\n", "\n").split("\n")

    fm_end = _front_matter_end(lines)
    if fm_end == -1:
        add("warn", "FRONT_MATTER", 1, "Front-matter mở nhưng không thấy dấu đóng '---'")
        fm_end = 0

    fence: tuple[str, int, int] | None = None     # (ký tự, độ dài, dòng mở)
    headings: list[tuple[int, int, str]] = []      # (dòng, cấp, tiêu đề)
    prev_level = 0
    table_cols: int | None = None
    mermaid_open = False

    for i in range(fm_end, len(lines)):
        line, ln = lines[i], i + 1

        m = _FENCE.match(line)
        if m:
            ch, size, info = m.group(1)[0], len(m.group(1)), m.group(2).strip()
            if fence is None:
                if ch == "`" and "`" in info:      # ```code``` trên một dòng, không phải fence
                    pass
                else:
                    fence = (ch, size, ln)
                    mermaid_open = info.lower().startswith("mermaid")
            elif ch == fence[0] and size >= fence[1] and not info:
                fence, mermaid_open = None, False
            continue
        if fence:                                   # trong code block: bỏ qua mọi kiểm tra
            continue

        h = _ATX.match(line)
        if h:
            level, title = len(h.group(1)), (h.group(2) or "").strip()
            if not title:
                add("warn", "EMPTY_HEADING", ln, "Heading không có tiêu đề")
            else:
                if prev_level and level > prev_level + 1:
                    add("warn", "HEADING_SKIP", ln,
                        f"Nhảy cấp H{prev_level} -> H{level}: {title[:40]}")
                headings.append((ln, level, title))
                prev_level = level
            table_cols = None
            continue

        if (_SETEXT.match(line) and i > fm_end and lines[i - 1].strip()
                and not lines[i - 1].lstrip().startswith(("|", "-", "*", ">", "#", "+"))
                and not _SETEXT.match(lines[i - 1])):
            add("warn", "SETEXT", ln,
                f"Heading kiểu setext (splitter không nhận): {lines[i - 1].strip()[:40]}")
            continue

        if _TABLE_SEP.match(line) and i > 0 and "|" in lines[i - 1]:
            table_cols = _ncols(lines[i - 1])
        elif table_cols is not None:
            if "|" in line and line.strip():
                if _ncols(line) != table_cols:
                    add("warn", "TABLE_COLS", ln,
                        f"Bảng lệch cột (header {table_cols}, dòng này {_ncols(line)})")
            else:
                table_cols = None

    if fence:
        kind = "mermaid " if mermaid_open else ""
        add("error", "UNCLOSED_FENCE", fence[2],
            f"Khối {kind}code mở nhưng không đóng, phần sau bị coi là code")

    # bảng HTML
    n_open, n_close = len(_HTML_TABLE_OPEN.findall(text)), len(_HTML_TABLE_CLOSE.findall(text))
    if n_open != n_close:
        add("error", "HTML_TABLE_UNBALANCED", None,
            f"<table> mở {n_open} lần nhưng đóng {n_close} lần, inline_tables sẽ cắt sai")

    # cấu trúc heading
    if not headings:
        add("warn", "NO_HEADINGS", None, "Không có heading, tầng 1 sẽ không tách được")
    else:
        if sum(1 for _, lv, _ in headings if lv == 1) > 1:
            add("info", "MULTI_H1", None, "Có nhiều hơn một H1")
        if headings[0][1] > 1:
            add("info", "NO_TOP_H1", headings[0][0],
                f"Heading đầu tiên là H{headings[0][1]}, không có H1")
        titles = Counter((lv, t.lower()) for _, lv, t in headings)
        dup = [t for (lv, t), c in titles.items() if c > 1]
        if dup:
            add("info", "DUP_HEADINGS", None,
                f"{len(dup)} tiêu đề trùng cùng cấp (vd {dup[0]!r}), section_path có thể mơ hồ")

        bounds = [h[0] - 1 for h in headings] + [len(lines)]
        for (ln, _, title), a, b in zip(headings, bounds, bounds[1:]):
            size = len("\n".join(lines[a:b]))
            if size > max_section_chars:
                add("info", "LONG_SECTION", ln,
                    f"Mục '{title[:30]}' dài {size} ký tự, sẽ bị cắt nhiều lần")
            elif size < min_section_chars:
                add("info", "SHORT_SECTION", ln, f"Mục '{title[:30]}' chỉ {size} ký tự")

    # rác OCR / PDF
    visible = [c for c in text if not c.isspace()]
    letters = sum(c.isalnum() for c in visible)
    if visible and letters / len(visible) < 0.6:
        add("warn", "NOISY", None,
            f"Chỉ {letters / len(visible):.0%} ký tự là chữ/số, nghi nhiễu OCR")
    rep = Counter(l.strip() for l in lines if len(l.strip()) > 10)
    rep = [(l, c) for l, c in rep.items() if c >= repeat_threshold and not _TABLE_SEP.match(l)]
    if rep:
        l, c = max(rep, key=lambda x: x[1])
        add("warn", "REPEATED_LINES", None,
            f"{len(rep)} dòng lặp >= {repeat_threshold} lần (header/footer trang?), "
            f"nhiều nhất {c} lần: {l[:40]!r}")

    return issues


def validate_chunks(chunks, limit: int = 512, min_len: int = 20, length_fn=len,
                    embed_prefix: str = "passage: ") -> list[Issue]:
    """Kiểm tra SAU khi tách. `chunks`: list[Document]; `length_fn`: hàm đo (token hoặc ký tự).
    Đo cả tiền tố embed và breadcrumb vì đó mới là chuỗi thật sự đi vào model."""
    issues: list[Issue] = []
    if not chunks:
        return [Issue("error", "NO_CHUNKS", None, "Không có chunk nào")]

    ids = Counter(c.metadata.get("chunk_id") for c in chunks if c.metadata.get("chunk_id"))
    for cid, n in ids.items():
        if n > 1:
            issues.append(Issue("error", "DUP_CHUNK_ID", None, f"chunk_id {cid} xuất hiện {n} lần"))

    for i, c in enumerate(chunks):
        body = c.page_content.strip()
        path = c.metadata.get("section_path", "")
        if not body:
            issues.append(Issue("error", "EMPTY_CHUNK", i, f"Chunk {i} rỗng"))
            continue
        n = length_fn(embed_prefix + (path + "\n" if path else "") + body)
        if n > limit:
            issues.append(Issue("warn", "CHUNK_TOO_BIG", i, f"Chunk {i}: {n} > {limit} (sau khi thêm tiền tố)"))
        elif length_fn(body) < min_len:
            issues.append(Issue("info", "CHUNK_TINY", i, f"Chunk {i}: {length_fn(body)} < {min_len}"))
        if not any(k.startswith("Header ") for k in c.metadata):
            issues.append(Issue("info", "NO_HEADER_META", i, f"Chunk {i} không có heading trong metadata"))
    return issues


def check_or_raise(text: str, source: str, logger=None, **kw) -> list[Issue]:
    """Ghi log mọi vấn đề; raise ValueError nếu có error."""
    issues = validate_markdown(text, **kw)
    if logger:
        log = {"error": logger.error, "warn": logger.warning, "info": logger.info}
        for it in issues:
            where = f"{source}:{it.line}" if it.line else source
            log[it.level](f"[{it.code}] {where} - {it.msg}")
    errors = [i for i in issues if i.level == "error"]
    if errors:
        raise ValueError(f"{source}: markdown không hợp lệ "
                         f"({', '.join(sorted({e.code for e in errors}))})")
    return issues


# ───────────────────────── CLI ─────────────────────────

def _collect(paths: list[str], pattern: str) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        files += sorted(p.rglob(pattern)) if p.is_dir() else [p]
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm tra tài liệu markdown trước khi chunk")
    ap.add_argument("paths", nargs="+", help="file hoặc thư mục")
    ap.add_argument("--glob", default="*.md", help="mẫu tên file khi quét thư mục")
    ap.add_argument("--details", action="store_true", help="liệt kê từng vấn đề")
    ap.add_argument("--json", action="store_true", help="xuất JSON")
    ap.add_argument("--strict", action="store_true", help="warn cũng làm exit code = 1")
    ap.add_argument("--max-section", type=int, default=8000)
    a = ap.parse_args(argv)

    files = _collect(a.paths, a.glob)
    if not files:
        print("Không tìm thấy file nào", file=sys.stderr)
        return 2

    report = {}
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            report[str(f)] = validate_markdown(text, max_section_chars=a.max_section)
        except UnicodeDecodeError:
            report[str(f)] = [Issue("error", "NOT_UTF8", None, "Không đọc được bằng UTF-8")]

    if a.json:
        print(json.dumps({k: [asdict(i) for i in v] for k, v in report.items()},
                         ensure_ascii=False, indent=2))
    else:
        w = min(max(len(k) for k in report), 50)
        print(f"{'File':<{w}}  {'err':>3} {'warn':>4} {'info':>4}  Mã chính")
        print("-" * (w + 40))
        for name, its in report.items():
            c = Counter(i.level for i in its)
            top = Counter(i.code for i in its if i.level != "info").most_common(2)
            shown = name if len(name) <= w else "..." + name[-(w - 3):]
            print(f"{shown:<{w}}  {c['error']:>3} {c['warn']:>4} {c['info']:>4}  "
                  f"{', '.join(k for k, _ in top) or 'OK'}")
            if a.details:
                for i in its:
                    loc = f"dòng {i.line}" if i.line else "toàn file"
                    print(f"    [{i.level:5}] {i.code:<22} {loc:<10} {i.msg}")

    n_err = sum(any(i.level == "error" for i in v) for v in report.values())
    n_warn = sum(any(i.level == "warn" for i in v) for v in report.values())
    if not a.json:
        print(f"\n{len(report)} file | {n_err} có lỗi | {n_warn} có cảnh báo")
    return 1 if n_err or (a.strict and n_warn) else 0


if __name__ == "__main__":
    sys.exit(main())