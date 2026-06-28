#!/usr/bin/env python3
"""Shared helpers for scholarly literature retrieval scripts.

Improvements over v1:
- OpenAlex `abstract_inverted_index` reconstruction.
- JATS/HTML markup stripping for Crossref abstracts.
- Fuzzy title similarity for deduplication.
- ISSN normalization.
- Richer canonical record schema (issn, arxiv_id, license, concepts, is_retracted, tldr).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT = 30
USER_AGENT = "ScientificLiteratureSkill/2.0 (https://github.com/anthropics/skills; mailto:petar@nauka.bg)"


# ------------------------- text helpers ------------------------- #

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(part) for part in value if part)
    text = str(value)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(value: str) -> str:
    lowered = clean_text(value).lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def strip_markup(value: str) -> str:
    """Strip JATS/XML/HTML tags from text (used for Crossref abstracts)."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return clean_text(text)


def reconstruct_inverted_index(index: dict | None) -> str:
    """Convert OpenAlex abstract_inverted_index back into plain text."""
    if not index or not isinstance(index, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for token, positions in index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                positioned.append((pos, token))
    positioned.sort(key=lambda item: item[0])
    return clean_text(" ".join(token for _, token in positioned))


def title_similarity(a: str, b: str) -> float:
    """Fuzzy title similarity in [0, 1]."""
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(a=na, b=nb).ratio()


# ------------------------- identifier helpers ------------------------- #

def normalize_doi(value: str) -> str:
    doi = clean_text(value).lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi.strip()


def maybe_doi_url(doi: str) -> str:
    doi = normalize_doi(doi)
    return f"https://doi.org/{doi}" if doi else ""


def normalize_issn(value: Any) -> list[str]:
    """Return a list of cleaned ISSNs (XXXX-XXXX, uppercase)."""
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    out: list[str] = []
    for entry in value:
        cleaned = re.sub(r"[^0-9Xx]", "", str(entry)).upper()
        if len(cleaned) == 8:
            out.append(f"{cleaned[:4]}-{cleaned[4:]}")
    return out


def parse_date_to_year(value: str) -> int | None:
    value = clean_text(value)
    match = re.search(r"(19|20)\d{2}", value)
    return int(match.group(0)) if match else None


# ------------------------- HTTP helpers ------------------------- #

def fetch_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    request_headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, headers=request_headers, method=method, data=data)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")


def safe_request_json(*args: Any, retries: int = 2, sleep_seconds: float = 1.0, **kwargs: Any) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch_json(*args, **kwargs)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(sleep_seconds * (attempt + 1))
    raise RuntimeError(f"Request failed after retries: {last_error}") from last_error


def safe_request_text(*args: Any, retries: int = 2, sleep_seconds: float = 1.0, **kwargs: Any) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch_text(*args, **kwargs)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(sleep_seconds * (attempt + 1))
    raise RuntimeError(f"Request failed after retries: {last_error}") from last_error


def load_dotenv(paths: list[str | Path] | None = None) -> None:
    """Load KEY=VALUE pairs from .env files without overriding existing env vars."""
    candidate_paths = paths or [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path_value in candidate_paths:
        path = Path(path_value).expanduser()
        if not path.exists() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# ------------------------- author helpers ------------------------- #

def make_author_list(names: list[Any]) -> list[str]:
    out: list[str] = []
    for name in names or []:
        if isinstance(name, dict):
            name = name.get("name") or " ".join(
                part for part in [name.get("given", ""), name.get("family", "")] if part
            )
        cleaned = clean_text(name)
        if cleaned:
            out.append(cleaned)
    return out


# ------------------------- canonical record ------------------------- #

def canonical_record(
    source: str,
    query: str,
    *,
    title: str = "",
    authors: list | None = None,
    year: int | None = None,
    publication_date: str = "",
    venue: str = "",
    issn: list[str] | None = None,
    doi: str = "",
    pmid: str = "",
    pmcid: str = "",
    arxiv_id: str = "",
    article_type: str = "",
    abstract: str = "",
    tldr: str = "",
    citations: int | None = None,
    influential_citations: int | None = None,
    is_oa: bool | None = None,
    oa_url: str = "",
    license: str = "",
    peer_review_status: str = "",
    language: str = "",
    concepts: list[str] | None = None,
    subjects: list[str] | None = None,
    is_retracted: bool = False,
    retraction_notice_doi: str = "",
    source_id: str = "",
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned_authors = make_author_list(authors or [])
    normalized_doi = normalize_doi(doi)
    record_year = year if year is not None else parse_date_to_year(publication_date)
    return {
        "title": clean_text(title),
        "authors": cleaned_authors,
        "first_author": cleaned_authors[0] if cleaned_authors else "",
        "year": record_year,
        "publication_date": clean_text(publication_date),
        "venue": clean_text(venue),
        "issn": normalize_issn(issn or []),
        "doi": normalized_doi,
        "doi_url": maybe_doi_url(normalized_doi),
        "pmid": clean_text(pmid),
        "pmcid": clean_text(pmcid),
        "arxiv_id": clean_text(arxiv_id),
        "article_type": clean_text(article_type),
        "abstract": clean_text(abstract),
        "tldr": clean_text(tldr),
        "source_databases": [source],
        "source_ids": {source: clean_text(source_id)} if source_id else {},
        "citations": citations,
        "influential_citations": influential_citations,
        "is_oa": is_oa,
        "oa_url": clean_text(oa_url),
        "license": clean_text(license),
        "peer_review_status": clean_text(peer_review_status),
        "language": clean_text(language),
        "concepts": [clean_text(c) for c in (concepts or []) if c],
        "subjects": [clean_text(s) for s in (subjects or []) if s],
        "is_retracted": bool(is_retracted),
        "retraction_notice_doi": normalize_doi(retraction_notice_doi),
        "query": clean_text(query),
        "raw": raw or {},
    }


# ------------------------- CLI / IO helpers ------------------------- #

def add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")


def dump_json(data: Any, output: str | None = None, pretty: bool = False) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        try:
            sys.stdout.write(payload)
            if pretty:
                sys.stdout.write("\n")
        except UnicodeEncodeError:
            encoded = payload.encode("utf-8")
            if pretty:
                encoded += b"\n"
            sys.stdout.buffer.write(encoded)
