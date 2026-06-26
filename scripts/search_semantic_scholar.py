#!/usr/bin/env python3
"""Search Semantic Scholar Graph API.

Provides influentialCitationCount, TLDR snippets, and cross-source IDs
(DOI, PubMed, arXiv) that help dedup downstream.

API doc: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

import argparse
import os

from common import add_output_argument, canonical_record, dump_json, safe_request_json


API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

FIELDS = ",".join([
    "paperId",
    "externalIds",
    "title",
    "abstract",
    "tldr",
    "venue",
    "year",
    "publicationDate",
    "authors.name",
    "openAccessPdf",
    "citationCount",
    "influentialCitationCount",
    "publicationTypes",
    "fieldsOfStudy",
])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance"], default="relevance")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = {
        "query": args.query,
        "limit": min(args.limit, 100),
        "fields": FIELDS,
    }
    if args.from_year or args.to_year:
        start = args.from_year or 1900
        end = args.to_year or 2100
        params["year"] = f"{start}-{end}"

    headers = {}
    if os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    payload = safe_request_json(API_URL, params=params, headers=headers, sleep_seconds=2.0)
    records = []
    for item in payload.get("data", []):
        ext = item.get("externalIds") or {}
        types = item.get("publicationTypes") or []
        article_type = types[0] if types else ""
        tldr = (item.get("tldr") or {}).get("text", "") if item.get("tldr") else ""
        record = canonical_record(
            "SemanticScholar",
            args.query,
            title=item.get("title", ""),
            authors=[a.get("name", "") for a in item.get("authors", [])],
            year=item.get("year"),
            publication_date=item.get("publicationDate", ""),
            venue=item.get("venue", ""),
            doi=ext.get("DOI", ""),
            pmid=ext.get("PubMed", ""),
            arxiv_id=ext.get("ArXiv", ""),
            article_type=article_type,
            abstract=item.get("abstract") or "",
            tldr=tldr,
            citations=item.get("citationCount"),
            influential_citations=item.get("influentialCitationCount"),
            is_oa=bool((item.get("openAccessPdf") or {}).get("url")),
            oa_url=(item.get("openAccessPdf") or {}).get("url", ""),
            concepts=item.get("fieldsOfStudy") or [],
            source_id=item.get("paperId", ""),
            raw=item,
        )
        records.append(record)

    if args.sort == "newest":
        records.sort(key=lambda r: r.get("publication_date") or "", reverse=True)

    dump_json({"source": "SemanticScholar", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
