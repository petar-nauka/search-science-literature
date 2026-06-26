#!/usr/bin/env python3
"""Search DataCite for datasets, software, and other research artifacts.

API doc: https://support.datacite.org/docs/api
"""

from __future__ import annotations

import argparse

from common import add_output_argument, canonical_record, dump_json, safe_request_json


API_URL = "https://api.datacite.org/dois"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--resource-type", help="Filter by resourceTypeGeneral (Dataset, Software, etc.)")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params: dict = {
        "query": args.query,
        "page[size]": min(args.limit, 100),
    }
    if args.from_year:
        params.setdefault("query", args.query)
        params["query"] += f" AND publicationYear:>={args.from_year}"
    if args.to_year:
        params["query"] += f" AND publicationYear:<={args.to_year}"
    if args.resource_type:
        params["resource-type-id"] = args.resource_type

    payload = safe_request_json(API_URL, params=params)
    records = []
    for hit in payload.get("data", []):
        attrs = hit.get("attributes", {}) or {}
        titles = attrs.get("titles", []) or []
        creators = attrs.get("creators", []) or []
        descriptions = attrs.get("descriptions", []) or []
        types = attrs.get("types", {}) or {}
        record = canonical_record(
            "DataCite",
            args.query,
            title=(titles[0] or {}).get("title", "") if titles else "",
            authors=[c.get("name", "") for c in creators],
            year=attrs.get("publicationYear"),
            publication_date=str(attrs.get("publicationYear", "")),
            venue=attrs.get("publisher", ""),
            doi=hit.get("id", ""),
            article_type=types.get("resourceTypeGeneral", "") or types.get("resourceType", ""),
            abstract=(descriptions[0] or {}).get("description", "") if descriptions else "",
            citations=attrs.get("citationCount"),
            is_oa=True,
            oa_url=attrs.get("url", ""),
            source_id=hit.get("id", ""),
            raw=hit,
        )
        records.append(record)
    dump_json({"source": "DataCite", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
