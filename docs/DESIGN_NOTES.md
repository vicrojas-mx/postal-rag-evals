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

## Evals

### v1: retrieval eval (free, deterministic)
- 27 human-verified questions (direct / paraphrase / disambiguation × en / es / spanglish), with the expected section checked against the PDF by hand.
- Metrics: hit@4, recall@4, rank, MRR. **Family rule:** an expected parent section accepts any of its child chunks (title-only parents aren't indexed), in one direction only.
- Baseline: hit@4 1.00, recall@4 1.00, **MRR 0.89** (paraphrase 0.77 is the weakest). hit@4 is saturated, so MRR is the discriminating metric.
- **Grader bug found and fixed:** a reversed family rule under-reported hit@4 as 0.88. The unit test had been written to match the buggy code. Tests come from the spec, not from the implementation, and every grader has negative test cases.

### v2: answer eval (Claude Opus 5.5 answers, Claude Sonnet 5.5 judge)
- 32 cases: the 27 above + 5 out-of-scope questions with no hook in the handbook. Gray-zone and false-premise questions are saved for a red-teaming suite.
- Metrics: `cites_section` (programmatic), `abstains_correctly` (programmatic), `same_language` (stopword heuristic), `faithful` (LLM judge with a structured-output schema: faithful / unsupported_claims / reason).
- Design choices: `None` means "doesn't apply" and is excluded from averages (no citation is expected for out-of-scope questions; no language check for "I don't know." or answers under 8 words). A **partial** "I don't know" on an answerable question counts as honesty, not failure. Infra errors go to a separate errors file, never scored as zeros.
- Judge smoke test before trusting it: empty answer → faithful, "I don't know." → faithful (no claims), confident made-up answer → unfaithful with each fabricated claim listed.
- Pilot of 5 cases measured **$0.10** before the full run. Full run: 32 cases, **$0.61**, about 3 minutes, mean latency 4.1 s, 0 errors.
- First results: cites 27/27 · abstains 30/32 · language 21/28 · faithful 19/27.

### What the answer eval revealed
- **Language grader bug:** all 7 language failures were English answers to English questions. Technical jargon and markdown push the English stopword ratio under the fixed 0.25 threshold. Planned fix: compare the Spanish vs. English ratios instead of using fixed thresholds.
- **Conflicting rules in my own system prompt:** "answer exactly 'I don't know.'" vs. "answer in the language of the question". Claude sometimes answered "No lo sé." To fix: one explicit rule.
- **An out-of-scope question had a hook after all:** the taquiza / break-room question pulled 13-2.2 (no food on the sales counter). Writing truly hook-free out-of-scope cases is hard.
- **The answer eval caught what the retrieval eval hid:** for a question pointing at a parent section, the family rule counted a hit even though one child (14-6.1) wasn't retrieved. Claude honestly said "I don't know" for that part.
- **Relevance gating, calibrated from eval data:** top retrieval score for in-scope questions is ≥ 0.42; gibberish and obvious out-of-scope questions score 0.16–0.31. A ~0.35 threshold would stop them with zero false rejects, but postal-sounding out-of-scope questions (0.43) overlap, so the LLM stays the final gate.

### LLM judge calibration (human vs. judge)
- I hand-reviewed all 8 judge failures: the judge was right on 4 (real extrapolations, e.g. inventing who may cash a money order) and too strict on 4 (fair paraphrases or obvious inferences).
- Three prompt iterations, re-judging the same frozen answers each time: faithful 19 → 20 → 19 out of 27, with human agreement stuck at 4/8. Individual cases flipped between runs, so the judge has run-to-run variance, and some cases were ambiguous even to me as the human reviewer.
- Decision: stop iterating and report both numbers. **LLM-judge faithful ~19–20/27 (a strict lower bound) vs. human-calibrated ~23/27.**
- Next ideas: few-shot (synthetic) examples in the judge prompt, majority vote over several judge samples, a judge from a different model family, and a supported-claims ratio as a diagnostic next to the strict binary gate.
- Lessons: avoid contradictory instructions and ALL-CAPS in prompts; save every experiment to its own file (I overwrote round 2).

### Known limitations
- The handbook is the **August 2023 edition**; some policies may have changed since (flagged per case with a `stale_risk` tag).
- The stopword language check is unreliable on short answers and on jargon-heavy English.

## Testing strategy (test pyramid)
- `tests/unit`: fake inputs, no PDF, about 0.03 s. Covers `find_title`, `clean_text`, Unicode cleaning, end pages, and breadcrumbs (including the stack shrinking to a middle depth).
- `tests/integration`: real PDF, full pipeline, about 4 s. Covers the section count, Transmittal kept, front matter removed, each chunk starting with its title, no leaks into the next section, no header remnants (regex separates `"August 2023 5"` headers from prose), and breadcrumb shape.
- `tests/evals`: LLM answer quality (next).
- **Mutation testing:** I broke the code on purpose (e.g. disabled header cleaning) to confirm each test fails when it should. A green test that can't fail is worse than no test.
- Types are checked with `mypy`.

## Roadmap
- V1: classic RAG (embeddings + vector store + retriever + LLM) with an eval harness (DeepEval + pytest, GitHub Actions).
- V2: agentic RAG, where V1's retriever becomes the agent's tool. Same eval suite, comparing accuracy, latency, and cost. No assumption that agentic wins; the numbers decide.
