#!/usr/bin/env python3
"""Search Crossref works and emit canonical records.

v2 improvements:
- Strip JATS markup from abstracts.
- Capture ISSN and subjects.
- Detect retraction via `relation.is-retracted-by` / `relation.is-corrected-by`.
"""

from __future__ import annotations

import argparse
import os

from common import (
    add_output_argument,
    canonical_record,
    clean_text,
    dump_json,
    normalize_doi,
    safe_request_json,
    strip_markup,
    USER_AGENT,
)


API_URL = "https://api.crossref.org/works"


def parse_date(parts):
    if not parts or not parts[0]:
        return ""
    date_parts = parts[0]
    padded = [str(part).zfill(2) for part in date_parts]
    return "-".join([padded[0]] + padded[1:])


def detect_retraction(item):
    """Return (is_retracted, retraction_notice_doi) for a Crossref record."""
    relation = item.get("relation") or {}
    retraction_keys = ("is-retracted-by", "is-corrected-by")
    for key in retraction_keys:
        entries = relation.get(key) or []
        for entry in entries:
            if (entry or {}).get("id-type", "").lower() == "doi":
                return True, normalize_doi(entry.get("id", ""))
    return False, ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance"], default="relevance")
    parser.add_argument("--filter-type", help="Crossref type filter (e.g. journal-article, review-article)")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filters = []
    if args.from_year:
        filters.append(f"from-pub-date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"until-pub-date:{args.to_year}-12-31")
    if args.filter_type:
        filters.append(f"type:{args.filter_type}")
    params = {
        "query.bibliographic": args.query,
        "rows": args.limit,
        "sort": "published" if args.sort == "newest" else "relevance",
        "order": "desc",
        "select": "DOI,title,author,container-title,published-print,published-online,issued,type,abstract,URL,ISSN,subject,relation",
    }
    if filters:
        params["filter"] = ",".join(filters)
    mailto = os.getenv("CROSSREF_MAILTO")
    headers = {"User-Agent": f"{USER_AGENT}; mailto:{mailto}"} if mailto else {}

    payload = safe_request_json(API_URL, params=params, headers=headers)
    records = []
    for item in payload.get("message", {}).get("items", []):
        authors = [
            " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
            for author in item.get("author", [])
        ]
        published = (
            item.get("published-print", {}).get("date-parts")
            or item.get("published-online", {}).get("date-parts")
            or item.get("issued", {}).get("date-parts")
        )
        publication_date = parse_date(published)
        is_retracted, retraction_notice = detect_retraction(item)
        record = canonical_record(
            "Crossref",
            args.query,
            title=(item.get("title") or [""])[0],
            authors=authors,
            publication_date=publication_date,
            venue=(item.get("container-title") or [""])[0],
            issn=item.get("ISSN", []),
            doi=item.get("DOI", ""),
            article_type=clean_text(item.get("type", "")),
            abstract=strip_markup(item.get("abstract", "")),
            language=item.get("language", ""),
            subjects=item.get("subject", []),
            is_retracted=is_retracted,
            retraction_notice_doi=retraction_notice,
            source_id=item.get("URL", ""),
            raw=item,
        )
        records.append(record)
    dump_json({"source": "Crossref", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
