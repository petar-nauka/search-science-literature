#!/usr/bin/env python3
"""Search Web of Science Starter API and emit canonical records.

Requires WOS_STARTER_API_KEY. This is an optional credentialed source for
metadata validation, DOI lookup, author/source-title checks, and times-cited
counts when the subscribed plan exposes them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    add_output_argument,
    canonical_record,
    clean_text,
    dump_json,
    load_dotenv,
    normalize_doi,
    safe_request_json,
)


SOURCE_NAME = "WebOfScienceStarter"
BASE_URL = "https://api.clarivate.com/apis/wos-starter/{version}/documents"
FIELD_TAG_RE = re.compile(r"(^|[\s(])(AU|DO|IS|OG|PY|SO|SU|TI|TS|UT)\s*=", re.IGNORECASE)
MONTHS = {
    "JAN": "01",
    "FEB": "02",
    "MAR": "03",
    "APR": "04",
    "MAY": "05",
    "JUN": "06",
    "JUL": "07",
    "AUG": "08",
    "SEP": "09",
    "OCT": "10",
    "NOV": "11",
    "DEC": "12",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Plain topic query or Web of Science advanced query")
    parser.add_argument("--doi", help="DOI lookup; builds DO=<doi>")
    parser.add_argument("--author", help="Author filter; builds AU=(...)")
    parser.add_argument("--source-title", help="Source title filter; builds SO=(...)")
    parser.add_argument("--field-tag", default="TS", help="WoS field tag for plain --query values")
    parser.add_argument("--raw-query", action="store_true", help="Send --query exactly as the q parameter")
    parser.add_argument("--db", default="WOS", help="WoS database, e.g. WOS, BCI, DIIDW, MEDLINE, PPRN")
    parser.add_argument("--api-version", choices=["v1", "v2"], default=os.getenv("WOS_STARTER_API_VERSION", "v1"))
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--sort", choices=["newest", "relevance", "cited"], default="relevance")
    parser.add_argument("--cache-ttl-hours", type=float, default=24.0)
    parser.add_argument("--no-cache", action="store_true")
    add_output_argument(parser)
    return parser.parse_args()


def build_query(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.doi:
        parts.append(f"DO={normalize_doi(args.doi)}")
    if args.author:
        parts.append(f"AU=({clean_text(args.author)})")
    if args.source_title:
        parts.append(f"SO=({clean_text(args.source_title)})")
    if args.query:
        query = clean_text(args.query)
        if args.raw_query or FIELD_TAG_RE.search(query):
            parts.append(query)
        else:
            tag = re.sub(r"[^A-Za-z]", "", args.field_tag).upper() or "TS"
            parts.append(f"{tag}=({query})")
    if not parts:
        raise SystemExit("Provide --query, --doi, --author, or --source-title.")
    return " AND ".join(parts)


def publish_timespan(args: argparse.Namespace) -> str:
    if not args.from_year and not args.to_year:
        return ""
    start = args.from_year or 1900
    end = args.to_year or datetime.utcnow().year
    return f"{start}-01-01+{end}-12-31"


def cache_dir() -> Path:
    configured = os.getenv("WOS_STARTER_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "search-science-literature" / "wos-starter"


def cache_key(url: str, params: dict[str, Any]) -> str:
    raw = json.dumps({"url": url, "params": params}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_cache(path: Path, ttl_hours: float) -> Any | None:
    if not path.exists():
        return None
    if ttl_hours >= 0:
        age_seconds = time.time() - path.stat().st_mtime
        if age_seconds > ttl_hours * 3600:
            return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_cache(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def fetch_page(url: str, params: dict[str, Any], headers: dict[str, str], args: argparse.Namespace) -> tuple[Any, bool]:
    path = cache_dir() / f"{cache_key(url, params)}.json"
    if not args.no_cache:
        cached = read_cache(path, args.cache_ttl_hours)
        if cached is not None:
            return cached, True
    payload = safe_request_json(url, params=params, headers=headers, retries=2, sleep_seconds=1.0)
    if not args.no_cache:
        write_cache(path, payload)
    return payload, False


def get_nested(item: dict[str, Any], *keys: str) -> Any:
    cur: Any = item
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def author_names(item: dict[str, Any]) -> list[str]:
    authors = get_nested(item, "names", "authors") or []
    out: list[str] = []
    for author in listify(authors):
        if not isinstance(author, dict):
            continue
        name = author.get("displayName") or author.get("wosStandard") or author.get("fullName")
        if name:
            out.append(clean_text(name))
    return out


def publication_date(item: dict[str, Any]) -> str:
    source = item.get("source") or {}
    year = clean_text(source.get("publishYear"))
    if not year:
        return ""
    month = clean_text(source.get("publishMonth")).upper()
    if month.isdigit():
        return f"{year}-{month.zfill(2)[:2]}"
    if month[:3] in MONTHS:
        return f"{year}-{MONTHS[month[:3]]}"
    return year


def citation_count(item: dict[str, Any]) -> int | None:
    counts: list[int] = []
    for entry in listify(item.get("citations")):
        if not isinstance(entry, dict):
            continue
        value = entry.get("count")
        try:
            counts.append(int(value))
        except (TypeError, ValueError):
            continue
    return max(counts) if counts else None


def identifiers(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("identifiers") or {}
    return value if isinstance(value, dict) else {}


def keyword_values(item: dict[str, Any]) -> list[str]:
    keywords = item.get("keywords") or {}
    if not isinstance(keywords, dict):
        return []
    values: list[str] = []
    for key in ("authorKeywords", "keywordsPlus"):
        for entry in listify(keywords.get(key)):
            cleaned = clean_text(entry)
            if cleaned:
                values.append(cleaned)
    return values


def record_from_hit(item: dict[str, Any], query: str) -> dict[str, Any]:
    source = item.get("source") or {}
    ids = identifiers(item)
    types = [clean_text(value) for value in listify(item.get("types")) if clean_text(value)]
    article_type = "; ".join(types)
    issn = [ids.get("issn", ""), ids.get("eissn", "")]

    return canonical_record(
        SOURCE_NAME,
        query,
        title=item.get("title", ""),
        authors=author_names(item),
        year=int(source["publishYear"]) if str(source.get("publishYear", "")).isdigit() else None,
        publication_date=publication_date(item),
        venue=source.get("sourceTitle", ""),
        issn=issn,
        doi=ids.get("doi", ""),
        pmid=ids.get("pmid", ""),
        article_type=article_type,
        citations=citation_count(item),
        concepts=keyword_values(item),
        source_id=item.get("uid", ""),
        raw=item,
    )


def extract_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits = payload.get("hits")
    if isinstance(hits, list):
        return [hit for hit in hits if isinstance(hit, dict)]
    return []


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.getenv("WOS_STARTER_API_KEY")
    if not api_key:
        raise SystemExit("Set WOS_STARTER_API_KEY to use Web of Science Starter API.")

    query = build_query(args)
    url = BASE_URL.format(version=args.api_version)
    headers = {"X-ApiKey": api_key, "Accept": "application/json"}
    sort_field = {"newest": "PY+D", "relevance": "RS+D", "cited": "TC+D"}[args.sort]
    timespan = publish_timespan(args)

    records: list[dict[str, Any]] = []
    cached_pages = 0
    page = max(1, args.page)
    max_pages = max(1, args.max_pages)
    metadata: dict[str, Any] = {}

    for index in range(max_pages):
        params: dict[str, Any] = {
            "db": args.db,
            "q": query,
            "limit": min(max(args.limit, 1), 50),
            "page": page + index,
            "sortField": sort_field,
        }
        if timespan:
            params["publishTimeSpan"] = timespan
        payload, cached = fetch_page(url, params, headers, args)
        cached_pages += int(cached)
        if isinstance(payload, dict):
            metadata = payload.get("metadata") or metadata
            records.extend(record_from_hit(item, query) for item in extract_hits(payload))
        if not cached and index < max_pages - 1:
            time.sleep(1.0)

    dump_json(
        {
            "source": SOURCE_NAME,
            "query": query,
            "records": records,
            "metadata": metadata,
            "cached_pages": cached_pages,
        },
        args.output,
        args.pretty,
    )


if __name__ == "__main__":
    main()
