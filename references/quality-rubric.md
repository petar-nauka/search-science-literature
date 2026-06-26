# Quality Rubric

Scoring is computed by `merge_dedup_rank.py` for every merged record.

## Relevance (0–3)

How well the record's title + abstract match the query terms.

- `3`: directly answers the user topic (all major query terms present)
- `2`: strongly related (most query terms present, or core noun phrase present)
- `1`: partially related (1–2 query terms present)
- `0`: peripheral or noisy

## Evidence Type (0–3)

- `3`: systematic review, meta-analysis, scoping review, Cochrane review
- `2`: strong original peer-reviewed article (journal-article from a reputable venue)
- `1`: weaker original article, technical note, brief communication, or unclear type
- `0`: non-peer-reviewed (preprint, editorial, news item, letter, erratum)

## Metadata Confidence (0–2)

- `2`: DOI + title + year + venue all present and verified across ≥ 2 sources
- `1`: mostly verified (some fields missing or single-source)
- `0`: identifier or venue ambiguity

## Influence (0–2)

Combines:

- `cited_by_count` thresholds (50+ → 2 baseline, 5+ → 1, else 0)
- `influential_citations` boost (Semantic Scholar): +1 if `influential ≥ 10`
- venue-tier boost: +1 if the venue is in a curated tier-1 list (Nature, Science, top discipline-specific)

Capped at `2`.

## Recency (0–2)

- `2`: published within the last `min(2, requested_window_years/3)` years
- `1`: within the requested window but older than the most-recent slice
- `0`: outside the preferred window

## Retraction Penalty

If `is_retracted == true`, subtract `5` from the total score. This pushes retracted papers to the bottom regardless of other signals, but they remain visible with a `⚠ RETRACTED` flag for transparency.

## Sorting Guidance

| Mode | Sort key (descending) |
|---|---|
| `relevance` | relevance → evidence → metadata → recency → influence → date |
| `influence` | evidence → influence → relevance → metadata → recency → date |
| `newest` | publication_date → relevance → metadata → influence |
| `systematic-review` | filter to evidence == 3 first, then sort by influence → date |

## Notes

- Citation counts and influence signals are **supportive**, never the only signal. A high-cite count on an outdated paper is not better than a recent, well-targeted, well-designed study.
- Recency is **relative to the user's requested window**, not absolute.
- A 0-score on metadata confidence usually means the record came from a single weak source — flag it in the audit trail.
