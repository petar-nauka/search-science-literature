# Field Mapping

## Canonical Record Fields

The skill normalizes every retrieved record into this schema:

| Field | Type | Notes |
|---|---|---|
| `title` | str | Cleaned (no surrounding whitespace, single-spaced) |
| `authors` | list[str] | "First Last" form preferred; "Last, First" tolerated |
| `first_author` | str | First entry of `authors` |
| `year` | int \| null | Derived from `publication_date` if missing |
| `publication_date` | str | `YYYY-MM-DD` if known, else `YYYY-MM` or `YYYY` |
| `venue` | str | Journal / conference / repository display name |
| `issn` | list[str] | Print + electronic ISSN; used in dedup |
| `doi` | str | Lowercased, no `https://doi.org/` prefix |
| `doi_url` | str | `https://doi.org/<doi>` (built from `doi`) |
| `pmid` | str | All digits |
| `pmcid` | str | `PMC` prefix preserved |
| `arxiv_id` | str | `YYMM.NNNNN` or `<category>/NNNNNNN` |
| `article_type` | str | "journal-article", "review-article", "preprint", "dataset", "software", etc. |
| `abstract` | str | Plain text. OpenAlex inverted-index reconstructed; Crossref JATS markup stripped. |
| `tldr` | str | Semantic Scholar TLDR snippet when available |
| `source_databases` | list[str] | Names of every API that returned this record |
| `source_ids` | dict[str, str] | `{ "OpenAlex": "W123…", "PubMed": "12345" }` |
| `citations` | int \| null | Max across sources (OpenAlex `cited_by_count`, EPMC `citedByCount`, S2 `citationCount`) |
| `influential_citations` | int \| null | Semantic Scholar `influentialCitationCount` |
| `is_oa` | bool \| null | True if any source confirms OA |
| `oa_url` | str | First confirmed OA link (Unpaywall > OpenAlex > EPMC > CORE) |
| `license` | str | OA license string (e.g. "cc-by") when known |
| `peer_review_status` | str | "peer-reviewed" / "preprint" / "unclear" |
| `language` | str | ISO 639-1 when known |
| `concepts` | list[str] | OpenAlex concepts (top 5) |
| `subjects` | list[str] | Crossref / DataCite subject tags |
| `is_retracted` | bool | True if any retraction signal found |
| `retraction_notice_doi` | str | DOI of the retraction notice when found |
| `query` | str | Original user query that produced this record |
| `scores` | dict | Filled by `merge_dedup_rank.py` (relevance, evidence, metadata, influence, recency, total) |
| `raw` | dict | Source-specific raw payload (debug / audit) |

## Mapping Hints

### OpenAlex (`https://api.openalex.org/works`)

| OpenAlex field | Canonical |
|---|---|
| `id` | `source_ids.OpenAlex` |
| `display_name` | `title` |
| `publication_year` | `year` |
| `publication_date` | `publication_date` |
| `primary_location.source.display_name` | `venue` |
| `primary_location.source.issn_l` + `issn` | `issn` |
| `doi` | `doi` |
| `authorships[].author.display_name` | `authors` |
| `cited_by_count` | `citations` |
| `open_access.is_oa` | `is_oa` |
| `open_access.oa_url` | `oa_url` (fallback) |
| `type` | `article_type` |
| `language` | `language` |
| `is_retracted` | `is_retracted` |
| `concepts[].display_name` (top 5 by score) | `concepts` |
| `abstract_inverted_index` (reconstructed) | `abstract` |

### Crossref (`https://api.crossref.org/works`)

| Crossref field | Canonical |
|---|---|
| `DOI` | `doi` |
| `title[0]` | `title` |
| `published-print.date-parts` or `published-online.date-parts` | `publication_date` |
| `container-title[0]` | `venue` |
| `ISSN[]` | `issn` |
| `author[]` (given + family) | `authors` |
| `type` | `article_type` |
| `abstract` (JATS markup stripped) | `abstract` |
| `subject[]` | `subjects` |
| `relation.is-retracted-by[].id`, `relation.is-corrected-by[].id` | `is_retracted` + `retraction_notice_doi` |

### PubMed (E-utilities)

| PubMed field | Canonical |
|---|---|
| `uid` | `pmid` |
| `title` | `title` |
| `pubdate` | `publication_date` |
| `fulljournalname` | `venue` |
| `authors[].name` | `authors` |
| `pubtype[]` | `article_type` |
| `articleids[]` (idtype=doi) | `doi` |

### Europe PMC

| EPMC field | Canonical |
|---|---|
| `id` | `source_ids.EuropePMC` |
| `pmid` | `pmid` |
| `pmcid` | `pmcid` |
| `title` | `title` |
| `journalTitle` | `venue` |
| `pubYear` | `year` |
| `firstPublicationDate` | `publication_date` |
| `doi` | `doi` |
| `authorString` (comma split) | `authors` |
| `pubType` | `article_type` |
| `abstractText` | `abstract` |
| `citedByCount` | `citations` |
| `isOpenAccess == "Y"` | `is_oa` |
| `fullTextUrlList.fullTextUrl[0].url` | `oa_url` |

### Semantic Scholar

| S2 field | Canonical |
|---|---|
| `paperId` | `source_ids.SemanticScholar` |
| `title` | `title` |
| `year` | `year` |
| `publicationDate` | `publication_date` |
| `venue` | `venue` |
| `externalIds.DOI` | `doi` |
| `externalIds.PubMed` | `pmid` |
| `externalIds.ArXiv` | `arxiv_id` |
| `authors[].name` | `authors` |
| `publicationTypes[]` | `article_type` |
| `abstract` | `abstract` |
| `citationCount` | `citations` |
| `influentialCitationCount` | `influential_citations` |
| `tldr.text` | `tldr` |
| `openAccessPdf.url` | `oa_url` |

### arXiv (Atom XML)

| arXiv field | Canonical |
|---|---|
| `id` (URL → strip `http://arxiv.org/abs/`) | `arxiv_id` |
| `title` | `title` |
| `summary` | `abstract` |
| `published` | `publication_date` |
| `author[].name` | `authors` |
| `arxiv:doi` | `doi` (when present) |
| `category[].term` | `concepts` |
| (constant) `"preprint"` | `article_type` |

### DBLP

| DBLP field | Canonical |
|---|---|
| `info.key` | `source_ids.DBLP` |
| `info.title` | `title` |
| `info.year` | `year` |
| `info.venue` | `venue` |
| `info.doi` | `doi` |
| `info.authors.author[].text` | `authors` |
| `info.type` | `article_type` |

### DOAJ

| DOAJ field | Canonical |
|---|---|
| `id` | `source_ids.DOAJ` |
| `bibjson.title` | `title` |
| `bibjson.year` | `year` |
| `bibjson.journal.title` | `venue` |
| `bibjson.identifier[].id` (type=doi) | `doi` |
| `bibjson.identifier[].id` (type=pissn/eissn) | `issn` |
| `bibjson.author[].name` | `authors` |
| `bibjson.abstract` | `abstract` |
| `bibjson.license[].type` | `license` |
| (constant) `true` | `is_oa` |

### DataCite

| DataCite field | Canonical |
|---|---|
| `id` | `doi` |
| `attributes.titles[0].title` | `title` |
| `attributes.publicationYear` | `year` |
| `attributes.publisher` | `venue` |
| `attributes.creators[].name` | `authors` |
| `attributes.types.resourceTypeGeneral` | `article_type` (Dataset / Software / etc.) |
| `attributes.descriptions[0].description` | `abstract` |
| `attributes.citationCount` | `citations` |

### Unpaywall (enrichment, not primary search)

| Unpaywall field | Canonical |
|---|---|
| `is_oa` | `is_oa` |
| `best_oa_location.url` | `oa_url` |
| `best_oa_location.license` | `license` |
| `best_oa_location.host_type` | (annotation) |
