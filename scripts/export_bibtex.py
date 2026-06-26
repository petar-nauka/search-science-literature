#!/usr/bin/env python3
"""Export merged records to BibTeX."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Merged records JSON")
    parser.add_argument("--output", help="Write BibTeX to this file")
    parser.add_argument("--limit", type=int, default=0, help="0 = all")
    return parser.parse_args()


def slugify(value: str) -> str:
    if not value:
        return "anon"
    norm = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^A-Za-z0-9]+", "", norm)
    return norm or "anon"


def cite_key(record: dict) -> str:
    first = record.get("first_author") or (record.get("authors") or [""])[0]
    last_name = first.split(",")[0].split(" ")[-1] if first else "anon"
    year = record.get("year") or "n.d."
    title_words = (record.get("title") or "").split()
    title_slug = slugify(title_words[0]) if title_words else ""
    return f"{slugify(last_name).lower()}{year}{title_slug.lower()}"


def field(name: str, value: str | None) -> str:
    if value in (None, "", []):
        return ""
    safe = str(value).replace("{", "(").replace("}", ")")
    return f"  {name} = {{{safe}}},\n"


def entry_type(article_type: str) -> str:
    at = (article_type or "").lower()
    if "preprint" in at:
        return "@misc"
    if "review" in at:
        return "@article"
    if "dataset" in at:
        return "@dataset"
    if "software" in at:
        return "@software"
    if "book" in at:
        return "@book"
    if "conference" in at or "proceedings" in at:
        return "@inproceedings"
    return "@article"


def format_entry(record: dict) -> str:
    key = cite_key(record)
    lines = [f"{entry_type(record.get('article_type', ''))}{{{key},\n"]
    authors_field = " and ".join(record.get("authors") or [])
    lines.append(field("author", authors_field))
    lines.append(field("title", record.get("title")))
    lines.append(field("journal", record.get("venue")))
    lines.append(field("year", record.get("year")))
    lines.append(field("doi", record.get("doi")))
    lines.append(field("url", record.get("doi_url") or record.get("oa_url")))
    lines.append(field("note", "RETRACTED" if record.get("is_retracted") else None))
    lines.append("}\n")
    return "".join(lines)


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if args.limit:
        records = records[: args.limit]
    output_lines = [format_entry(r) for r in records]
    bibtex = "\n".join(output_lines)
    if args.output:
        Path(args.output).write_text(bibtex, encoding="utf-8")
    else:
        print(bibtex)


if __name__ == "__main__":
    main()
