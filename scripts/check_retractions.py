#!/usr/bin/env python3
"""Cross-check a record set for retractions.

Two independent signals:
1. Crossref `relation.is-retracted-by` / `is-corrected-by`.
2. OpenAlex `is_retracted` boolean.

A record is flagged if either source reports retraction.
Outputs a JSON map keyed by DOI: {doi: {is_retracted, notice_doi, sources}}.
"""

from __future__ import annotations

import argparse
import json
import time

from common import add_output_argument, dump_json, normalize_doi, safe_request_json


CROSSREF_URL = "https://api.crossref.org/works/{doi}"
OPENALEX_URL = "https://api.openalex.org/works/doi:{doi}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Merged records JSON")
    add_output_argument(parser)
    return parser.parse_args()


def load_records(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "records" in payload:
        return payload["records"]
    return payload if isinstance(payload, list) else []


def crossref_check(doi: str) -> tuple[bool, str]:
    try:
        payload = safe_request_json(CROSSREF_URL.format(doi=doi))
        relation = ((payload.get("message") or {}).get("relation")) or {}
        for key in ("is-retracted-by", "is-corrected-by"):
            entries = relation.get(key) or []
            for entry in entries:
                if (entry or {}).get("id-type", "").lower() == "doi":
                    return True, normalize_doi(entry.get("id", ""))
    except Exception:
        return False, ""
    return False, ""


def openalex_check(doi: str) -> bool:
    try:
        payload = safe_request_json(OPENALEX_URL.format(doi=doi))
        return bool(payload.get("is_retracted"))
    except Exception:
        return False


def main() -> None:
    args = parse_args()
    records = load_records(args.input)
    result: dict[str, dict] = {}
    for record in records:
        doi = normalize_doi(record.get("doi", ""))
        if not doi or doi in result:
            continue
        cr_retracted, notice = crossref_check(doi)
        oa_retracted = openalex_check(doi)
        if cr_retracted or oa_retracted:
            sources = []
            if cr_retracted:
                sources.append("Crossref")
            if oa_retracted:
                sources.append("OpenAlex")
            result[doi] = {
                "is_retracted": True,
                "notice_doi": notice,
                "sources": sources,
                "title": record.get("title", ""),
            }
        time.sleep(0.1)  # be polite

    dump_json({"retractions": result, "checked_count": len({normalize_doi(r.get('doi', '')) for r in records if r.get('doi')})}, args.output, args.pretty)


if __name__ == "__main__":
    main()
