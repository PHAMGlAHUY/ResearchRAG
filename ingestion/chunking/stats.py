from ingestion.load_data import load_data
from ingestion.chunking.chunker import split_text_into_chunks, _get_tokenizer
from ingestion.chunking.context import contextualize

NAME = "2005.11401v4.md"

chunks = split_text_into_chunks(load_data(NAME), source=NAME)
tok = _get_tokenizer()

# đếm token của đúng chuỗi sẽ được embed (có tiền tố passage:)
tokens = sorted(len(tok.encode("passage: " + contextualize(c))) for c in chunks)
n = len(tokens)

print(f"Số chunk       : {n}")
print(f"Token min/med/max: {tokens[0]} / {tokens[n // 2]} / {tokens[-1]}")
print(f"Chunk > 512 token: {sum(t > 512 for t in tokens)}  (phải bằng 0)")
print(f"Chunk < 60 token : {sum(t < 60 for t in tokens)}   (chunk vụn)")

# thêm vào cuối stats.py
rows = sorted(((len(tok.encode("passage: " + contextualize(c))), c) for c in chunks), key=lambda x: -x[0])
for n_tok, c in rows[:3]:
    print(n_tok, c.metadata.get("Header 2") or c.metadata.get("Header 1"), repr(c.page_content[:100]))