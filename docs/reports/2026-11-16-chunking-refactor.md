# Report: Chunking Module Refactor

| | |
|---|---|
| Date | 2026-11-15 |
| Scope | `ingestion/chunking/*`, the `chunking` section of `settings` |
| Proposed version | `v0.2.0` |
| Status | Code written; **items marked ☐ in sections 7 and 8 are pending verification on real data** |

## 1. Summary

The original chunker worked well on one scientific paper (`2005.11401v4.md`) but was hard-wired to that document type and had several silent data-loss bugs when processing multiple documents. This change:

- fixes **27 bugs** across 6 files (section 3);
- splits `split_text_into_chunks` into small functions that can each be tested in isolation;
- adds a validator that checks markdown before chunking and chunks after splitting;
- adds metadata for Qdrant (`chunk_id`, `section_path`, `n_tokens`, `start_index`);
- moves document-type-specific rules into configuration.

The three most serious bugs (real data loss):

1. Every call deleted the chunks of all other documents.
2. `remove_sections` wrongly deleted valid sections such as `## API Reference`.
3. Table cells containing only a number were treated as page numbers and deleted.

## 2. Files in scope

| File | Type of change |
|---|---|
| `chunker.py` | Rewritten: split into functions, bug fixes, CLI added |
| `cleaner.py` | Rewritten: 5 functions fixed, `iter_lines` added |
| `tables.py` | Rewritten: regex, markdown table output, colspan |
| `context.py` | Rewritten: dead code removed, H1 to H6 supported |
| `stats.py` | Rewritten as a CLI |
| `test_cleaner.py` | Replaced with a pytest suite (17 cases) |
| `validator.py` | **New** |
| `test_validator.py` | **New** (21 cases) |

## 3. Bugs fixed

Severity: 🔴 data loss or swallowed errors, 🟠 poor chunk quality, 🟡 maintainability and accuracy.

### 3.1 `chunker.py`

| ID | Sev. | Bug | Impact | Fix |
|---|---|---|---|---|
| C1 | 🔴 | `glob("*.md")` followed by `unlink()` deleted every chunk in the output folder | Processing document B wiped the chunks of document A | One folder per document: `processed/<name>/` |
| C2 | 🔴 | `except Exception` followed by `return []` | A real failure looked like an empty document | `logger.exception` then `raise`; an empty document raises `ValueError` |
| C3 | 🔴 | `clean_markdown` ran before `inline_tables` | `<td>\n12\n</td>` matched the "page-number-only line" rule and the cell was deleted | Reordered: `inline_tables` runs first |
| C4 | 🟠 | `header_levels` defaulted to 2 with no warning | H3 to H6 silently disappeared from metadata | `header_levels: auto`, plus a warning when headings are deeper than configured |
| C5 | 🟠 | Second-tier split and filtering ran twice, with duplicate log lines | Wasted work; easy to fix one copy and forget the other | Runs once |
| C6 | 🟠 | Chunks under 50 characters were filtered out | Short but meaningful sections (definitions, notes) were lost | Merged into the previous chunk of the same parent section |
| C7 | 🟠 | Splitting measured in tokens, filtering in characters | Inconsistent units | A single `_length_fn(cfg)` shared by splitting and filtering |
| C8 | 🟠 | The default splitter is not markdown-aware | Could cut through code blocks, tables, and lists | `RecursiveCharacterTextSplitter.from_language(Language.MARKDOWN)` |
| C9 | 🟡 | `from_huggingface_tokenizer` counts special tokens | Each chunk over-counted by about 2 tokens | `encode(..., add_special_tokens=False)` |
| C10 | 🟡 | Dump filename used only `Header 2` or `Header 1` | Filename did not reflect the real section | Uses the deepest available heading (up to H6) |
| C11 | 🟡 | `__main__` hard-coded a filename; typo `"Saved chunkm"` | Usable only as a quick test | `argparse` CLI, typo fixed |
| C12 | 🟡 | `_get_tokenizer` relied on a module-level global | Hard to test, hard to swap models | `lru_cache`; still callable with no arguments |

### 3.2 `cleaner.py`

| ID | Sev. | Bug | Impact | Fix |
|---|---|---|---|---|
| L1 | 🔴 | `remove_sections` matched only the start of a heading, and `IGNORECASE` let the prefix group match lowercase text | `## API Reference` and `## References to prior work` were deleted | Regex matches the **entire** heading (`...\s*$`) |
| L2 | 🔴 | Skipping stopped at any heading, including `#` lines inside code | Subsections of References leaked into the data; later sections were cut incorrectly | Cut by heading level; code blocks are ignored |
| L3 | 🟠 | `normalize_headings` re-levelled headings by section number for every document | `## 10 Tips` dropped to H1 and breadcrumbs became wrong | `numbered_headings: auto` (applies only when numbered headings were flattened to a single level) |
| L4 | 🟠 | No distinction between prose and code blocks | `# install *args` inside code had its content altered | `iter_lines` marks code lines; functions skip them |
| L5 | 🟠 | Hyphen-newline joining `(\w)-\n(\w)` was always on | `end-\nto-end` became `endto-end` | `join_hyphen` is configurable |
| L6 | 🟠 | `simplify_mermaid` understood only `["..."]` and filtered with `[A-Za-z]` | Other diagram styles produced an empty string (the figure was lost); Vietnamese labels were dropped | Handles `A[x]`, `A(x)`, `A{x}` and edge labels; uses `[^\W\d_]`; **keeps the block unchanged** if no labels can be extracted |
| L7 | 🟡 | Numbered-heading depth capped at H3 | `2.1.3.1` was pulled down to H3 | Cap raised to H6 |
| L8 | 🟡 | Page-number regex used `\s*` | Could swallow blank lines | Uses `[ \t]*` |

### 3.3 `tables.py`

| ID | Sev. | Bug | Impact | Fix |
|---|---|---|---|---|
| T1 | 🟠 | Strict `<table>` regex | `<table border="1">` and `<TABLE>` stayed as raw HTML | `<table\b[^>]*>` with `IGNORECASE` |
| T2 | 🔴 | A table row starting with `#` (an index column) | Treated as an H1 heading by `MarkdownHeaderTextSplitter`, **silently** | Output a markdown table with a leading `\|` on every row |
| T3 | 🟡 | `<br>` inside a cell | Two words fused together | Replaced with a space |
| T4 | 🟡 | `colspan` ignored; rows with missing cells | Misaligned columns | Pad cells per `colspan` and to the widest row |
| T5 | 🟡 | `\|` character inside a cell | Broke the table structure | Escaped as `\|` |

### 3.4 `context.py`, `stats.py`, `test_cleaner.py`

| ID | Sev. | File | Bug | Fix |
|---|---|---|---|---|
| X1 | 🟡 | `context.py` | `section_path` defined twice (the first copy was dead code) | Removed the first copy |
| X2 | 🟠 | `context.py` | `HEADER_KEYS` fixed at 3 levels | Reads `Header N` keys dynamically from metadata |
| S1 | 🟡 | `stats.py` | Ran on import with a hard-coded filename | `argparse` CLI and a `main` function |
| S2 | 🟡 | `stats.py` | Calling the chunker overwrote chunk files | `dump_chunks` is off by default |
| S3 | 🟡 | `stats.py` | `IndexError` when there were no chunks | Exits with a clear message |
| S4 | 🟡 | `stats.py` | Tokenized each chunk twice | Once |
| R1 | 🟠 | `test_cleaner.py` | Imported a nonexistent `remove_tail_sections`; no assertions | Rewritten with pytest, 17 cases |

## 4. New features

| Feature | Details |
|---|---|
| Function structure | `split_text_into_chunks` orchestrates `preprocess`, `split_markdown`, `postprocess`, `dump_chunks`; the first two are pure and independently testable |
| Validator | `validator.py`: 16 markdown checks (error/warn/info), `validate_chunks` for post-split checks, and a directory-scanning CLI |
| Metadata | Adds `chunk_id` (deterministic SHA-1), `section_path`, `n_tokens` (or `n_chars`), `start_index` |
| Merge instead of drop | Chunks under `min_chunk_size` are merged into the previous chunk of the same parent section |
| Heading debug | `count_heading_levels` and `_build_headers(text, cfg)` log the heading levels found and warn when levels would be lost |
| CLI | `python chunker.py <file> [--dump]`, `python stats.py <file>`, `python -m ingestion.chunking.validator <path>` |

## 5. Behavior changes (read before upgrading)

| Change | Impact |
|---|---|
| An empty document raises `ValueError` instead of returning `[]` | Callers that relied on `[]` need a `try/except` |
| `dump_chunks` defaults to `false` | The chunk folder is no longer created automatically; use `--dump` or enable it in config |
| Chunk folder is per document | Path changes from `processed/*.md` to `processed/<name>/*.md` |
| HTML tables become markdown tables | More `\|` and `---` characters, so token counts rise |
| `Language.MARKDOWN` and `add_special_tokens=False` | Chunk boundaries and chunk counts differ from the previous version |
| `numbered_headings: auto` | May differ from old behavior for documents whose headings were not flattened |
| Stricter `remove_sections` matching | Sections that merely resemble "References" are no longer cut |

## 6. New configuration

```yaml
chunking:
  mode: token
  header_levels: auto        # auto | 1..6
  token_chunk_size: 400      # below 512 to leave room for "passage: " and the breadcrumb
  token_chunk_overlap: 50
  chunk_size: 1000           # used when mode: char
  chunk_overlap: 150
  min_chunk_size: 20         # same unit as mode
  dump_chunks: false
  numbered_headings: auto    # auto | true | false
  join_hyphen: true          # false for native markdown (not converted from PDF)
  drop_sections: []
```

## 7. Testing and measurements

### 7.1 Tests

| Suite | Cases | Status |
|---|---|---|
| `test_validator.py` | 21 | Run; 21 passed (using a minimal pytest-compatible runner, because pytest could not be installed without network access) |
| `test_cleaner.py` | 17 | ☐ Not yet run on the project machine |

16 `pytest -q` is fully green on the project machine.

### 7.2 Before and after (fill in real numbers)

Run `python stats.py 2005.11401v4.md` on the previous commit and on the new one, then fill in:

| Metric | Before | After |
|---|---|---|
| Number of chunks | x | 54 |
| Tokens min / median / max | x | 18/294/426 |
| Chunks > 512 tokens (must be 0) | x | 0 |
| Chunks < 60 tokens | x | 2 |

### 7.3 Verification checklist

1. 0 Validator scan of the real document folder shows no `error`
2. 0 Visual inspection of 5 to 10 dumped chunk files: no cuts through tables or code, breadcrumbs correct
3. 0 Two additional documents of different types tested (with H3 to H4 headings, with many tables)

## 8. Not done yet (technical debt)

| Item | Notes |
|---|---|
| `rowspan` and nested tables in `tables.py` | Rare in documents converted from PDF |
| Appendix has no end boundary in `normalize_headings` | Inspect visually when a document has sections after the appendix |
| Long tables lose their header row in later chunks | Header row needs to be repeated in each chunk |
| `setup_logging()` and `load_settings()` still run at import time | Left as is so other modules do not break; move into an init function once the chunker has its own tests |
| `chunk_id` is not a valid Qdrant point ID | Convert with `uuid.uuid5` when building the vector store |
| Validator thresholds for `REPEATED_LINES` and `NOISY` are heuristics | Tune after scanning real data |
| No dedicated chunker for source code | Needed if the goal is RAG over a code repository |

## 9. Risks and rollback

- Baseline before this change: commit `before refactor chunker` (☐ record the commit hash: `__________`).
- Roll back with `git revert <merge-commit>` or `git checkout <baseline> -- ingestion/chunking/`.
- Biggest risk: chunk counts and boundaries change, so if vectors already exist in Qdrant, **re-ingest everything** (drop the old collection, then upsert again).

## 10. How to reproduce

```bash
pytest -q
python stats.py 2005.11401v4.md
python -m ingestion.chunking.validator data/raw --details
python chunker.py 2005.11401v4.md --dump
```
