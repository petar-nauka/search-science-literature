# Source Priority

The skill fans out across **open scholarly APIs** and is robust to any one source being unavailable. Use this file to decide which sources to query for a given topic and how to resolve metadata conflicts.

## Tier 1 — Core open scholarly sources (always)

| Source | Strength | API doc |
|---|---|---|
| **OpenAlex** | broadest discovery; topic search; date sorting; cited-by counts; authors; sources; concepts; abstracts (inverted-index, reconstructed by the skill) | https://docs.openalex.org/ |
| **Crossref** | authoritative DOI validation; metadata normalization; journal/publisher records; funding info | https://api.crossref.org/swagger-ui/index.html |
| **Semantic Scholar** | citation graph, **influential citation count**, **TLDR** summaries, paper embeddings (re-ranking signal), s2 paper IDs | https://api.semanticscholar.org/api-docs/graph |

## Tier 2 — Domain-specific (add on topic match)

| Source | Domain | API doc |
|---|---|---|
| **PubMed** (NCBI E-utilities) | biomedical, life sciences, pharmacology, clinical | https://www.ncbi.nlm.nih.gov/books/NBK25500/ |
| **Europe PMC** | life sciences + chem + materials; full-text + references + citations; **also indexes bioRxiv/medRxiv/chemRxiv preprints** (`SRC:PPR`) | https://europepmc.org/RestfulWebService |
| **arXiv** | physics, math, CS, statistics, q-bio, q-fin, econ — preprints | https://info.arxiv.org/help/api/index.html |
| **DBLP** | computer science conference + journal records (XML/JSON) | https://dblp.org/faq/13501473 |
| **bioRxiv / medRxiv / chemRxiv** | life-science / medical / chemistry preprints — via Europe PMC `SRC:PPR` or direct bioRxiv API | https://api.biorxiv.org/ |

## Tier 3 — Open access + verification enrichment

| Source | Use | API doc |
|---|---|---|
| **DOAJ** | open-access journal/article verification, license + APC clarity | https://doaj.org/api/v3/docs |
| **CORE** | repository OA copies (needs `CORE_API_KEY`) | https://api.core.ac.uk/docs/v3 |
| **OpenAIRE Graph** | additional open research graph discovery (publications + datasets + software + projects) | https://graph.openaire.eu/docs/apis/search-api/ |
| **Unpaywall** | OA location lookup by DOI; license metadata | https://unpaywall.org/products/api |
| **DataCite** | datasets + software linked to publications; DOIs for research artifacts | https://support.datacite.org/docs/api |
| **Retraction check** (Crossref relations + OpenAlex `is_retracted`) | flag retracted/corrected papers | built-in |

## Tier 4 — Paywalled / entitlement-based (not queried by default)

- Web of Science Starter API (`scripts/search_wos_starter.py`, enabled with `--include-wos-starter` and `WOS_STARTER_API_KEY`)
- Scopus
- ScienceDirect
- IEEE Xplore

Keep Web of Science Starter off by default because free trial plans can be quota-limited. Use it for DOI, author, source-title, and bibliographic metadata checks; report `times cited` only when the subscribed response includes citation counts. If the user explicitly asks for another entitlement-based source and the environment cannot access it, say so in one sentence and continue with the strongest open evidence. Never scrape paywalled sites.

## Reliability order for metadata conflicts

When two sources disagree on a field, prefer in this order:

1. Publisher DOI landing page (resolved via `https://doi.org/<doi>`)
2. PubMed or Europe PMC (peer-review record)
3. Crossref (DOI registration record)
4. Web of Science Starter (credentialed bibliographic/citation metadata when available)
5. OpenAlex (aggregated)
6. Semantic Scholar (graph-derived)
7. Unpaywall (OA location only)
8. CORE / OpenAIRE / DOAJ (repository + index pages)
9. arXiv / bioRxiv / DBLP (preprint or domain-specific index)
10. Anything else

## Default retrieval mix

For a generic topic with no domain hint:

1. OpenAlex
2. Crossref
3. Semantic Scholar
4. Europe PMC
5. CORE (if `CORE_API_KEY` set)
6. OpenAIRE
7. Unpaywall enrichment by DOI for the final result set
8. Retraction check on the final result set

Add domain sources when the topic matches:

- biomedical → PubMed + bioRxiv/medRxiv
- CS / ML → arXiv + DBLP
- physics / math → arXiv
- chemistry → chemRxiv (via Europe PMC) + DOAJ
- datasets / software → DataCite + OpenAIRE
