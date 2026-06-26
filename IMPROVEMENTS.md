# Improvements & API Keys

How to make this skill faster, more accurate, and broader — by registering for free API keys and by adding new sources / pipeline stages.

Ordered by **return on time invested** (highest first).

> **Email placeholder:** Every example below uses `you@example.com`. Replace it with **your own real email** — the polite-pool APIs (OpenAlex, Crossref, Unpaywall) use it to identify your traffic. Fake emails get throttled or banned.

---

## 🟢 Tier 1 — no registration, just an email (5 minutes)

These APIs don't have a signup form — they read an `email` parameter (or `User-Agent`) from your requests and put you into the **polite pool** (higher rate limits, priority queue).

| API | What you provide | What you get | Env var |
|---|---|---|---|
| **OpenAlex** | your email | shared pool → ~10 req/sec, priority queue | `OPENALEX_MAILTO=you@example.com` |
| **Crossref** | your email | polite-pool quota (fewer 429s) | `CROSSREF_MAILTO=you@example.com` |
| **Unpaywall** | your email (TOS requirement) | without it, falls back to `anonymous@example.invalid` — heavily rate-limited | `UNPAYWALL_EMAIL=you@example.com` |

**How to apply:** create a `.env` file in the skill folder (already in `.gitignore`):

```bash
OPENALEX_MAILTO=you@example.com
CROSSREF_MAILTO=you@example.com
UNPAYWALL_EMAIL=you@example.com
```

Then either source it before running the scripts (`set -a; source .env; set +a`) or use `python-dotenv` to load it.

---

## 🟡 Tier 2 — fast signup, instant key (10–15 minutes each)

### 1. NCBI / PubMed API Key — highest leverage

- **URL:** https://www.ncbi.nlm.nih.gov/account/
- **Steps:** register → log in → **Settings → API Key Management → Create an API Key** → copy
- **Effect:** PubMed rate limit goes from **3 → 10 req/sec** (3.3× faster)
- **Env:** `NCBI_API_KEY=<your-key>`

### 2. CORE API Key — unlocks an extra OA source

- **URL:** https://core.ac.uk/services/api → "Apply for an API Key"
- **Steps:** register → 1-minute form → key arrives by email immediately
- **Effect:** activates `scripts/search_core.py` (repository OA copies). Without the key the orchestrator skips CORE with a warning.
- **Env:** `CORE_API_KEY=<your-key>`

### 3. OpenAIRE Personal Token — higher quota

- **URL:** https://aai.openaire.eu/ → "Sign up" → then on https://graph.openaire.eu/ → "Personal Token"
- **Effect:** ~7,200 req/h instead of anonymous 60 req/h
- **Env:** `OPENAIRE_TOKEN=<your-key>`
- **Note:** `search_openaire.py` currently runs without a token. To use the token, the script needs a small update — open an issue or PR.

---

## 🟠 Tier 3 — requires approval (days to weeks)

### 4. Semantic Scholar API Key — biggest quality win

- **URL:** https://www.semanticscholar.org/product/api#api-key-form
- **Steps:** fill out the form (use case, expected query volume) → AllenAI reviews → key by email
- **Approval time:** typically 1–3 weeks (sometimes longer)
- **Effect:** rate limit ~1 req/sec → ~10 req/sec. Without a key, the shared pool returns HTTP 429 in ~50% of calls.
- **Env:** `SEMANTIC_SCHOLAR_API_KEY=<your-key>`
- **Tip:** in the "use case" field, mention non-commercial / personal research / literature review usage — non-commercial applicants are routinely approved.

---

## 🔵 Tier 4 — new integrations worth adding

These are **not yet** in the skill. Each would meaningfully expand coverage or quality. Open an issue or PR for any you want — happy to integrate.

### A. ORCID Public API — author disambiguation
- **Free**, no key needed for the public endpoint
- **Why:** distinguishes "John Smith (Imperial College)" from "John Smith (MIT)" → accurate author dedup
- https://info.orcid.org/documentation/features/public-api/

### B. OpenCitations REST API — citation network
- **Free**, no key
- **Why:** walk the citation graph from a seed paper (similar to Connected Papers)
- https://opencitations.net/index/coci/api/v1

### C. Lens.org Scholar API — broad index + patents
- Free **academic tier** (requires academic email)
- **Why:** combines publications + patents + grant data; useful for innovation-oriented reviews
- https://www.lens.org/lens/user/subscriptions#scholar

### D. Scite API — "smart citations"
- Free tier (~100 calls/month)
- **Why:** classifies each citation as **supporting**, **contrasting**, or mentioning — invaluable for systematic reviews
- https://scite.ai/api

### E. CrossRef Event Data — altmetrics
- **Free**, no key
- **Why:** Twitter/Wikipedia/blog mentions → early impact signal before citations accrue
- https://www.eventdata.crossref.org/guide/

### F. arXiv Vanity / ar5iv — HTML versions of arXiv papers
- **Free**
- **Why:** machine-readable HTML instead of PDF; lets us do semantic extraction reliably
- https://ar5iv.labs.arxiv.org/

---

## 🟣 Pipeline improvements (no new APIs)

### 1. Embedding-based re-ranking — high impact, medium effort
After dedup, run titles + abstracts through an embedding model (Voyage AI, OpenAI, or a local Sentence-Transformer) and compute cosine similarity to the user query. Beats keyword-relevance match for fuzzy queries.

### 2. Citation-graph expansion — high impact
After the orchestrator returns Top-10, traverse Semantic Scholar `/paper/{id}/references` and `/citations` → discover "seminal works" and "recent extensions" automatically connected to the topic.

### 3. Full-text PDF extraction — medium impact, high effort
When `oa_url` is available, fetch the PDF, extract text with PyMuPDF or pdfplumber, and feed key paragraphs (intro, conclusion, results tables) to an LLM for grounded summaries.

### 4. Multi-language seed expansion (Bulgarian and beyond)
Current `query_expand.py` only covers hydrogen/electrolysis. Add LLM-driven Bulgarian→English translation for arbitrary topics (no hard-coded regex patterns).

### 5. Cache layer — high impact for repeat sessions
SQLite cache for DOI → result mappings with a 7-day TTL. Saves rate limit and speeds up follow-up research sessions 5–10×.

### 6. Streaming preview in the orchestrator
Instead of blocking until all 5–8 APIs return, stream each source as it completes (`yield` in the orchestrator → progress in the UI).

---

## 📋 Recommended order

**Week 1:**
1. Tier 1 (10 minutes) → `.env` with the three emails
2. Tier 2.1 NCBI API key (15 minutes) — instant value for PubMed
3. Tier 2.2 CORE API key (15 minutes) — unlocks a previously skipped source

**Week 2:**
4. Tier 3 Semantic Scholar form — apply now, key arrives in 1–3 weeks

**Later:**
5. Pick a Tier 4 integration or pipeline improvement that fits your research — open an issue or PR.

---

## .env example (copy and edit)

```bash
# Tier 1 — polite-pool identification (no signup, just your real email)
OPENALEX_MAILTO=you@example.com
CROSSREF_MAILTO=you@example.com
UNPAYWALL_EMAIL=you@example.com

# Tier 2 — instant signup keys
NCBI_API_KEY=
CORE_API_KEY=
OPENAIRE_TOKEN=

# Tier 3 — approval required (Semantic Scholar reviews each application)
SEMANTIC_SCHOLAR_API_KEY=
```

Leave any key blank — the skill degrades gracefully (skips or shared-pool fallback) instead of failing.
