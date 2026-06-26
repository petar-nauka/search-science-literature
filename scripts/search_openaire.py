#!/usr/bin/env python3
"""Search OpenAIRE publications and emit canonical records."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET

from common import add_output_argument, canonical_record, dump_json, fetch_text


API_URL = "https://api.openaire.eu/search/publications"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=25)
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    xml_text = fetch_text(
        API_URL,
        params={"keywords": args.query, "size": args.limit},
        headers={"Accept": "application/xml"},
    )
    root = ET.fromstring(xml_text)
    records = []
    ns = {
        "oaf": "http://namespace.openaire.eu/oaf",
        "dr": "http://www.driver-repository.eu/namespace/dri",
    }
    for result in root.findall(".//oaf:result", ns):
        title = result.findtext(".//dr:title", default="", namespaces=ns)
        date = result.findtext(".//dr:dateofacceptance", default="", namespaces=ns)
        publisher = result.findtext(".//dr:publisher", default="", namespaces=ns)
        authors = [elem.text or "" for elem in result.findall(".//dr:creator", ns)]
        doi = ""
        for identifier in result.findall(".//dr:pid", ns):
            if (identifier.text or "").lower().startswith("10."):
                doi = identifier.text or ""
                break
        oa_url = result.findtext(".//dr:webresource", default="", namespaces=ns)
        record = canonical_record(
            "OpenAIRE",
            args.query,
            title=title,
            authors=authors,
            publication_date=date,
            venue=publisher,
            doi=doi,
            is_oa=bool(oa_url),
            oa_url=oa_url,
            raw={"xml_title": title},
        )
        records.append(record)
    dump_json({"source": "OpenAIRE", "query": args.query, "records": records}, args.output, args.pretty)


if __name__ == "__main__":
    main()
