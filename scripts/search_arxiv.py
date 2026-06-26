#!/usr/bin/env python3
"""Search arXiv via its Atom XML API.

Treats every result as a preprint (peer_review_status = "preprint").

API doc: https://info.arxiv.org/help/api/user-manual.html
"""

from __future__ import annotations

import argparse
import re
import time
import xml.etree.ElementTree as ET

from common import add_output_argument, canonical_record, dump_json, safe_request_text


API_URL = "http://export.arxiv.org/api/query"
ATOM = "http://www.w3.org/2005/Atom"
ARXIV = "http://arxiv.org/schemas/atom"


def _t(node, tag):
    el = node.find(f"{{{ATOM}}}{tag}")
    return el.text.strip() if el is not None and el.text else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance"], default="relevance")
    add_output_argument(parser)
    return parser.parse_args()


def build_search(query: str, from_year, to_year) -> str:
    parts = [f'all:"{query}"' if " " in query else f"all:{query}"]
    if from_year or to_year:
        start = f"{from_year}01010000" if from_year else "190001010000"
        end = f"{to_year}12312359" if to_year else "210012312359"
        parts.append(f"submittedDate:[{start} TO {end}]")
    return " AND ".join(parts)


def main() -> None:
    args = parse_args()
    # Be polite — arXiv asks for ~1 req per 3 seconds.
    time.sleep(1)

    params = {
        "search_query": build_search(args.query, args.from_year, args.to_year),
        "start": 0,
        "max_results": min(args.limit, 100),
        "sortBy": "submittedDate" if args.sort == "newest" else "relevance",
        "sortOrder": "descending",
    }
    xml_text = safe_request_text(API_URL, params=params, sleep_seconds=3.0)
    root = ET.fromstring(xml_text)
    records = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        arxiv_url = _t(entry, "id")
        arxiv_id = re.sub(r"^https?://arxiv\.org/abs/", "", arxiv_url)
        authors = [
            (a.findtext(f"{{{ATOM}}}name") or "").strip()
            for a in entry.findall(f"{{{ATOM}}}author")
        ]
        doi_el = entry.find(f"{{{ARXIV}}}doi")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else ""
        categories = [
            (c.attrib.get("term") or "").strip()
            for c in entry.findall(f"{{{ATOM}}}category")
        ]
        record = canonical_record(
            "arXiv",
            args.query,
            title=_t(entry, "title"),
            authors=authors,
            publication_date=_t(entry, "published")[:10],
            venue="arXiv",
            doi=doi,
            arxiv_id=arxiv_id,
            article_type="preprint",
            abstract=_t(entry, "summary"),
            is_oa=True,
            oa_url=arxiv_url,
            peer_review_status="preprint",
            concepts=categories,
            source_id=arxiv_id,
            raw={"arxiv_id": arxiv_id, "categories": categories},
        )
        records.append(record)
    dump_json({"source": "arXiv", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
