---
name: search-science-literature
description: Use when Codex must search, validate, rank, or synthesize scientific literature using open scholarly APIs and optional credentialed Web of Science Starter API. Trigger for literature reviews, state of the art, related work, newest papers, DOI/PMID/author/source-title checks, citation-aware reading lists, systematic-review starter sets, open-access discovery, "литературен преглед", "научни статии", and Web of Science metadata/times-cited validation. Accepts Bulgarian or English and must not invent papers, DOIs, venues, or metrics.
---

# Search Science Literature

## Overview

Find and organize trustworthy scientific literature **without hallucinating** papers, DOIs, venues, or metrics.
Prefer open scholarly APIs first. Use credentialed sources such as Web of Science Starter only when explicitly requested or enabled by credentials and quota. Keep the workflow auditable and state access or metadata limits explicitly.

The skill is **deterministic**: Python scripts in `scripts/` handle every retrieval, normalization, deduplication, and ranking step. The model's job is orchestration, query design, gap analysis, and narrative synthesis — not invention.

---

## Workflow (1-pass overview)

1. **Parse** the user request — topic, date range, doc type, ranking mode, output language, depth (compact list vs. full review).
2. **Normalize & expand** the topic into English scientific search terms (see [references/query-templates.md](references/query-templates.md)). Bulgarian input is translated, never paraphrased silently.
3. **Multi-source search** — fan out to the relevant Tier-1 and Tier-2 APIs in parallel (see [references/source-priority.md](references/source-priority.md)).
4. **Validate identifiers** — DOI regex + Crossref existence + PMID digit-check.
5. **Deduplicate & merge** — DOI → PMID → fuzzy(title)+year+venue, with `source_databases` aggregation.
6. **Rank** by intent: `newest`, `relevance`, `influence`, or `systematic-review`.
7. **Report** with a structured table, search audit trail, key trends, top influential papers, gaps, recommended first reads, and optional BibTeX/RIS/CSV exports.

Full step-by-step playbook: [references/search-workflow.md](references/search-workflow.md).

---

## Query Handling

Accept user requests in Bulgarian or English.
When the user writes in Bulgarian, **translate the scientific intent into English** before searching — almost all scholarly metadata is indexed in English. Keep the original BG query visible in the final audit trail and show the normalized English query plus expanded keywords.

Use **controlled expansion**, not uncontrolled paraphrasing:
- Start from the user's exact topic.
- Add domain synonyms, abbreviations, method names, and outcome terms.
- Add adjacent terms only when they materially improve recall.
- If the user asks for narrow retrieval, keep expansion conservative (`--mode strict`).

For topics outside the built-in BG→EN dictionary (hydrogen/electrolysis/materials), produce the translation yourself in the conversation and pass it as `--query "<english>"` plus `--keyword` hints to the script. The script logs both the original and the normalized form.

Read [references/query-templates.md](references/query-templates.md) before constructing search strings.
Use [scripts/query_expand.py](scripts/query_expand.py) for repeatable expansion.

---

## Source Strategy

Read [references/source-priority.md](references/source-priority.md) first.

### Tier 1 — broad, citation-aware discovery (always)

- **OpenAlex** — broad discovery, date sorting, source metadata, cited-by counts, concept tagging. Abstracts reconstructed from `abstract_inverted_index`.
- **Crossref** — DOI validation, metadata normalization, journal/publisher records.
- **Semantic Scholar** — citation graph, **influential citation count**, **TLDR** snippets, paper embeddings (re-ranking signal). [NEW vs. v1]

### Tier 2 — domain-specific (added on topic match)

- **PubMed** — biomedical, life sciences, public health, pharmacology, clinical.
- **Europe PMC** — life sciences + chemistry + materials; full-text links; **biorXiv/medrXiv/chemrXiv preprints indexed**.
- **arXiv** — physics, math, CS, statistics, quantitative biology, economics preprints. [NEW]
- **DBLP** — computer science conference and journal records. [NEW]
- **bioRxiv / medRxiv / chemRxiv** — direct preprint queries via Europe PMC `SRC:PPR` filter. [NEW]

### Tier 3 — open-access + verification enrichment

- **DOAJ** — open-access journal/article verification, license clarity. [NEW]
- **CORE** — repository and OA copies discovery (needs `CORE_API_KEY`).
- **OpenAIRE** — additional open research graph discovery (datasets + publications).
- **Unpaywall** — OA location lookup by DOI.
- **DataCite** — datasets and software linked to publications. [NEW]
- **Retraction check** — query Crossref for retraction/correction relations + OpenAlex `is_retracted`. [NEW]

### Tier 4 — paywalled (not fetched, declared if asked)

Web of Science Starter API is supported as an optional credentialed source via `--include-wos-starter` and `WOS_STARTER_API_KEY`. Keep it off by default because free trial quota is small.

Scopus, ScienceDirect, IEEE Xplore, and other entitlement-based sources are not queried unless a script and credentials are available. If the user requests one and the environment cannot access it, say so in one sentence and continue with the strongest open evidence.

**Never** scrape Google Scholar or other unofficial paths.

---

## Search Modes

Ranking intents:

- `newest` — most recent relevant papers first (publication_date desc).
- `relevance` — best topical matches first (default for literature reviews).
- `influence` — favor reviews, high citation signals, venue credibility, topical centrality.
- `systematic-review` — return only review/meta-analysis/systematic-review article types, sorted by influence.

For newest-first discovery, default to the **compact record** format (see [references/output-template.md](references/output-template.md)).

---

## Validation Rules

- Never invent papers, DOIs, PMIDs, journals, impact factors, or citation counts.
- Prefer publisher DOI landing pages, PubMed, Europe PMC, Crossref, OpenAlex over weaker metadata pages (see [references/api-notes.md](references/api-notes.md)).
- Deduplicate by DOI → PMID → fuzzy-title (≥ 0.92 similarity) + year + venue.
- If a field cannot be verified reliably, write `недостъпно` (Bulgarian output) or `not available` (English output).
- Treat preprints as a separate "Non-peer-reviewed context" section unless the user explicitly asks to include them in the main set.
- Run retraction check (`scripts/check_retractions.py`) before claiming a paper is current best evidence. Flag any retracted/corrected papers in the output.

Read [references/peer-review-policy.md](references/peer-review-policy.md) and [references/metric-policy.md](references/metric-policy.md) before reporting peer-review status or metrics.

---

## Preferred Scripts

Preferred entry point:

- [`scripts/search_orchestrator.py`](scripts/search_orchestrator.py) — runs the full pipeline (expand → multi-source search → dedup → rank → output JSON).

Supporting tools:

- Query handling: [`scripts/query_expand.py`](scripts/query_expand.py)
- Tier-1 search: [`scripts/search_openalex.py`](scripts/search_openalex.py), [`scripts/search_crossref.py`](scripts/search_crossref.py), [`scripts/search_semantic_scholar.py`](scripts/search_semantic_scholar.py)
- Domain search: [`scripts/search_pubmed.py`](scripts/search_pubmed.py), [`scripts/search_europepmc.py`](scripts/search_europepmc.py), [`scripts/search_arxiv.py`](scripts/search_arxiv.py), [`scripts/search_dblp.py`](scripts/search_dblp.py), [`scripts/search_biorxiv.py`](scripts/search_biorxiv.py)
- OA + verification: [`scripts/search_doaj.py`](scripts/search_doaj.py), [`scripts/search_core.py`](scripts/search_core.py), [`scripts/search_openaire.py`](scripts/search_openaire.py), [`scripts/search_datacite.py`](scripts/search_datacite.py), [`scripts/enrich_unpaywall.py`](scripts/enrich_unpaywall.py), [`scripts/check_retractions.py`](scripts/check_retractions.py)
- Credentialed sources: [`scripts/search_wos_starter.py`](scripts/search_wos_starter.py) for Web of Science Starter API when `WOS_STARTER_API_KEY` is set
- Post-processing: [`scripts/validate_identifiers.py`](scripts/validate_identifiers.py), [`scripts/merge_dedup_rank.py`](scripts/merge_dedup_rank.py), [`scripts/build_review_table.py`](scripts/build_review_table.py)
- Exports: [`scripts/export_bibtex.py`](scripts/export_bibtex.py), [`scripts/export_ris.py`](scripts/export_ris.py), [`scripts/export_csv.py`](scripts/export_csv.py)

Scripts are retrieval and normalization aids. They do not replace scientific judgment.

---

## Typical Invocations

```bash
# Full review pipeline (default)
python scripts/search_orchestrator.py \
    --query "PEM electrolysis efficiency" \
    --from-year 2022 --limit 25 --sort relevance \
    --include-arxiv --include-semantic-scholar --include-doaj \
    --output /tmp/lit_search.json

# Newest-first compact list, BG input
python scripts/search_orchestrator.py \
    --query "статии за солидно-оксидни горивни клетки" \
    --sort newest --limit 30 --output /tmp/sofc_new.json

# Systematic-review starter set
python scripts/search_orchestrator.py \
    --query "lithium-ion battery thermal runaway" \
    --sort systematic-review --from-year 2020 --output /tmp/li_sr.json

# Include Web of Science Starter API when credentials and quota are available
python scripts/search_orchestrator.py \
    --query "PEM electrolysis efficiency" \
    --from-year 2022 --limit 25 --sort relevance \
    --include-wos-starter --output /tmp/lit_search_wos.json

# DOI check through Web of Science Starter API
python scripts/search_wos_starter.py \
    --doi "10.1038/nphys1170" --pretty

# Export final reading list
python scripts/export_bibtex.py /tmp/lit_search.json --output reading.bib
python scripts/build_review_table.py /tmp/lit_search.json --mode review > review.md
```

---

## Final Output

- Use the structure in [references/output-template.md](references/output-template.md).
- Always include a short **search audit trail** (databases hit, initial hits, dedup count, access limits).
- Show both the original BG query and the normalized EN query when input was in Bulgarian.
- For `newest` intent, sort globally by `publication_date` after merging records from all sources.
- Flag retracted papers with `⚠ RETRACTED` and link the retraction notice DOI.

---

## Environment Variables (optional but recommended)

| Variable | Purpose | Effect when missing |
|---|---|---|
| `OPENALEX_MAILTO` | polite pool access | rate-limited shared pool |
| `CROSSREF_MAILTO` | polite pool access | rate-limited shared pool |
| `UNPAYWALL_EMAIL` | required header | `anonymous@example.invalid` fallback |
| `CORE_API_KEY` | CORE v3 API | CORE skipped with a one-line note |
| `SEMANTIC_SCHOLAR_API_KEY` | higher rate limits | shared free tier |
| `NCBI_API_KEY` | higher PubMed rate limits | 3 req/sec shared limit |
| `WOS_STARTER_API_KEY` | Web of Science Starter API | WoS Starter skipped unless explicitly called |
| `WOS_STARTER_API_VERSION` | `v1` or `v2` endpoint | `v1` |
| `WOS_STARTER_CACHE_DIR` | cache path for WoS Starter responses | user cache directory |

Set them in `.env` (already gitignored by the project CLAUDE.md convention).

---

## References To Load On Demand

- [references/search-workflow.md](references/search-workflow.md) — full step playbook
- [references/source-priority.md](references/source-priority.md) — tier list + metadata conflict order
- [references/query-templates.md](references/query-templates.md) — 12+ domain templates
- [references/quality-rubric.md](references/quality-rubric.md) — scoring weights
- [references/output-template.md](references/output-template.md) — table + audit + narrative shape
- [references/api-notes.md](references/api-notes.md) — endpoint quirks, rate limits, gotchas
- [references/field-mapping.md](references/field-mapping.md) — canonical schema vs. each API
- [references/peer-review-policy.md](references/peer-review-policy.md) — what counts as the main corpus
- [references/metric-policy.md](references/metric-policy.md) — when to (not) report impact factor / citation counts
