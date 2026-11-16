from langchain_core.documents import Document

from ingestion.chunking.chunker import preprocess, postprocess
from ingestion.chunking.cleaner import (
    clean_markdown, normalize_headings, remove_sections, simplify_mermaid,
)
from ingestion.chunking.context import section_path
from ingestion.chunking.tables import inline_tables


# ── remove_sections ──
def test_api_reference_is_kept():
    assert "GET /x" in remove_sections("# Doc\n## API Reference\nGET /x\n")

def test_references_to_prior_work_is_kept():
    assert "body" in remove_sections("# P\n## References to prior work\nbody\n")

def test_references_with_subsections_removed_appendix_kept():
    out = remove_sections("# P\n## References\n### Journals\n[1] A\n## Appendix\nok\n")
    assert "[1] A" not in out and "ok" in out

def test_numbered_vietnamese_reference_removed():
    out = remove_sections("# T\nnội dung\n## 6. Tài liệu tham khảo\n[1] x\n")
    assert "[1] x" not in out and "nội dung" in out

def test_hash_comment_in_code_does_not_end_cut():
    src = "# T\n## References\n```bash\n# note\n```\n[1] x\n## Appendix\nok\n"
    out = remove_sections(src)
    assert "[1] x" not in out and "ok" in out


# ── normalize_headings ──
def test_code_comment_is_not_a_heading():
    src = "# T\n```bash\n# cài *args\n```\n"
    assert "# cài *args" in normalize_headings(src)

def test_stars_removed_from_heading():
    assert normalize_headings("## **Intro**\n") == "## Intro"

def test_flattened_numbered_headings_get_levels():
    out = normalize_headings("## 1 Intro\n## 2 Methods\n## 2.1 Setup\n")
    assert out.splitlines() == ["# 1 Intro", "# 2 Methods", "## 2.1 Setup"]

def test_existing_structure_is_trusted():
    out = normalize_headings("# Guide\n## 1. Install\n### 1.1 Pip\n## 10 tips\n")
    assert "## 1. Install" in out and "## 10 tips" in out


# ── clean_markdown ──
def test_hyphen_join_is_configurable():
    assert "international" in clean_markdown("inter-\nnational")
    assert "end-\nto-end" in clean_markdown("end-\nto-end", join_hyphen=False)

def test_code_block_untouched_by_clean():
    src = "text\n```\nline   \n\n\n\nx\n```\n"
    assert "line   \n\n\n\nx" in clean_markdown(src)


# ── mermaid ──
def test_mermaid_labels_extracted():
    src = '```mermaid\ngraph TD\nA["Retriever"] --> B[Truy xuất]\n```\n'
    out = simplify_mermaid(src)
    assert "Retriever" in out and "Truy xuất" in out

def test_mermaid_without_labels_is_kept():
    src = "```mermaid\ngraph TD\nA-->B\n```\n"
    assert "mermaid" in simplify_mermaid(src)


# ── tables ──
def test_table_with_attributes_and_hash_column():
    out = inline_tables("<table border='1'><tr><th>#</th><th>A</th></tr>"
                        "<tr><td>1</td><td>x</td></tr></table>")
    assert "<table" not in out
    assert not any(l.startswith("#") for l in out.splitlines())

def test_table_numbers_survive_preprocess():
    assert "12" in preprocess("<table><tr><td>\n12\n</td><td>A</td></tr></table>", {})


# ── context / postprocess ──
def test_section_path_supports_deep_levels():
    d = Document(page_content="x", metadata={"Header 1": "A", "Header 4": "**D**"})
    assert section_path(d) == "A > D"

def test_short_chunk_is_merged_not_dropped():
    a = Document(page_content="x" * 100, metadata={"Header 1": "A"})
    b = Document(page_content="Định nghĩa: X", metadata={"Header 1": "A"})
    out = postprocess([a, b], "t.md", {"min_chunk_size": 50})
    assert len(out) == 1 and "Định nghĩa" in out[0].page_content