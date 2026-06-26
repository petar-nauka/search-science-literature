#!/usr/bin/env python3
"""Search CORE and emit canonical records."""

from __future__ import annotations

import argparse
import os

from common import add_output_argument, canonical_record, dump_json, safe_request_json


API_URL = "https://api.core.ac.uk/v3/search/works"


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
    api_key = os.getenv("CORE_API_KEY")
    if not api_key:
        raise SystemExit("CORE_API_KEY is required for CORE API requests in this script.")
    body = {
        "q": args.query,
        "limit": args.limit,
        "scroll": False,
    }
    if args.from_year or args.to_year:
        body["publishedDate"] = {
            "from": f"{args.from_year or 1900}-01-01",
            "to": f"{args.to_year or 2100}-12-31",
        }
    payload = safe_request_json(
        API_URL,
        method="POST",
        body=body,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    records = []
    for item in payload.get("results", []):
        record = canonical_record(
            "CORE",
            args.query,
            title=item.get("title", ""),
            authors=[author.get("name", "") for author in item.get("authors", [])],
            publication_date=item.get("publishedDate", ""),
            venue=item.get("publisher", ""),
            doi=item.get("doi", ""),
            abstract=item.get("abstract", ""),
            is_oa=item.get("openAccess"),
            oa_url=item.get("downloadUrl", ""),
            source_id=str(item.get("id", "")),
            raw=item,
        )
        records.append(record)
    dump_json({"source": "CORE", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
