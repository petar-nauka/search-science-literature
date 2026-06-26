#!/usr/bin/env python3
"""Search PubMed via E-utilities and emit canonical records.

v2 improvements:
- Use NCBI_API_KEY when set (10 req/sec vs 3).
- Map pubtype list (last entry is usually the most specific type).
"""

from __future__ import annotations

import argparse
import os

from common import add_output_argument, canonical_record, dump_json, safe_request_json


SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


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
    term = args.query
    if args.from_year or args.to_year:
        start = args.from_year or 1900
        end = args.to_year or 2100
        term = f"({term}) AND ({start}:{end}[pdat])"

    api_key = os.getenv("NCBI_API_KEY")
    common_params = {"api_key": api_key} if api_key else {}

    search_payload = safe_request_json(
        SEARCH_URL,
        params={
            "db": "pubmed",
            "term": term,
            "retmax": args.limit,
            "sort": "pub_date" if args.sort == "newest" else "relevance",
            "retmode": "json",
            **common_params,
        },
    )
    ids = search_payload.get("esearchresult", {}).get("idlist", [])
    if not ids:
        dump_json({"source": "PubMed", "query": args.query, "records": []}, args.output, args.pretty)
        return
    summary_payload = safe_request_json(
        SUMMARY_URL,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json", **common_params},
    )
    records = []
    result_map = summary_payload.get("result", {})
    for uid in ids:
        item = result_map.get(uid, {})
        authors = [author.get("name", "") for author in item.get("authors", [])]
        article_ids = item.get("articleids", [])
        doi = ""
        for article_id in article_ids:
            if article_id.get("idtype") == "doi":
                doi = article_id.get("value", "")
                break
        pubtype = item.get("pubtype", [])
        article_type = pubtype[-1] if pubtype else ""

        record = canonical_record(
            "PubMed",
            args.query,
            title=item.get("title", ""),
            authors=authors,
            publication_date=item.get("pubdate", ""),
            venue=item.get("fulljournalname", ""),
            issn=[item.get("issn", ""), item.get("essn", "")],
            doi=doi,
            pmid=uid,
            article_type=article_type,
            language=(item.get("lang") or [""])[0] if isinstance(item.get("lang"), list) else item.get("lang", ""),
            source_id=uid,
            raw=item,
        )
        records.append(record)
    dump_json({"source": "PubMed", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
