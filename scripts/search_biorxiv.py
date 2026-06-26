#!/usr/bin/env python3
"""Search bioRxiv / medRxiv / chemRxiv preprints.

Uses Europe PMC with `SRC:PPR` for keyword search (their primary index)
because the bioRxiv direct API is DOI-keyed, not keyword-search.

For per-DOI metadata lookup, see `--doi` mode (hits api.biorxiv.org).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import add_output_argument, canonical_record, dump_json, safe_request_json


BIORXIV_URL = "https://api.biorxiv.org/details/biorxiv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Keyword query (proxied through Europe PMC SRC:PPR)")
    parser.add_argument("--doi", help="Look up a single bioRxiv DOI")
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--sort", choices=["newest", "relevance"], default="newest")
    add_output_argument(parser)
    return parser.parse_args()


def lookup_doi(doi: str, query: str) -> list[dict]:
    payload = safe_request_json(f"{BIORXIV_URL}/{doi}")
    out = []
    for entry in payload.get("collection", []):
        out.append(
            canonical_record(
                "bioRxiv",
                query or doi,
                title=entry.get("title", ""),
                authors=[a.strip() for a in (entry.get("authors") or "").split(";") if a.strip()],
                year=int(entry.get("date", "")[:4]) if entry.get("date") else None,
                publication_date=entry.get("date", ""),
                venue=entry.get("server", "bioRxiv"),
                doi=entry.get("doi", ""),
                article_type="preprint",
                abstract=entry.get("abstract", ""),
                is_oa=True,
                oa_url=f"https://doi.org/{entry.get('doi', '')}",
                peer_review_status="preprint",
                concepts=[entry.get("category", "")] if entry.get("category") else [],
                source_id=entry.get("doi", ""),
                raw=entry,
            )
        )
    return out


def keyword_via_epmc(args) -> list[dict]:
    """Delegate keyword search to search_europepmc.py with --preprints-only."""
    import json
    import tempfile

    script = Path(__file__).resolve().parent / "search_europepmc.py"
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as handle:
        tmp_path = handle.name
    argv = [sys.executable, str(script), "--query", args.query, "--preprints-only", "--limit", str(args.limit), "--sort", args.sort, "--output", tmp_path]
    if args.from_year:
        argv.extend(["--from-year", str(args.from_year)])
    if args.to_year:
        argv.extend(["--to-year", str(args.to_year)])
    subprocess.run(argv, check=True)
    with open(tmp_path, "r", encoding="utf-8") as h:
        payload = json.load(h)
    for r in payload.get("records", []):
        # rebrand the source name so the audit trail is accurate
        if "EuropePMC" in r.get("source_databases", []):
            r["source_databases"] = ["bioRxiv-via-EPMC"]
    return payload.get("records", [])


def main() -> None:
    args = parse_args()
    if args.doi:
        records = lookup_doi(args.doi, args.query or "")
    elif args.query:
        records = keyword_via_epmc(args)
    else:
        raise SystemExit("Provide --query or --doi")
    dump_json({"source": "bioRxiv", "query": args.query or args.doi, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
