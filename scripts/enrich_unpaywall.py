#!/usr/bin/env python3
"""Enrich DOI records with open-access locations from Unpaywall."""

from __future__ import annotations

import argparse
import os

from common import add_output_argument, dump_json, normalize_doi, safe_request_json


API_URL = "https://api.unpaywall.org/v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doi", action="append", required=True, help="DOI to enrich")
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    email = os.getenv("UNPAYWALL_EMAIL", "anonymous@example.invalid")
    results = []
    for doi in args.doi:
        normalized = normalize_doi(doi)
        payload = safe_request_json(f"{API_URL}/{normalized}", params={"email": email})
        best = payload.get("best_oa_location") or {}
        results.append(
            {
                "doi": normalized,
                "is_oa": payload.get("is_oa"),
                "oa_url": best.get("url", ""),
                "landing_page_url": best.get("url_for_landing_page", ""),
                "host_type": best.get("host_type", ""),
                "license": best.get("license", ""),
                "source": "Unpaywall",
            }
        )
    dump_json({"source": "Unpaywall", "results": results}, args.output, args.pretty)


if __name__ == "__main__":
    main()
