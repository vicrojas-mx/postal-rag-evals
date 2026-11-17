# Design Notes

Raw notes for the README. Each decision gives the reason behind it.

## Source document
- USPS Handbook PO-209, *Retail Operations Handbook* (August 2023), a public PDF of 136 pages.
- The printed labels run i–xiv (14 front-matter pages), then 1–122. PDF page index ≠ printed page number, so the metadata keeps `page_label` (what a person sees on the page).

## Ingestion is offline ETL
- RAG ingestion works like the nightly ETL into a data warehouse. The heavy lifting runs once, offline, so retrieval at query time stays fast.
- Pipeline: `PDF → outline → section boundaries → section text → cleanup → breadcrumbs → filter front matter → chunks`

## Custom PDF loader instead of `langchain-community`
- `langchain-community` was sunset (archived, no longer maintained), and no official standalone PyPDF loader package replaced it.
- I built a small loader on `pypdf` + `langchain-core` instead of depending on an abandoned package.

## Section-based chunking, not page-based
- Page boundaries are arbitrary because the printer decides them. One page can hold 6 unrelated sections (e.g. 1-4.1 through 1-4.6), and a section can span two pages.
- I use the PDF outline (bookmarks) to cut text **by section**, so each chunk carries one complete idea to the LLM.
- Long sections are sub-split (~1500 characters, 200 overlap). Sections whose content is only a title are skipped.
- Plan: build page-based chunking too, and let the evals decide which works better.

## Cleanup decisions
- **Whitespace normalization:** the PDF wraps long titles across lines (`"...Retail \nPersonnel"`), and the line breaks are mid-sentence, not paragraph breaks. The LLM writes its own formatting, and embeddings don't need it.
- **Headers/footers:** stripped per page **before** normalization, while line boundaries still exist. On normal pages the header is 2 lines; on chapter-first pages it's 1 line (the next line is the chapter title, which must survive). Markers live in one constant (`HEADER_MARKERS`).
- **Glued chapter numbers:** the PDF renders `"10Product Offerings"` with no space. `find_title()` tries the exact title first, then the glued variant. I kept the source text as-is (source fidelity) and made the matching tolerant.
- **Unicode:** characters in Unicode category C (control, format, private-use font glyphs such as `` bullets) are removed, except `\n`, `\r`, `\t`. One rule instead of hardcoding each character.
- **Blank pages** (`"This page intentionally left blank"`) are dropped.

## Front matter
- Dropped: cover, Contents (43K characters that mention every title and would "steal" retrieval spots), List of Exhibits.
- Kept: **Transmittal Letter**, because it answers "what changed in this edition / when is it effective?"
- Rule: keep sections with a numeric `page_label`, plus an allowlist (`KEEP_FRONT_MATTER`).
- Order matters: **compute boundaries with every neighbor present, then filter.** Filtering first would make the Transmittal swallow the Contents pages.

## Breadcrumbs
- Problem: section names repeat. "Ordering Supplies" appears 3 times (RSS equipment, Toshiba printer, Self-Service Kiosk), and "Cash Drawers" 3 times.
- Each chunk carries its family path, e.g. `7 Equipment and Supplies > 7-14 Self-Service Kiosk > 7-14.2 Ordering Supplies`.
- Built in one pass with a stack keyed by `depth` (child → parent, like parent pointers).
- The breadcrumb is prepended to `page_content`, so the parent context goes into the embedding too.

## Metadata is denormalized on purpose
- Every chunk repeats its section metadata (`title`, `breadcrumbs`, `page_label`, `depth`, `source`, `chunk_index`).
- Vector stores return chunks one by one and don't do joins. As with star schemas / OLAP cubes, it's cheaper to denormalize up front than to join at query time.
- Cost: about 350 chunks × ~200 bytes ≈ 70 KB. DRY applies to logic, not always to data.
- The embedding (from `page_content`) **finds** the chunk. The metadata **says where it came from** (citations, filtering, evals).

## Testing strategy (test pyramid)
- `tests/unit`: fake inputs, no PDF, about 0.03 s. Covers `find_title`, `clean_text`, Unicode cleaning, end pages, and breadcrumbs (including the stack shrinking to a middle depth).
- `tests/integration`: real PDF, full pipeline, about 4 s. Covers the section count, Transmittal kept, front matter removed, each chunk starting with its title, no leaks into the next section, no header remnants (regex separates `"August 2023 5"` headers from prose), and breadcrumb shape.
- `tests/evals`: LLM answer quality (next).
- **Mutation testing:** I broke the code on purpose (e.g. disabled header cleaning) to confirm each test fails when it should. A green test that can't fail is worse than no test.
- Types are checked with `mypy`.

## Roadmap
- V1: classic RAG (embeddings + vector store + retriever + LLM) with an eval harness (DeepEval + pytest, GitHub Actions).
- V2: agentic RAG, where V1's retriever becomes the agent's tool. Same eval suite, comparing accuracy, latency, and cost. No assumption that agentic wins; the numbers decide.
