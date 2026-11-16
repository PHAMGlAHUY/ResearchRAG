import argparse

from ingestion.load_data import load_data
from ingestion.chunking.chunker import split_text_into_chunks, _get_tokenizer
from ingestion.chunking.context import contextualize, section_path


def main(name: str, limit: int = 512, tiny: int = 60) -> None:
    chunks = split_text_into_chunks(load_data(name), source=name)
    if not chunks:
        raise SystemExit("Không có chunk nào")

    tok = _get_tokenizer()
    rows = sorted(
        ((len(tok.encode("passage: " + contextualize(c))), c) for c in chunks),
        key=lambda r: r[0],
    )
    t = [n for n, _ in rows]

    print(f"Số chunk         : {len(t)}")
    print(f"Token min/med/max: {t[0]} / {t[len(t) // 2]} / {t[-1]}")
    print(f"Chunk > {limit}     : {sum(x > limit for x in t)}  (phải bằng 0)")
    print(f"Chunk < {tiny}      : {sum(x < tiny for x in t)}  (chunk vụn)")
    print("3 chunk dài nhất:")
    for n, c in rows[-3:][::-1]:
        print(f"  {n:4d}  {section_path(c)[:60]!r}  {c.page_content[:60]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Thống kê token của các chunk")
    ap.add_argument("name", help="ví dụ 2005.11401v4.md")
    ap.add_argument("--limit", type=int, default=512)
    ap.add_argument("--tiny", type=int, default=60)
    a = ap.parse_args()
    main(a.name, a.limit, a.tiny)