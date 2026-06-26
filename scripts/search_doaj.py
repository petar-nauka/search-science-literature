#!/usr/bin/env python3
"""Search DOAJ for open-access articles.

DOAJ is the gold reference for whether a journal is *genuinely* OA — useful
both as a search source and as a verification signal in the merge step.

API doc: https://doaj.org/api/v3/docs
"""

from __future__ import annotations

import argparse
import urllib.parse

from common import add_output_argument, canonical_record, dump_json, safe_request_json


BASE = "https://doaj.org/api/v3/search/articles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parts = [args.query]
    if args.from_year:
        parts.append(f"bibjson.year:>={args.from_year}")
    if args.to_year:
        parts.append(f"bibjson.year:<={args.to_year}")
    query_string = " AND ".join(parts)
    url = f"{BASE}/{urllib.parse.quote(query_string)}"
    payload = safe_request_json(url, params={"pageSize": min(args.limit, 100)})
    records = []
    for hit in payload.get("results", []):
        bib = hit.get("bibjson", {}) or {}
        identifiers = bib.get("identifier", []) or []
        doi = ""
        issns = []
        for ident in identifiers:
            id_type = (ident.get("type") or "").lower()
            if id_type == "doi":
                doi = ident.get("id", "")
            elif id_type in ("pissn", "eissn"):
                issns.append(ident.get("id", ""))
        authors = [a.get("name", "") for a in bib.get("author", [])]
        licenses = [(l or {}).get("type", "") for l in (bib.get("journal", {}) or {}).get("license", [])]
        record = canonical_record(
            "DOAJ",
            args.query,
            title=bib.get("title", ""),
            authors=authors,
            year=int(bib.get("year")) if str(bib.get("year", "")).isdigit() else None,
            publication_date=f"{bib.get('year', '')}",
            venue=(bib.get("journal", {}) or {}).get("title", ""),
            issn=issns,
            doi=doi,
            article_type="journal-article",
            abstract=bib.get("abstract", ""),
            is_oa=True,
            license=licenses[0] if licenses else "",
            peer_review_status="peer-reviewed",
            source_id=hit.get("id", ""),
            raw=hit,
        )
        records.append(record)
    dump_json({"source": "DOAJ", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
