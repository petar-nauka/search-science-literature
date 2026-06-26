#!/usr/bin/env python3
"""Search Europe PMC and emit canonical records.

v2 improvements:
- Pick the best OA URL from `fullTextUrlList.fullTextUrl[]` (prefer HTML > PDF, OA > S, EuropePMC > PUBMED).
- Detect preprint sources (SRC:PPR) and set peer_review_status correctly.
- Optional --preprints-only filter.
"""

from __future__ import annotations

import argparse

from common import add_output_argument, canonical_record, dump_json, safe_request_json


API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def pick_oa_url(item: dict) -> str:
    """Choose the best open-access URL from Europe PMC's fullTextUrlList."""
    urls = ((item.get("fullTextUrlList") or {}).get("fullTextUrl") or [])
    if not urls:
        return ""

    def score(entry: dict) -> int:
        s = 0
        if (entry.get("availability", "").lower() in ("open access", "free")):
            s += 4
        if entry.get("documentStyle", "").lower() == "html":
            s += 2
        if entry.get("documentStyle", "").lower() == "pdf":
            s += 1
        if "europepmc.org" in entry.get("url", "").lower():
            s += 1
        return s

    best = max(urls, key=score)
    return best.get("url", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance"], default="relevance")
    parser.add_argument("--preprints-only", action="store_true", help="Filter to SRC:PPR (bioRxiv/medRxiv/chemRxiv)")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    query = args.query
    if args.preprints_only:
        query = f"({query}) AND SRC:PPR"
    if args.from_year or args.to_year:
        start = args.from_year or 1900
        end = args.to_year or 2100
        query = f"({query}) AND PUB_YEAR:[{start} TO {end}]"
    payload = safe_request_json(
        API_URL,
        params={
            "query": query,
            "pageSize": args.limit,
            "sort": "DATE_DESC" if args.sort == "newest" else "",
            "format": "json",
            "resultType": "core",
        },
    )
    records = []
    for item in payload.get("resultList", {}).get("result", []):
        authors = [name.strip() for name in (item.get("authorString", "") or "").split(",") if name.strip()]
        source_db = (item.get("source") or "").upper()
        is_preprint = source_db == "PPR"
        record = canonical_record(
            "EuropePMC",
            args.query,
            title=item.get("title", ""),
            authors=authors,
            year=int(item.get("pubYear")) if str(item.get("pubYear", "")).isdigit() else None,
            publication_date=item.get("firstPublicationDate", "") or item.get("pubYear", ""),
            venue=item.get("journalTitle", "") or item.get("bookOrReportDetails", {}).get("publisher", ""),
            doi=item.get("doi", ""),
            pmid=item.get("pmid", ""),
            pmcid=item.get("pmcid", ""),
            article_type=item.get("pubType", "") if not is_preprint else "preprint",
            abstract=item.get("abstractText", ""),
            citations=int(item.get("citedByCount")) if str(item.get("citedByCount", "")).isdigit() else None,
            is_oa=(item.get("isOpenAccess") == "Y") or is_preprint,
            oa_url=pick_oa_url(item),
            peer_review_status="preprint" if is_preprint else "peer-reviewed",
            language=item.get("language", ""),
            source_id=item.get("id", ""),
            raw=item,
        )
        records.append(record)
    dump_json({"source": "EuropePMC", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
