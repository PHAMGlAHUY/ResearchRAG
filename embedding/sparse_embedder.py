import json
import logging
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from core.load_settings import load_settings

logger = logging.getLogger('embedding')

_BASE_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were "
    "will with we our can also not but if than then these those which who whom their there into "
    "such may more most other some any each both do does did been being".split()
)
_QUESTION_WORDS = frozenset("what how many much why when where whose".split())

_TOKEN_LEGACY = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_TOKEN_NUMBERS = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?(?:[-'][a-z0-9]+)*")   # giữ nguyên "44.5", "0.05"


@dataclass(frozen=True)
class TokenizerOptions:
    """Mặc định (tất cả False) = tokenizer cũ. Lưu cùng file thống kê để query và document luôn khớp."""
    stem: bool = False             # gộp dạng biến đổi: documents -> document, retrieved -> retriev
    split_hyphen: bool = False     # "rag-token" -> thêm "rag", "token" bên cạnh "rag-token"
    numbers: bool = False          # giữ số thập phân; bỏ đuôi sở hữu 's ("RAG's" -> "rag")
    extra_stopwords: bool = False  # bỏ từ để hỏi: what, how, many, much, why, when, where


def light_stem(word: str) -> str:
    """Stemmer tiếng Anh nhẹ, không cần thư viện. Chỉ cần nhất quán giữa document và query."""
    if len(word) < 4 or not word.isalpha():
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    for suf in ("ing", "ed", "ion", "er", "or"):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            word = word[:-len(suf)]
            if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "lsz":
                word = word[:-1]                      # running -> run
            break
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]                              # retrieve -> retriev
    return word


@lru_cache(maxsize=8192)
def _tokenize(text: str, opts: TokenizerOptions) -> tuple[str, ...]:
    stop = _BASE_STOPWORDS | _QUESTION_WORDS if opts.extra_stopwords else _BASE_STOPWORDS
    pattern = _TOKEN_NUMBERS if opts.numbers else _TOKEN_LEGACY
    out = []
    for tok in pattern.findall(text.lower()):
        if opts.numbers and tok.endswith("'s"):
            tok = tok[:-2]
        parts = [tok]
        if opts.split_hyphen and ("-" in tok or "'" in tok):
            parts += [p for p in re.split(r"[-']", tok) if p]
        for p in parts:
            if len(p) < 2 or p in stop:
                continue
            out.append(light_stem(p) if opts.stem else p)
    return tuple(out)


def tokenize(text: str, opts: TokenizerOptions | None = None) -> list[str]:
    return list(_tokenize(text, opts or TokenizerOptions()))


class SparseEmbedder:
    """BM25 dạng vector thưa: tích vô hướng (doc, query) = điểm BM25.

    - Document: trọng số = thành phần TF của BM25 (bão hòa theo k1, chuẩn hóa độ dài theo b).
    - Query:    trọng số = IDF của từng từ (tính từ document frequency lúc fit).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75, opts: TokenizerOptions | None = None):
        self.k1, self.b = k1, b
        self.opts = opts or TokenizerOptions()
        self.vocab: dict[str, int] = {}
        self.df: list[int] = []
        self.n_docs = 0
        self.avgdl = 0.0

    def fit(self, texts: list[str]) -> "SparseEmbedder":
        df: Counter = Counter()
        total_len = 0
        for text in texts:
            tokens = tokenize(text, self.opts)
            total_len += len(tokens)
            for term in set(tokens):
                df[term] += 1
        self.vocab = {term: i for i, term in enumerate(sorted(df))}
        self.df = [df[t] for t in self.vocab]
        self.n_docs = len(texts)
        self.avgdl = total_len / max(self.n_docs, 1)
        logger.info("Fitted sparse embedder: %d docs, %d terms, avgdl=%.1f, k1=%.2f, b=%.2f, %s",
                    self.n_docs, len(self.vocab), self.avgdl, self.k1, self.b, self.opts)
        return self

    def idf(self, idx: int) -> float:
        n, df = self.n_docs, self.df[idx]
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def encode_document(self, text: str) -> tuple[list[int], list[float]]:
        tokens = tokenize(text, self.opts)
        if not tokens:
            return [], []
        norm = self.k1 * (1.0 - self.b + self.b * len(tokens) / self.avgdl)
        indices, values = [], []
        for term, tf in Counter(tokens).items():
            idx = self.vocab.get(term)
            if idx is None:
                continue
            indices.append(idx)
            values.append(tf * (self.k1 + 1.0) / (tf + norm))
        return indices, values

    def encode_query(self, text: str) -> tuple[list[int], list[float]]:
        indices, values = [], []
        for term in set(tokenize(text, self.opts)):
            idx = self.vocab.get(term)
            if idx is None:
                continue
            indices.append(idx)
            values.append(self.idf(idx))
        return indices, values

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "k1": self.k1, "b": self.b, "tokenizer": asdict(self.opts),
            "n_docs": self.n_docs, "avgdl": self.avgdl, "vocab": self.vocab, "df": self.df,
        }), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SparseEmbedder":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        obj = cls(d["k1"], d["b"], TokenizerOptions(**d.get("tokenizer", {})))   # file cũ: tokenizer mặc định
        obj.vocab, obj.df, obj.n_docs, obj.avgdl = d["vocab"], d["df"], d["n_docs"], d["avgdl"]
        return obj


# ---------- cấu hình và bộ nạp dùng chung ----------
_cfg = load_settings()['embedding']
SPARSE_STATS_PATH = _cfg['sparse_stats_path']
BM25_K1 = _cfg.get('bm25_k1', 1.5)
BM25_B = _cfg.get('bm25_b', 0.75)
TOKENIZER_OPTIONS = TokenizerOptions(**_cfg.get('sparse_tokenizer', {}))

_instance: "SparseEmbedder | None" = None


def new_sparse_embedder() -> "SparseEmbedder":
    """Embedder chưa fit, dùng cấu hình trong settings (dùng ở bước nạp dữ liệu)."""
    return SparseEmbedder(BM25_K1, BM25_B, TOKENIZER_OPTIONS)


def get_sparse_embedder() -> "SparseEmbedder":
    """Nạp file thống kê BM25 một lần rồi giữ trong bộ nhớ (dùng ở retriever)."""
    global _instance
    if _instance is None:
        if not Path(SPARSE_STATS_PATH).exists():
            raise FileNotFoundError(f"Chưa có {SPARSE_STATS_PATH}. Hãy chạy ingestion pipeline trước.")
        _instance = SparseEmbedder.load(SPARSE_STATS_PATH)
    return _instance


def reset_sparse_embedder() -> None:
    global _instance
    _instance = None