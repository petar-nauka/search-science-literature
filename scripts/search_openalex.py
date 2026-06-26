#!/usr/bin/env python3
"""Search OpenAlex works and emit canonical records.

v2 improvements:
- Reconstruct `abstract` from `abstract_inverted_index`.
- Capture `is_retracted`, ISSN, top concepts, language.
- Polite-pool support via OPENALEX_MAILTO.
"""

from __future__ import annotations

import argparse
import os

from common import (
    add_output_argument,
    canonical_record,
    dump_json,
    reconstruct_inverted_index,
    safe_request_json,
)


API_URL = "https://api.openalex.org/works"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance", "cited"], default="relevance")
    parser.add_argument("--filter-type", help="Optional OpenAlex type filter (e.g. journal-article, review)")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filters = []
    if args.from_year:
        filters.append(f"from_publication_date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"to_publication_date:{args.to_year}-12-31")
    if args.filter_type:
        filters.append(f"type:{args.filter_type}")

    params = {
        "search": args.query,
        "per-page": min(args.limit, 200),
        "sort": {
            "newest": "publication_date:desc",
            "relevance": "relevance_score:desc",
            "cited": "cited_by_count:desc",
        }[args.sort],
    }
    if filters:
        params["filter"] = ",".join(filters)
    if os.getenv("OPENALEX_MAILTO"):
        params["mailto"] = os.getenv("OPENALEX_MAILTO")

    payload = safe_request_json(API_URL, params=params)
    records = []
    for item in payload.get("results", []):
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
        ]
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        venue = source.get("display_name", "")
        issns = [source.get("issn_l", "")] + (source.get("issn") or [])

        concepts = [
            concept.get("display_name", "")
            for concept in (item.get("concepts") or [])[:5]
        ]

        abstract = reconstruct_inverted_index(item.get("abstract_inverted_index"))

        record = canonical_record(
            "OpenAlex",
            args.query,
            title=item.get("display_name", ""),
            authors=authors,
            year=item.get("publication_year"),
            publication_date=item.get("publication_date", ""),
            venue=venue,
            issn=issns,
            doi=item.get("doi", ""),
            article_type=item.get("type", ""),
            abstract=abstract,
            citations=item.get("cited_by_count"),
            is_oa=(item.get("open_access") or {}).get("is_oa"),
            oa_url=(item.get("open_access") or {}).get("oa_url", ""),
            license=(item.get("open_access") or {}).get("license", ""),
            language=item.get("language", ""),
            concepts=concepts,
            is_retracted=bool(item.get("is_retracted")),
            source_id=item.get("id", ""),
            raw=item,
        )
        records.append(record)
    dump_json({"source": "OpenAlex", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
