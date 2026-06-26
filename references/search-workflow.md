# Search Workflow — full step-by-step playbook

## 1. Interpret the user request

Extract:

- **topic** (core noun phrase + qualifiers)
- **date range** (e.g. "last 5 years" → from-year = current − 5)
- **document type** preference (review, original, systematic review, preprints OK?)
- **ranking mode** — `newest` / `relevance` / `influence` / `systematic-review`
- **inclusion / exclusion rules** (animal vs. human, specific country, language)
- **language of the final answer** (default: match the user's input language; in this project usually Bulgarian)
- **depth** — compact list vs. full literature review with narrative

If the request is in **Bulgarian**, preserve it verbatim, then normalize the *search intent* (not the surface phrasing) into English scientific terms.

## 2. Normalize and expand the query

Build:

- one **English core query** (3–7 words, the most specific phrase that still has recall)
- a small **synonym set** (acronyms ↔ full forms, near-synonyms, method names)
- topic-specific **keyword clusters** (mechanism, materials, outcome, application)
- optional **exclusion terms** (editorial, conference abstract, news, book review, retracted)

Use **conservative expansion** by default. Switch to broader exploratory expansion (`--mode exploratory`) only when the user asks for breadth or the first pass returns too few hits.

The built-in `query_expand.py` covers hydrogen/electrolysis/materials BG→EN mapping. For other domains, do the translation in the conversation and pass it explicitly via `--query "<english>"` plus optional `--keyword "<term>"` hints.

## 3. Multi-pass retrieval

### Pass 1 — broad discovery

OpenAlex + Crossref + Semantic Scholar with the **core query**. Limit per source: 25 by default, 50 for thorough reviews.

### Pass 2 — domain retrieval (conditional)

| Topic touches | Add sources |
|---|---|
| biology / medicine / pharmacology / public health | PubMed + Europe PMC + (bioRxiv/medRxiv via EPMC `SRC:PPR`) |
| chemistry / materials / electrochemistry | Europe PMC + chemRxiv (via EPMC) + DOAJ |
| physics / math / astronomy / quant-* / CS / ML / stats | arXiv |
| computer science | arXiv + DBLP |
| dataset / software discovery | DataCite + OpenAIRE |
| general OA verification | DOAJ |

### Pass 3 — access + verification enrichment

For the **merged** record set:

- Unpaywall — DOI lookup for OA URL and license.
- CORE (if `CORE_API_KEY` is set) — for repository copies.
- Retraction check — Crossref relation + OpenAlex `is_retracted`.

## 4. Validation

For each record:

- DOI matches `^10\.\d{4,9}/[-._;()/:a-z0-9]+$`.
- PMID is all-digits.
- Title is non-empty and ≥ 6 chars.
- `publication_date` parses to a year.
- Venue is non-empty (warn if empty for a non-preprint).

Records that fail validation but have a real DOI go through Crossref re-fetch to repair metadata.

## 5. Deduplication

Deduplicate in this order:

1. Normalized DOI match.
2. PMID match.
3. (fuzzy normalized title ≥ 0.92) AND year match AND (venue match OR ISSN match).
4. Normalized title + first author + year fallback.

Keep a `source_databases` list and a `source_ids` dict for every merged record. The merged record inherits the most complete value per field (longest non-empty title, earliest non-empty year that matches the canonical year, etc.).

## 6. Ranking

Apply the rubric in [quality-rubric.md](quality-rubric.md). For each record compute:

- `relevance` (0–3) — term-hit count in title + abstract, weighted by query salience
- `evidence_type` (0–3) — systematic review > review > original > unclear > non-peer-reviewed
- `metadata_confidence` (0–2) — DOI + title + year + venue presence
- `influence` (0–2) — combination of cited_by_count, **influential_citations** (Semantic Scholar), venue tier
- `recency` (0–2) — within the user's preferred window

Apply the **retraction penalty** (`-5` total score) if `is_retracted == true`.

Sort:

- `newest` — `publication_date desc`, then relevance, then metadata
- `relevance` — relevance → evidence → metadata → recency → influence
- `influence` — evidence → influence → relevance → metadata → recency
- `systematic-review` — filter to review/SR/MA article types first, then sort by influence

## 7. Reporting

Produce, in the user's language:

1. Summary table (review mode) or compact table (newest mode).
2. Search audit trail (databases, query forms, hits, dedup count, access limits).
3. Key trends — 3–5 paragraphs.
4. Top 3 influential papers with reasoning.
5. Open questions / gaps.
6. Recommended first reading (3 papers).
7. Any retraction warnings.
8. Optional exports if user asked: BibTeX, RIS, CSV.

Always note which sources were unreachable or returned 0 results — those are non-trivial signals about the topic's indexing.
