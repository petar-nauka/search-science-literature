#!/usr/bin/env python3
"""Export merged records to CSV (Excel / Sheets-friendly)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


COLUMNS = [
    "#",
    "title",
    "first_author",
    "authors",
    "year",
    "publication_date",
    "venue",
    "doi",
    "doi_url",
    "pmid",
    "pmcid",
    "arxiv_id",
    "article_type",
    "abstract",
    "tldr",
    "citations",
    "influential_citations",
    "is_oa",
    "oa_url",
    "license",
    "peer_review_status",
    "language",
    "concepts",
    "subjects",
    "source_databases",
    "is_retracted",
    "retraction_notice_doi",
    "scores.total",
    "scores.relevance",
    "scores.evidence",
    "scores.metadata",
    "scores.influence",
    "scores.recency",
]


def flatten(record: dict, idx: int) -> dict:
    out = {"#": idx}
    for col in COLUMNS[1:]:
        if col.startswith("scores."):
            scores = record.get("scores") or {}
            out[col] = scores.get(col.split(".", 1)[1])
        else:
            value = record.get(col)
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            out[col] = value
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Merged records JSON")
    parser.add_argument("--output", help="Write CSV to this file")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if args.limit:
        records = records[: args.limit]

    target = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(target, fieldnames=COLUMNS)
        writer.writeheader()
        for idx, record in enumerate(records, start=1):
            writer.writerow(flatten(record, idx))
    finally:
        if args.output:
            target.close()


if __name__ == "__main__":
    main()
