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

## Embeddings: local model behind an interface
- Anthropic doesn't offer an embeddings model; its docs point to Voyage AI. For V1 I run **`voyageai/voyage-4-nano`** locally (open-weight, Apache 2.0, about 0.3B params) via `sentence-transformers`, with `truncate_dim=1024`.
- Why local first: free, offline, no extra vendor account, and CI can run it without secrets. Paid options (Voyage API `voyage-4`, Bedrock Titan) are the next step and get **compared through the evals**, not chosen on faith.
- `LocalEmbedder` implements LangChain's `Embeddings` interface (`embed_documents` / `embed_query`), so swapping providers or plugging into any vector store is a one-line change.
- **Asymmetric retrieval:** `encode_query` and `encode_document` add different instruction prefixes, so a question lands near its answer, not near other questions.
- Only `page_content` is embedded. Metadata travels alongside for citations. That's why the breadcrumb is inside `page_content`: it brings the parent context into the vector.
- **Accepted risk:** `trust_remote_code=True` runs code from the model's Hugging Face repo locally. Acceptable for a local portfolio project; for production, pin the model revision and review the code.

### Sanity check: semantic, not keyword
- Query `"how do I get more paper for the kiosk?"` against three chunks: 7-14.2 Ordering Supplies **0.230** vs Name Tags 0.124 / 0.131. It won, but "kiosk" appears in both the query and the chunk, so lexical overlap helped.
- Harder test, a paraphrase with **zero key-word overlap**: `"where do I request more rolls for the self-serve machine?"` (no "kiosk", "paper", or "supplies"). 7-14.2 still ranked first, and the gap widened: **0.242** vs 0.103 / 0.104. The model mapped "self-serve machine" ≈ "kiosk" and "rolls" ≈ "consumables/supplies".
- **Spanglish (code-switched) query:** 7-14.2 still ranked first at **0.226** vs 0.098 / 0.101, so the multilingual model bridged Spanish/Spanglish wording to an English chunk. *¿dónde pido más rollos pa' la máquina self-serve, carnal?* This matters because many postal workers speak Spanish, so multilingual queries will get their own eval set.
- Contrast: my earlier hand-built keyword RAG ([rag-by-hand](https://github.com/vicrojas-mx/rag-by-hand)) missed synonyms like "phone" and "money". Embeddings fix that class of failure.
- Similarity scores sit close together, so ranking and relative gap matter more than the absolute value.

## Testing strategy (test pyramid)
- `tests/unit`: fake inputs, no PDF, about 0.03 s. Covers `find_title`, `clean_text`, Unicode cleaning, end pages, and breadcrumbs (including the stack shrinking to a middle depth).
- `tests/integration`: real PDF, full pipeline, about 4 s. Covers the section count, Transmittal kept, front matter removed, each chunk starting with its title, no leaks into the next section, no header remnants (regex separates `"August 2023 5"` headers from prose), and breadcrumb shape.
- `tests/evals`: LLM answer quality (next).
- **Mutation testing:** I broke the code on purpose (e.g. disabled header cleaning) to confirm each test fails when it should. A green test that can't fail is worse than no test.
- Types are checked with `mypy`.

## Roadmap
- V1: classic RAG (embeddings + vector store + retriever + LLM) with an eval harness (DeepEval + pytest, GitHub Actions).
- V2: agentic RAG, where V1's retriever becomes the agent's tool. Same eval suite, comparing accuracy, latency, and cost. No assumption that agentic wins; the numbers decide.
