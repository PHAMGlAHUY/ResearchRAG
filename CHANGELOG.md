## [0.2.0] - 2026-11-16
### Fixed
- preserve document chunks during other document ingestion
- ensure `remove_section` is no mistakenly remove `## API Reference`
- numeric-only table cells are no longer misclassified as page numbers
### Added
- `validator.py`: validate markdown before chunk and after splitting
- Metadata `chunk_id`, `section_path`, `n_tokens`, `start_index`
### Changed
- Empty docs raise `ValueError`; `dump_chunks` off as default
Further details: docs/reports/2026-11-16-chunking-refactor.md