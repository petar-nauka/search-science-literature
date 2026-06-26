#!/usr/bin/env python3
"""Build Markdown tables for newest-first or review-style outputs."""

from __future__ import annotations

import argparse
import json

from common import clean_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Merged records JSON")
    parser.add_argument("--mode", choices=["newest", "review"], default="review")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--output", help="Write markdown to this file")
    return parser.parse_args()


def load_records(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("records", [])


def cell(value: object) -> str:
    text = clean_text(value)
    return text.replace("|", "\\|")


def newest_table(records: list[dict], limit: int) -> str:
    lines = [
        "| # | Publication Date | Title | First Author | Venue | DOI | Type | Source | OA |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for index, record in enumerate(records[:limit], start=1):
        lines.append(
            "| {idx} | {date} | {title} | {author} | {venue} | {doi} | {type_} | {source} | {oa} |".format(
                idx=index,
                date=cell(record.get("publication_date") or record.get("year")),
                title=cell(record.get("title")),
                author=cell(record.get("first_author")),
                venue=cell(record.get("venue")),
                doi=cell(record.get("doi")),
                type_=cell(record.get("article_type")),
                source=cell(", ".join(record.get("source_databases", []))),
                oa=cell(record.get("oa_url")),
            )
        )
    return "\n".join(lines)


def review_table(records: list[dict], limit: int) -> str:
    lines = [
        "| # | Authors | Year | Publication Date | Title | Journal or Venue | DOI | Article Type | Source Databases | Open Access Link |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for index, record in enumerate(records[:limit], start=1):
        lines.append(
            "| {idx} | {authors} | {year} | {date} | {title} | {venue} | {doi} | {type_} | {source} | {oa} |".format(
                idx=index,
                authors=cell(", ".join(record.get("authors", []))),
                year=cell(record.get("year")),
                date=cell(record.get("publication_date")),
                title=cell(record.get("title")),
                venue=cell(record.get("venue")),
                doi=cell(record.get("doi")),
                type_=cell(record.get("article_type")),
                source=cell(", ".join(record.get("source_databases", []))),
                oa=cell(record.get("oa_url")),
            )
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    records = load_records(args.input)
    markdown = newest_table(records, args.limit) if args.mode == "newest" else review_table(records, args.limit)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
