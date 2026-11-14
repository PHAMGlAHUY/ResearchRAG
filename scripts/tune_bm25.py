"""Quét k1, b và tùy chọn tokenizer cho nhánh BM25 (offline: không embed, không gọi LLM).

Chạy từ thư mục gốc my_rag:   python -m scripts.tune_bm25
Chunk được đọc từ chính collection Qdrant (đúng thứ đang được index).
"""
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

from embedding.sparse_embedder import SparseEmbedder, TokenizerOptions

QUESTIONS_PATH = Path("eval/questions.json")
K1_GRID = [0.9, 1.2, 1.5, 1.8, 2.1]
B_GRID = [0.3, 0.5, 0.75, 0.9]
CUTOFF = 10                                    # cùng top_k của retriever
BASELINE = (1.5, 0.75, TokenizerOptions())     # cấu hình đang chạy


@dataclass
class Chunk:
    index_text: str      # text đưa vào BM25 (có đường dẫn mục, giống lúc index)
    raw_text: str        # page_content gốc, dùng để kiểm tra đáp án
    label: str


def norm(s: str) -> str:
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return " ".join(s.split()).lower()


def load_chunks_from_qdrant() -> list[Chunk]:
    from langchain_core.documents import Document
    from ingestion.chunking.context import contextualize
    from vectorstore.qdrant import get_qdrant_client, VECTOR_DB_COLLECTION

    points, _ = get_qdrant_client().scroll(
        VECTOR_DB_COLLECTION, limit=10_000, with_payload=True, with_vectors=False)
    docs = [Document(page_content=p.payload["text"],
                     metadata={k: v for k, v in p.payload.items() if k != "text"}) for p in points]
    docs.sort(key=lambda d: d.metadata.get("chunk_index", 0))
    return [Chunk(contextualize(d), d.page_content,
                  f"#{d.metadata.get('chunk_index')} {d.metadata.get('Header 3') or d.metadata.get('Header 2') or d.metadata.get('Header 1') or '?'}")
            for d in docs]


def evaluate(chunks, questions, k1, b, opts):
    """Trả về danh sách hạng (None nếu không có trong top CUTOFF) cho từng câu hỏi."""
    emb = SparseEmbedder(k1, b, opts).fit([c.index_text for c in chunks])
    doc_vecs = [dict(zip(*emb.encode_document(c.index_text))) for c in chunks]
    raw = [norm(c.raw_text) for c in chunks]
    ranks = []
    for q in questions:
        qi, qv = emb.encode_query(q["question"])
        qd = dict(zip(qi, qv))
        scores = [sum(w * d.get(i, 0.0) for i, w in qd.items()) for d in doc_vecs]
        order = sorted(range(len(chunks)), key=lambda j: (-scores[j], j))[:CUTOFF]
        needle, rank = norm(q["needle"]), None
        for pos, j in enumerate(order, 1):
            if scores[j] > 0 and needle in raw[j]:
                rank = pos
                break
        ranks.append(rank)
    return ranks


def metrics(ranks):
    n = len(ranks)
    hit = lambda k: sum(1 for r in ranks if r and r <= k) / n
    mrr = sum(1 / r for r in ranks if r) / n
    return {"mrr": mrr, "h1": hit(1), "h3": hit(3), "h5": hit(5)}


def fmt_opts(o: TokenizerOptions) -> str:
    flags = [n for n in ("stem", "split_hyphen", "numbers", "extra_stopwords") if getattr(o, n)]
    return "+".join(flags) or "legacy"


def main(chunks=None, questions=None):
    chunks = chunks or load_chunks_from_qdrant()
    questions = questions or json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    print(f"{len(chunks)} chunk, {len(questions)} câu hỏi (1 câu đổi hạng ≈ {100 / len(questions):.0f}% hit@k)\n")

    # kiểm tra đáp án: mỗi câu phải có ít nhất 1 chunk chứa đáp án
    for q in questions:
        n_ok = sum(1 for c in chunks if norm(q["needle"]) in norm(c.raw_text))
        if n_ok == 0:
            print(f"  ! câu {q['id']}: không chunk nào chứa đáp án {q['needle']!r} (chunk/clean đã đổi?)")

    variants = [TokenizerOptions(*flags) for flags in itertools.product([False, True], repeat=4)]
    results = []
    for opts in variants:
        for k1, b in itertools.product(K1_GRID, B_GRID):
            ranks = evaluate(chunks, questions, k1, b, opts)
            results.append({"opts": opts, "k1": k1, "b": b, "ranks": ranks, **metrics(ranks)})

    base_ranks = evaluate(chunks, questions, BASELINE[0], BASELINE[1], BASELINE[2])
    base = metrics(base_ranks)
    print(f"Cấu hình hiện tại (k1=1.5, b=0.75, legacy): MRR={base['mrr']:.3f}  "
          f"hit@1={base['h1']:.2f}  hit@3={base['h3']:.2f}  hit@5={base['h5']:.2f}\n")

    results.sort(key=lambda r: (-r["mrr"], -r["h1"], abs(r["k1"] - 1.5) + abs(r["b"] - 0.75)))
    print("Top 10 cấu hình:")
    print(f"  {'tokenizer':44} {'k1':>4} {'b':>5}  {'MRR':>5} {'h@1':>5} {'h@3':>5} {'h@5':>5}")
    for r in results[:10]:
        print(f"  {fmt_opts(r['opts']):44} {r['k1']:4} {r['b']:5}  {r['mrr']:5.3f} {r['h1']:5.2f} {r['h3']:5.2f} {r['h5']:5.2f}")

    print("\nMRR trung bình theo từng lựa chọn tokenizer (bền vững hơn một đỉnh đơn lẻ):")
    for name in ("stem", "split_hyphen", "numbers", "extra_stopwords"):
        on = [r["mrr"] for r in results if getattr(r["opts"], name)]
        off = [r["mrr"] for r in results if not getattr(r["opts"], name)]
        print(f"  {name:16} bật: {sum(on) / len(on):.3f}   tắt: {sum(off) / len(off):.3f}")

    best = results[0]
    print(f"\nMRR theo (k1 × b) với tokenizer tốt nhất [{fmt_opts(best['opts'])}]:")
    print("        " + "".join(f"b={b:<6}" for b in B_GRID))
    for k1 in K1_GRID:
        row = [r["mrr"] for b in B_GRID for r in results if r["opts"] == best["opts"] and r["k1"] == k1 and r["b"] == b]
        print(f"  k1={k1:<4}" + "".join(f"{v:<8.3f}" for v in row))

    print("\nCâu thay đổi hạng (hiện tại -> tốt nhất):")
    changed = False
    for q, r0, r1 in zip(questions, base_ranks, best["ranks"]):
        if r0 != r1:
            changed = True
            print(f"  câu {q['id']:>2} [{q['type']}] {r0 or '-'} -> {r1 or '-'}   {q['question']}")
    if not changed:
        print("  (không có)")
    miss = [q for q, r in zip(questions, best["ranks"]) if r is None]
    if miss:
        print(f"\nVẫn không có trong top {CUTOFF} ở cấu hình tốt nhất:")
        for q in miss:
            print(f"  câu {q['id']:>2} [{q['type']}] {q['question']}")


if __name__ == "__main__":
    main()