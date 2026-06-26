#!/usr/bin/env python3
"""Run the full multi-source scholarly search pipeline.

Pipeline:
1. Expand the query (`query_expand.py`).
2. Fan out to selected sources in parallel (thread pool).
3. Merge + dedup + rank (`merge_dedup_rank.py`).
4. Cross-check retractions (`check_retractions.py`).
5. Emit a single merged JSON with audit trail.

Sources default ON:  OpenAlex, Crossref, Semantic Scholar, Europe PMC, PubMed.
Toggle flags add:    arXiv, DBLP, DOAJ, CORE, OpenAIRE, DataCite, bioRxiv.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import add_output_argument, dump_json


BASE_DIR = Path(__file__).resolve().parent


def load_module(name: str):
    path = BASE_DIR / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke_module(script_name: str, argv: list[str]) -> dict:
    """Invoke a per-source script in-process. Each call is isolated by sys.argv lock."""
    module = load_module(script_name)
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as handle:
        out_path = handle.name
    full_argv = [sys.argv[0]] + argv + ["--output", out_path]
    # sys.argv is process-global; serialize per-call via lock at the caller layer.
    original = sys.argv[:]
    try:
        sys.argv = full_argv
        module.main()
    finally:
        sys.argv = original
    try:
        with open(out_path, "r", encoding="utf-8") as h:
            return json.load(h)
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


_ARGV_LOCK = threading.Lock()


def safe_invoke(script_name: str, argv: list[str]) -> tuple[str, dict | None, str | None]:
    """Wrap invoke_module with a lock + error capture; returns (script, payload_or_None, error_str_or_None).

    Catches BaseException because argparse uses sys.exit() (SystemExit) on bad args.
    """
    try:
        with _ARGV_LOCK:
            payload = invoke_module(script_name, argv)
        return script_name, payload, None
    except SystemExit as exc:
        return script_name, None, f"SystemExit (likely argparse): code={exc.code}"
    except Exception as exc:  # noqa: BLE001
        return script_name, None, f"{type(exc).__name__}: {exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="User query in Bulgarian or English")
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--sort",
        choices=["newest", "relevance", "influence", "systematic-review"],
        default="relevance",
    )
    parser.add_argument("--expansion-mode", choices=["strict", "expanded", "exploratory"], default="expanded")
    parser.add_argument("--keyword", action="append", default=[], help="Extra keyword hint")
    parser.add_argument("--include-arxiv", action="store_true")
    parser.add_argument("--include-dblp", action="store_true")
    parser.add_argument("--include-doaj", action="store_true")
    parser.add_argument("--include-core", action="store_true")
    parser.add_argument("--include-openaire", action="store_true")
    parser.add_argument("--include-datacite", action="store_true")
    parser.add_argument("--include-biorxiv", action="store_true")
    parser.add_argument("--include-semantic-scholar", action="store_true", default=True)
    parser.add_argument("--no-semantic-scholar", action="store_true", help="Disable Semantic Scholar (e.g. when rate-limited)")
    parser.add_argument("--check-retractions", action="store_true", help="Cross-check retractions after dedup")
    parser.add_argument("--fuzzy-threshold", type=float, default=0.92)
    add_output_argument(parser)
    return parser.parse_args()


def expand(args) -> dict:
    return invoke_module(
        "query_expand.py",
        [
            "--query",
            args.query,
            "--mode",
            args.expansion_mode,
            *sum([["--keyword", value] for value in args.keyword], []),
        ],
    )


def build_search_query(expansion: dict, original: str) -> str:
    norm = expansion.get("normalized_english_query") or original
    terms = expansion.get("expanded_terms") or []
    if terms and len(terms) > 1:
        return " OR ".join(f'"{t}"' for t in terms[:6])
    return norm


def main() -> None:
    args = parse_args()
    expansion = expand(args)
    search_query = (
        expansion.get("normalized_english_query") or args.query
        if args.expansion_mode == "strict"
        else build_search_query(expansion, args.query)
    )

    sort_flag = "newest" if args.sort == "newest" else "relevance"
    # Crossref + PubMed + DOAJ + DBLP + DataCite handle plain phrase queries better than OR clauses
    plain_query = expansion.get("normalized_english_query") or args.query
    common_args = ["--query", search_query, "--limit", str(args.limit)]
    plain_args = ["--query", plain_query, "--limit", str(args.limit)]
    date_args = []
    if args.from_year:
        date_args.extend(["--from-year", str(args.from_year)])
    if args.to_year:
        date_args.extend(["--to-year", str(args.to_year)])

    def with_sort(*extra):
        return common_args + date_args + ["--sort", sort_flag] + list(extra)

    def with_sort_plain(*extra):
        return plain_args + date_args + ["--sort", sort_flag] + list(extra)

    def without_sort_plain(*extra):
        return plain_args + date_args + list(extra)

    # OpenAlex + EuropePMC + arXiv + Semantic Scholar handle OR-clause queries well.
    # Crossref + PubMed + DBLP + DOAJ + DataCite + CORE want plain phrase queries.
    jobs = [
        ("search_openalex.py", with_sort()),
        ("search_crossref.py", with_sort_plain()),
        ("search_pubmed.py", with_sort_plain()),
        ("search_europepmc.py", with_sort()),
    ]
    if args.include_semantic_scholar and not args.no_semantic_scholar:
        jobs.append(("search_semantic_scholar.py", with_sort()))
    if args.include_arxiv:
        jobs.append(("search_arxiv.py", with_sort()))
    if args.include_biorxiv:
        jobs.append(("search_biorxiv.py", with_sort_plain()))
    if args.include_dblp:
        jobs.append(("search_dblp.py", without_sort_plain()))
    if args.include_doaj:
        jobs.append(("search_doaj.py", without_sort_plain()))
    if args.include_datacite:
        jobs.append(("search_datacite.py", without_sort_plain()))
    if args.include_core:
        if os.getenv("CORE_API_KEY"):
            jobs.append(("search_core.py", without_sort_plain()))
        else:
            print("⚠ CORE skipped — set CORE_API_KEY to enable.", file=sys.stderr)
    if args.include_openaire:
        jobs.append(("search_openaire.py", ["--query", plain_query, "--limit", str(args.limit)]))

    # Fan out — bounded thread pool so we don't hammer any single host
    record_files: list[str] = []
    errors: dict[str, str] = {}
    source_hits: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        futures = [pool.submit(safe_invoke, name, argv) for name, argv in jobs]
        for fut in as_completed(futures):
            script_name, payload, err = fut.result()
            source_label = script_name.replace("search_", "").replace(".py", "")
            if err:
                errors[source_label] = err
                continue
            recs = payload.get("records", []) if isinstance(payload, dict) else []
            source_hits[source_label] = len(recs)
            with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
                record_files.append(handle.name)

    # Merge + rank
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as handle:
        merged_path = handle.name
    merge_argv = [*record_files, "--sort", args.sort, "--query", args.query, "--fuzzy-threshold", str(args.fuzzy_threshold), "--output", merged_path]
    with _ARGV_LOCK:
        original = sys.argv[:]
        try:
            sys.argv = [sys.argv[0]] + merge_argv
            load_module("merge_dedup_rank.py").main()
        finally:
            sys.argv = original
    with open(merged_path, "r", encoding="utf-8") as h:
        merged = json.load(h)

    # Optional retraction cross-check
    if args.check_retractions:
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as handle:
            retraction_path = handle.name
        with _ARGV_LOCK:
            original = sys.argv[:]
            try:
                sys.argv = [sys.argv[0], merged_path, "--output", retraction_path]
                load_module("check_retractions.py").main()
            finally:
                sys.argv = original
        with open(retraction_path, "r", encoding="utf-8") as h:
            retraction_data = json.load(h)
        retraction_map = retraction_data.get("retractions", {})
        for record in merged.get("records", []):
            doi = (record.get("doi") or "").lower()
            if doi in retraction_map:
                record["is_retracted"] = True
                record["retraction_notice_doi"] = retraction_map[doi].get("notice_doi", "")
                # Recompute total score with penalty
                scores = record.get("scores") or {}
                # If we already applied the penalty during scoring, skip; otherwise apply now
                if scores.get("_retraction_applied") is None:
                    scores["total"] = scores.get("total", 0) - 5
                    scores["_retraction_applied"] = True
                    record["scores"] = scores

    # Audit trail
    merged["original_query"] = args.query
    merged["normalized_english_query"] = expansion.get("normalized_english_query", "")
    merged["expanded_terms"] = expansion.get("expanded_terms", [])
    merged["search_query_used"] = search_query
    merged["source_hits"] = source_hits
    merged["source_errors"] = errors
    merged["date_range"] = {"from": args.from_year, "to": args.to_year}
    merged["expansion_mode"] = args.expansion_mode

    # Cleanup tmp files
    for path in record_files:
        try:
            os.unlink(path)
        except OSError:
            pass

    dump_json(merged, args.output, args.pretty)


if __name__ == "__main__":
    main()
