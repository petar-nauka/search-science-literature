# API Notes

Per-source quirks, rate limits, and "gotchas" the scripts already handle. Keep this updated whenever you discover new behavior.

## OpenAlex

- Strong default for broad discovery.
- Sort: `publication_date:desc`, `relevance_score:desc`, `cited_by_count:desc`.
- Filter syntax: `from_publication_date:YYYY-MM-DD,to_publication_date:YYYY-MM-DD,type:journal-article`.
- **Polite pool**: set `OPENALEX_MAILTO=<your email>` for higher rate limits.
- **Abstracts** come as `abstract_inverted_index` (token → list of positions). The skill's `search_openalex.py` reconstructs them into plain text.
- Free; no API key needed.
- Rate limit (anonymous): 10 req/sec, 100k/day.

## Crossref

- Use for **DOI validation** and metadata repair.
- Set `User-Agent: AppName/1.0 (mailto:you@example.com)` to enter the polite pool — `CROSSREF_MAILTO` triggers this.
- Some records lack abstracts; when present, abstracts are wrapped in **JATS XML** (`<jats:p>…</jats:p>`). The skill strips JATS markup.
- Retraction relations live in `relation.is-retracted-by` and `relation.is-corrected-by` arrays — used by `check_retractions.py`.
- Filter syntax: `filter=from-pub-date:YYYY-MM-DD,until-pub-date:YYYY-MM-DD,type:journal-article`.
- Rate limit: variable; polite pool gets higher quota.

## Semantic Scholar

- Citation graph + **influential citations** + **TLDR** + paper embeddings.
- Endpoint: `https://api.semanticscholar.org/graph/v1/paper/search`.
- `SEMANTIC_SCHOLAR_API_KEY` recommended; without a key you share a small free tier and hit 429s quickly.
- Specify the fields you want explicitly via `?fields=` (otherwise minimal response).
- Sort: not first-class; the script post-sorts by `influentialCitationCount` desc.
- Rate limit (anonymous): ~1 req/sec; with key: ~10 req/sec.

## PubMed

- Two-step: `esearch` for IDs → `esummary` (and optionally `efetch`) for metadata.
- Date filter: `(start:end[pdat])` appended to the term.
- Set `NCBI_API_KEY` for 10 req/sec (vs. 3 req/sec anonymous).
- Sort: `pub_date` (newest), `relevance`. PubMed's relevance is internal — opaque but generally good.

## Europe PMC

- Discovery, citations, references, OA links — strong complement to PubMed for life sciences + chemistry + materials.
- Preprint server access: filter `SRC:PPR` (bioRxiv, medRxiv, chemRxiv, arXiv mirrors).
- Sort: `DATE_DESC`; default sort is relevance.
- `fullTextUrlList.fullTextUrl[]` contains multiple OA URLs (publisher, EuropePMC, PMC) — the script picks the first non-empty, preferring `documentStyle=html`.
- Rate limit: be polite; no hard published cap.

## arXiv

- Atom XML API at `http://export.arxiv.org/api/query`.
- Search syntax: `search_query=all:"<terms>"` plus `sortBy=submittedDate&sortOrder=descending`.
- Records always have an arXiv ID (`<id>http://arxiv.org/abs/2401.12345v1</id>`); DOIs are filled in only after publication and appear in the `arxiv:doi` element when present.
- Treat every arXiv record as a **preprint** (not peer-reviewed) — keep them in a separate section unless the user asks otherwise.
- Rate limit: 1 req/3 seconds — script enforces a small delay.

## DBLP

- JSON API: `https://dblp.org/search/publ/api?q=<query>&format=json&h=<limit>`.
- Strong for computer science venues (conference and journal); poor for biomedical.
- DOIs and venue names may be partial — use Crossref to repair.

## bioRxiv / medRxiv / chemRxiv

- Primary path: query Europe PMC with `SRC:PPR` filter (combined index).
- Direct API: `https://api.biorxiv.org/details/biorxiv/<DOI>` for per-DOI lookup.
- All records are preprints — flag accordingly.

## DOAJ

- v3 JSON API: `https://doaj.org/api/v3/search/articles/<query>?pageSize=<n>`.
- Confirms whether a journal is genuinely open-access (DOAJ-listed). Useful as an OA verification signal.
- Returns ISSN, license, APC info.

## CORE

- v3 POST `https://api.core.ac.uk/v3/search/works` with `{ "q": "...", "limit": N }`.
- Needs `CORE_API_KEY` (free tier available); skipped with a one-line note if missing.
- Heterogeneous metadata — treat as supplementary.

## OpenAIRE Graph

- Search API: `https://api.openaire.eu/search/publications?keywords=<q>&size=N&format=json` (JSON now supported alongside the older XML).
- Useful for European OA records, dataset linking, and project linking.
- Schema variability — normalize carefully.

## Unpaywall

- DOI-keyed: `https://api.unpaywall.org/v2/<DOI>?email=<your-email>`.
- Set `UNPAYWALL_EMAIL` (required header per their TOS). Falls back to `anonymous@example.invalid` with degraded service.
- Use only to enrich DOI records with OA URL and license.

## DataCite

- REST API: `https://api.datacite.org/dois?query=<q>&page[size]=<n>`.
- Indexes DOIs for datasets, software, and other research artifacts.
- Citation count via `citation-count`; type via `attributes.types.resourceTypeGeneral` (Dataset, Software, Audiovisual, etc.).

## Retraction checks

Two parallel paths:

1. **Crossref**: read `relation.is-retracted-by` and `relation.is-corrected-by` arrays for each DOI — if non-empty, the paper has a retraction or correction notice.
2. **OpenAlex**: read the `is_retracted` boolean directly.

Cross-check both; raise the flag if either reports retraction. Show the **retraction notice DOI** when found.

## General

- Respect rate limits — every per-source script includes retries with backoff (`safe_request_json`, `retries=2`, `sleep_seconds=1.0`).
- Cache when appropriate (results live in `/tmp/lit_*.json`; safe to re-use within a session).
- Treat APIs as dynamic and evolving — if an endpoint fails, say so and continue with the working sources. **Never invent records to compensate.**
- Set `User-Agent` to something descriptive on every call (handled by `common.py`).
