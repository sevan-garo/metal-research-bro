# 0004 — Docling for layout-aware PDF parsing

## Context

Metallurgy papers lean heavily on tables (alloy compositions, mechanical
properties) and figures (phase diagrams, micrographs). Naive text extraction
(e.g. `pdfplumber` reading text in raster order, or PyPDF2) flattens tables
into unstructured runs of numbers and loses the row/column relationships that
give the data meaning. Since the RAG layer only sees the extracted text, a
broken table becomes an unrecoverable loss of information at query time.

## Decision

Use Docling to parse PDFs. It preserves document layout — headings, tables,
figure captions — and produces a structured document tree instead of a flat
text blob.

## Consequences

- `ingestion/parse.py` walks `docling`'s item tree and tags each text block
  with its nearest preceding section heading and page number
  (`ParsedBlock.section`, `ParsedBlock.page`), which then drives both the
  section-based chunking (ADR 0006) and the citation format `[Title, p.X]`.
  Neither would be possible from a flat-text extractor.
- Docling includes an OCR fallback (RapidOCR) for scanned pages, useful for
  older papers that are image-only PDFs — not yet exercised by the POC test
  corpus (all born-digital), but available without extra integration work.
- Cost: Docling pulls in `torch` and OCR models, making it the heaviest
  dependency in the stack (~150MB+ of models cached under `.venv`). Accepted
  given the alternative is silently corrupting exactly the data (tables) the
  spec flags as most important to get right.
- Figures are extracted as images but not analyzed in the POC — reading phase
  diagrams/micrographs is deferred to a V2 multimodal pass (see CLAUDE.md,
  "Metallurgy-specific points of attention").
