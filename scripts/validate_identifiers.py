#!/usr/bin/env python3
"""Validate DOI and PMID fields inside canonical record files."""

from __future__ import annotations

import argparse
import json
import re

from common import add_output_argument, clean_text, dump_json, normalize_doi


DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="JSON files containing canonical records")
    add_output_argument(parser)
    return parser.parse_args()


def load_records(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("records", payload if isinstance(payload, list) else [])


def main() -> None:
    args = parse_args()
    results = []
    for path in args.inputs:
        for record in load_records(path):
            doi = normalize_doi(record.get("doi", ""))
            pmid = clean_text(record.get("pmid", ""))
            results.append(
                {
                    "title": record.get("title", ""),
                    "doi": doi,
                    "doi_valid": bool(doi and DOI_RE.match(doi)),
                    "pmid": pmid,
                    "pmid_valid": bool(pmid.isdigit()),
                    "venue": record.get("venue", ""),
                    "source_databases": record.get("source_databases", []),
                }
            )
    dump_json({"validation": results}, args.output, args.pretty)


if __name__ == "__main__":
    main()
