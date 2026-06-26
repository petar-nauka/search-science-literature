#!/usr/bin/env python3
"""Merge canonical records, deduplicate them, and rank.

v2 improvements:
- Fuzzy title match (SequenceMatcher >= 0.92) as a third dedup layer.
- ISSN-based venue equivalence in dedup.
- Influential-citation + venue-tier influence boost.
- Retraction penalty (-5 total).
- `systematic-review` sort mode.
- Better field-merge precedence (use longest non-empty title; prefer Crossref/OpenAlex DOI form).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any

from common import (
    add_output_argument,
    clean_text,
    dump_json,
    normalize_doi,
    normalize_text,
    parse_date_to_year,
    title_similarity,
)


# Tier-1 venue substrings get an influence boost. Keep small + curated.
TIER_1_VENUES = (
    "nature",
    "science",
    "cell",
    "lancet",
    "new england journal of medicine",
    "proceedings of the national academy of sciences",
    "nature communications",
    "advanced materials",
    "joule",
    "journal of the american chemical society",
    "physical review letters",
    "advances in neural information processing systems",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="JSON files containing canonical records")
    parser.add_argument(
        "--sort",
        choices=["newest", "relevance", "influence", "systematic-review"],
        default="relevance",
    )
    parser.add_argument("--query", default="", help="Original user query for relevance scoring")
    parser.add_argument("--fuzzy-threshold", type=float, default=0.92)
    add_output_argument(parser)
    return parser.parse_args()


def load_records(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "records" in payload:
        return payload["records"]
    return payload if isinstance(payload, list) else []


def merge_records(target: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    # Prefer longer non-empty strings for title/venue/abstract/tldr.
    for key in ("title", "venue", "abstract", "tldr", "oa_url"):
        cur = target.get(key) or ""
        inc = incoming.get(key) or ""
        if len(inc) > len(cur):
            target[key] = inc
    for key in ("doi", "doi_url", "pmid", "pmcid", "arxiv_id", "article_type", "license", "language"):
        if not target.get(key) and incoming.get(key):
            target[key] = incoming[key]
    if not target.get("publication_date") and incoming.get("publication_date"):
        target["publication_date"] = incoming["publication_date"]
    if not target.get("year") and incoming.get("year"):
        target["year"] = incoming["year"]
    if incoming.get("authors"):
        existing = {author.lower() for author in target.get("authors", [])}
        for author in incoming["authors"]:
            if author.lower() not in existing:
                target.setdefault("authors", []).append(author)
                existing.add(author.lower())
        if not target.get("first_author"):
            target["first_author"] = target["authors"][0]
    for source in incoming.get("source_databases", []):
        if source not in target.setdefault("source_databases", []):
            target["source_databases"].append(source)
    target.setdefault("source_ids", {}).update(incoming.get("source_ids", {}))
    existing_issn = set(target.get("issn") or [])
    for issn in (incoming.get("issn") or []):
        if issn not in existing_issn:
            target.setdefault("issn", []).append(issn)
            existing_issn.add(issn)
    existing_concepts = set(target.get("concepts") or [])
    for c in (incoming.get("concepts") or []):
        if c not in existing_concepts:
            target.setdefault("concepts", []).append(c)
            existing_concepts.add(c)
    existing_subjects = set(target.get("subjects") or [])
    for s in (incoming.get("subjects") or []):
        if s not in existing_subjects:
            target.setdefault("subjects", []).append(s)
            existing_subjects.add(s)
    target["is_oa"] = bool(target.get("is_oa") or incoming.get("is_oa"))
    if incoming.get("citations") is not None:
        target["citations"] = max(target.get("citations") or 0, incoming["citations"])
    if incoming.get("influential_citations") is not None:
        target["influential_citations"] = max(
            target.get("influential_citations") or 0, incoming["influential_citations"]
        )
    target["is_retracted"] = bool(target.get("is_retracted")) or bool(incoming.get("is_retracted"))
    if incoming.get("retraction_notice_doi") and not target.get("retraction_notice_doi"):
        target["retraction_notice_doi"] = incoming["retraction_notice_doi"]
    return target


def find_fuzzy_match(record: dict[str, Any], merged_list: list[dict[str, Any]], threshold: float) -> dict | None:
    """Return an existing merged record that fuzzy-matches the candidate, or None."""
    title = record.get("title") or ""
    if len(title) < 10:
        return None
    year = record.get("year") or parse_date_to_year(record.get("publication_date", ""))
    issn_set = set(record.get("issn") or [])
    venue_norm = normalize_text(record.get("venue") or "")
    for other in merged_list:
        # year tolerance: same year, or ±1 for online-first vs printed
        other_year = other.get("year") or parse_date_to_year(other.get("publication_date", ""))
        if year and other_year and abs(year - other_year) > 1:
            continue
        if title_similarity(title, other.get("title", "")) < threshold:
            continue
        # Confirm with venue or ISSN match (avoids merging unrelated review/original with same title family)
        other_issn = set(other.get("issn") or [])
        if issn_set and other_issn and (issn_set & other_issn):
            return other
        other_venue = normalize_text(other.get("venue") or "")
        if venue_norm and other_venue and (venue_norm == other_venue or venue_norm in other_venue or other_venue in venue_norm):
            return other
        # If neither side has venue/ISSN, accept fuzzy-only match as a soft merge
        if not issn_set and not other_issn and not venue_norm and not other_venue:
            return other
    return None


def dedup_key(record: dict[str, Any]) -> tuple[str, str] | None:
    doi = normalize_doi(record.get("doi", ""))
    if doi:
        return ("doi", doi)
    pmid = clean_text(record.get("pmid", ""))
    if pmid:
        return ("pmid", pmid)
    arxiv_id = clean_text(record.get("arxiv_id", ""))
    if arxiv_id:
        return ("arxiv", arxiv_id)
    return None  # fall through to fuzzy match


def score_record(record: dict[str, Any], query: str) -> dict[str, int]:
    title = normalize_text(record.get("title", ""))
    abstract = normalize_text(record.get("abstract", "") + " " + (record.get("tldr") or ""))
    query_terms = [term for term in normalize_text(query).split() if len(term) > 2]

    term_hits = sum(1 for term in query_terms if term in title or term in abstract)
    if not query_terms:
        relevance = 1
    elif term_hits >= len(query_terms):
        relevance = 3
    elif term_hits >= max(1, len(query_terms) // 2):
        relevance = 2
    elif term_hits >= 1:
        relevance = 1
    else:
        relevance = 0

    article_type = normalize_text(record.get("article_type", ""))
    if any(k in article_type for k in ("systematic review", "meta analysis", "cochrane")):
        evidence = 3
    elif "review" in article_type:
        evidence = 3 if article_type.endswith("review article") or "review-article" in article_type else 2
    elif "preprint" in article_type or record.get("peer_review_status") == "preprint":
        evidence = 0
    elif article_type in {"journal article", "research article", "article", "journal-article"}:
        evidence = 2
    else:
        evidence = 1 if article_type else 0

    has_doi = bool(record.get("doi"))
    has_title = bool(record.get("title"))
    has_venue = bool(record.get("venue"))
    has_year = bool(record.get("year") or parse_date_to_year(record.get("publication_date", "")))
    if has_doi and has_title and has_year and has_venue:
        metadata = 2
    elif has_title and (has_doi or has_year):
        metadata = 1
    else:
        metadata = 0

    citations = record.get("citations") or 0
    influential = record.get("influential_citations") or 0
    venue_norm = normalize_text(record.get("venue", ""))
    venue_tier1 = any(v in venue_norm for v in TIER_1_VENUES)

    if citations >= 50:
        influence = 2
    elif citations >= 5:
        influence = 1
    else:
        influence = 0
    if influential >= 10:
        influence = min(2, influence + 1)
    if venue_tier1:
        influence = min(2, influence + 1)

    year = record.get("year") or parse_date_to_year(record.get("publication_date", "")) or 0
    current_year = datetime.utcnow().year
    if year >= current_year - 1:
        recency = 2
    elif year >= current_year - 3:
        recency = 1
    else:
        recency = 0

    total = relevance + evidence + metadata + influence + recency
    if record.get("is_retracted"):
        total -= 5

    return {
        "relevance": relevance,
        "evidence": evidence,
        "metadata": metadata,
        "influence": influence,
        "recency": recency,
        "total": total,
    }


def sort_key(record: dict[str, Any], mode: str):
    scores = record.get("scores", {})
    date_value = clean_text(record.get("publication_date", ""))
    retraction_demote = -10 if record.get("is_retracted") else 0
    if mode == "newest":
        return (
            retraction_demote,
            date_value,
            scores.get("relevance", 0),
            scores.get("metadata", 0),
        )
    if mode == "influence":
        return (
            retraction_demote,
            scores.get("evidence", 0),
            scores.get("influence", 0),
            scores.get("relevance", 0),
            scores.get("metadata", 0),
            date_value,
        )
    if mode == "systematic-review":
        is_sr = 1 if scores.get("evidence", 0) == 3 else 0
        return (
            retraction_demote,
            is_sr,
            scores.get("influence", 0),
            scores.get("relevance", 0),
            scores.get("metadata", 0),
            date_value,
        )
    return (
        retraction_demote,
        scores.get("relevance", 0),
        scores.get("evidence", 0),
        scores.get("metadata", 0),
        scores.get("recency", 0),
        scores.get("influence", 0),
        date_value,
    )


def main() -> None:
    args = parse_args()
    merged_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    unkeyed: list[dict[str, Any]] = []
    initial_count = 0
    source_counts: dict[str, int] = {}

    for path in args.inputs:
        for record in load_records(path):
            initial_count += 1
            for src in record.get("source_databases", []):
                source_counts[src] = source_counts.get(src, 0) + 1
            key = dedup_key(record)
            if key is None:
                # Try fuzzy match against everything we have so far
                merged_list = list(merged_by_key.values()) + unkeyed
                match = find_fuzzy_match(record, merged_list, args.fuzzy_threshold)
                if match is not None:
                    merge_records(match, record)
                else:
                    unkeyed.append(record)
                continue
            if key in merged_by_key:
                merge_records(merged_by_key[key], record)
            else:
                # Also try fuzzy match before adding as new
                fuzzy = find_fuzzy_match(record, list(merged_by_key.values()) + unkeyed, args.fuzzy_threshold)
                if fuzzy is not None:
                    merge_records(fuzzy, record)
                    # promote unkeyed match to keyed if possible
                    if fuzzy in unkeyed and key is not None:
                        unkeyed.remove(fuzzy)
                        merged_by_key[key] = fuzzy
                else:
                    merged_by_key[key] = record

    merged_records = list(merged_by_key.values()) + unkeyed
    for record in merged_records:
        record["scores"] = score_record(record, args.query or record.get("query", ""))

    if args.sort == "systematic-review":
        # Hide non-review records by default in this mode
        merged_records = [r for r in merged_records if r["scores"]["evidence"] == 3]

    merged_records.sort(key=lambda item: sort_key(item, args.sort), reverse=True)
    dump_json(
        {
            "initial_count": initial_count,
            "deduplicated_count": len(merged_records),
            "sort_mode": args.sort,
            "source_counts": source_counts,
            "retracted_count": sum(1 for r in merged_records if r.get("is_retracted")),
            "records": merged_records,
        },
        args.output,
        args.pretty,
    )


if __name__ == "__main__":
    main()
