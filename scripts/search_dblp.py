#!/usr/bin/env python3
"""Search DBLP for computer science publications.

API doc: https://dblp.org/faq/13501473
"""

from __future__ import annotations

import argparse

from common import add_output_argument, canonical_record, dump_json, safe_request_json


API_URL = "https://dblp.org/search/publ/api"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    add_output_argument(parser)
    return parser.parse_args()


def author_list(info: dict) -> list[str]:
    authors_field = (info.get("authors") or {}).get("author")
    if not authors_field:
        return []
    if isinstance(authors_field, dict):
        authors_field = [authors_field]
    out = []
    for a in authors_field:
        if isinstance(a, dict):
            name = a.get("text") or a.get("@text") or ""
        else:
            name = str(a)
        if name:
            out.append(name)
    return out


def main() -> None:
    args = parse_args()
    payload = safe_request_json(
        API_URL,
        params={"q": args.query, "format": "json", "h": min(args.limit, 100)},
    )
    hits = (((payload.get("result") or {}).get("hits") or {}).get("hit")) or []
    records = []
    for hit in hits:
        info = hit.get("info", {}) or {}
        year = int(info.get("year")) if str(info.get("year", "")).isdigit() else None
        if args.from_year and year and year < args.from_year:
            continue
        if args.to_year and year and year > args.to_year:
            continue
        record = canonical_record(
            "DBLP",
            args.query,
            title=info.get("title", ""),
            authors=author_list(info),
            year=year,
            publication_date=str(year) if year else "",
            venue=info.get("venue", ""),
            doi=info.get("doi", ""),
            article_type=info.get("type", ""),
            source_id=info.get("key", ""),
            raw=info,
        )
        records.append(record)
    dump_json({"source": "DBLP", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
