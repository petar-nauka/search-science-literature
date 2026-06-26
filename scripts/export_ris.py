#!/usr/bin/env python3
"""Export merged records to RIS (EndNote/Zotero/Mendeley)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Merged records JSON")
    parser.add_argument("--output", help="Write RIS to this file")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def ris_type(article_type: str) -> str:
    at = (article_type or "").lower()
    if "preprint" in at:
        return "UNPB"
    if "review" in at:
        return "JOUR"
    if "book" in at:
        return "BOOK"
    if "conference" in at or "proceedings" in at:
        return "CPAPER"
    if "dataset" in at:
        return "DATA"
    if "software" in at:
        return "COMP"
    return "JOUR"


def format_entry(record: dict) -> str:
    lines = [f"TY  - {ris_type(record.get('article_type', ''))}"]
    for author in record.get("authors") or []:
        lines.append(f"AU  - {author}")
    if record.get("title"):
        lines.append(f"TI  - {record['title']}")
    if record.get("year"):
        lines.append(f"PY  - {record['year']}")
    if record.get("publication_date"):
        lines.append(f"DA  - {record['publication_date']}")
    if record.get("venue"):
        lines.append(f"JO  - {record['venue']}")
    if record.get("doi"):
        lines.append(f"DO  - {record['doi']}")
    if record.get("doi_url") or record.get("oa_url"):
        lines.append(f"UR  - {record.get('doi_url') or record.get('oa_url')}")
    if record.get("abstract"):
        lines.append(f"AB  - {record['abstract']}")
    if record.get("is_retracted"):
        lines.append("N1  - RETRACTED")
    lines.append("ER  - ")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if args.limit:
        records = records[: args.limit]
    output = "\n\n".join(format_entry(r) for r in records)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
