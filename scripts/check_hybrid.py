import os

# Model đã tải sẵn: chạy offline, bỏ cảnh báo HF_TOKEN. Xóa dòng này nếu chưa tải model lần nào.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from qdrant_client.models import SparseVector

from core.load_settings import load_settings
from embedding.embed_texts import embed_query
from embedding.sparse_embedder import get_sparse_embedder
from retrieval.retriever import retrieve
from vectorstore.qdrant import get_qdrant_client, VECTOR_DB_COLLECTION

LIMIT = load_settings()['retrieval'].get('top_k', 10)     # cùng số kết quả với retrieve()
SHOW = 5

# (câu hỏi, chuỗi phải có trong chunk đúng; None = câu ngoài phạm vi bài báo)
CASES = [
    ("How many retrieved documents does RAG-Token use at test time?", "15 retrieved documents"),
    ("What is MIPS?", "Maximum Inner Product Search"),
    ("Which retriever does RAG use?", "is based on DPR"),
    ("What is qdrant?", None),
]


def norm(s: str) -> str:
    return " ".join(s.split())


def section(meta: dict) -> str:
    return " > ".join(meta[k] for k in ("Header 1", "Header 2", "Header 3") if meta.get(k)) or "?"


def rows_from_points(points):
    return [(p.score, p.payload, p.payload.get("text", "")) for p in points]


def rows_from_docs(docs):
    return [(d.score, d.metadata, d.text) for d in docs]


def rank_of(rows, needle):
    if needle is None:
        return None
    for i, (_, _, text) in enumerate(rows, 1):
        if needle in norm(text):
            return i
    return None


client = get_qdrant_client()
info = client.get_collection(VECTOR_DB_COLLECTION)
sp = get_sparse_embedder()

print("points:", info.points_count)
print("dense:", list(info.config.params.vectors), "| sparse:", list(info.config.params.sparse_vectors))
print("stats n_docs:", sp.n_docs, "| vocab:", len(sp.vocab))
assert sp.n_docs == info.points_count, "Thống kê BM25 lệch số điểm trong collection!"

summary = {"dense": [], "sparse": [], "hybrid": []}

for question, needle in CASES:
    print(f"\n=== {question}")
    print(f"    cần tìm: {needle!r}" if needle else "    (ngoài phạm vi: không có đáp án)")

    dense = rows_from_points(client.query_points(
        VECTOR_DB_COLLECTION, query=embed_query(question), using="dense",
        limit=LIMIT, with_payload=True).points)

    si, sv = sp.encode_query(question)
    sparse = rows_from_points(client.query_points(
        VECTOR_DB_COLLECTION, query=SparseVector(indices=si, values=sv), using="sparse",
        limit=LIMIT, with_payload=True).points) if si else []

    hybrid = rows_from_docs(retrieve(question))

    ranks = {}
    for name, rows in (("dense", dense), ("sparse", sparse), ("hybrid", hybrid)):
        ranks[name] = rank_of(rows, needle)
        if needle:
            summary[name].append(ranks[name])
        for score, meta, text in rows[:SHOW]:
            mark = "  <-- ĐÚNG" if needle and needle in norm(text) else ""
            print(f"  {name:6} {score:7.3f}  #{meta.get('chunk_index', '?'):<3} {section(meta)[:70]}{mark}")
        if not rows:
            print(f"  {name:6} (không có kết quả: câu hỏi không chứa từ nào trong vocab)")

    if needle:
        fmt = lambda r: f"#{r}" if r else f"ngoài top {LIMIT}"
        print("  -> hạng chunk đúng:", " | ".join(f"{k}: {fmt(v)}" for k, v in ranks.items()))

print("\n=== Tổng hợp (chỉ các câu có đáp án)")
n = len(summary["dense"])
for name, ranks in summary.items():
    cells = [f"top-{k}: {sum(1 for r in ranks if r and r <= k)}/{n}" for k in (1, 3, 5, LIMIT)]
    print(f"  {name:6} " + "  ".join(cells))