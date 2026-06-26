#!/usr/bin/env python3
"""Normalize and expand scientific search queries, including Bulgarian input."""

from __future__ import annotations

import argparse
import re
from typing import Any

from common import add_output_argument, clean_text, dump_json


PATTERN_MAP = [
    (r"\b\u0437\u0435\u043b\u0435\u043d(?:\u0438\u044f\u0442|\u0438\u044f|\u0438|\u0430|\u043e)?\s+\u0432\u043e\u0434\u043e\u0440\u043e\u0434\b", ["green hydrogen", "renewable hydrogen"]),
    (r"\b\u0432\u043e\u0434\u043e\u0440\u043e\u0434(?:\u044a\u0442|\u0430|\u0438)?\b", ["hydrogen"]),
    (r"\bpem\s+\u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043b\u0438\u0437\w*\b", ["PEM electrolysis", "proton exchange membrane electrolysis", "PEM water electrolysis"]),
    (r"\b\u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043b\u0438\u0437\w*\b", ["electrolysis", "water electrolysis"]),
    (r"\b\u0430\u043b\u043a\u0430\u043b\u043d\w*\s+\u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043b\u0438\u0437\w*\b", ["alkaline electrolysis", "alkaline water electrolysis"]),
    (r"\b\u0442\u0432\u044a\u0440\u0434\u043e\u043e\u043a\u0441\u0438\u0434\w*\s+\u0435\u043b\u0435\u043a\u0442\u0440\u043e\u043b\u0438\u0437\w*\b", ["solid oxide electrolysis", "SOEC"]),
    (r"\b\u0435\u0444\u0435\u043a\u0442\u0438\u0432\u043d\w*\b", ["efficiency", "performance", "energy efficiency"]),
    (r"\b\u0434\u0435\u0433\u0440\u0430\u0434\u0430\u0446\w*\b", ["degradation", "durability", "stability"]),
    (r"\b\u0446\u0435\u043d\w*\b", ["cost", "cost reduction", "techno-economic"]),
    (r"\b\u0440\u0430\u0437\u0445\u043e\u0434\w*\b", ["cost", "capex", "opex"]),
    (r"\b\u043d\u0430\u043c\u0430\u043b\u044f\u0432\u0430\u043d\w*\b", ["reduction", "optimization"]),
    (r"\b\u043a\u0430\u0442\u0430\u043b\u0438\u0437\u0430\u0442\u043e\u0440\w*\b", ["catalyst", "electrocatalyst"]),
    (r"\b\u043c\u0435\u043c\u0431\u0440\u0430\u043d\w*\b", ["membrane"]),
    (r"\b\u0435\u043b\u0435\u043a\u0442\u0440\u043e\u0434\w*\b", ["electrode"]),
    (r"\b\u0438\u0440\u0438\u0434\u0438\w*\b", ["iridium"]),
    (r"\b\u043d\u0438\u043a\u0435\u043b\w*\b", ["nickel"]),
    (r"\b\u0434\u043e\u043a\u0442\u043e\u0440\u0430\u043d\u0442\w*\b", ["doctoral research", "research gaps"]),
]

DOMAIN_EXPANSIONS = {
    "pem electrolysis": [
        "proton exchange membrane electrolysis",
        "PEM water electrolysis",
        "PEM electrolyzer",
    ],
    "green hydrogen": ["renewable hydrogen", "electrolytic hydrogen"],
    "cost reduction": ["techno-economic", "LCOH", "CAPEX", "OPEX"],
    "efficiency": ["performance", "current density", "energy consumption", "voltage efficiency"],
    "degradation": ["stability", "durability", "lifetime"],
    "catalyst": ["catalyst loading", "precious metal reduction", "iridium reduction"],
    "membrane": ["membrane conductivity", "ion transport", "chemical stability"],
    "stack": ["stack design", "balance of plant", "system integration"],
}

STOPWORDS = {
    "and",
    "or",
    "for",
    "on",
    "in",
    "about",
    "the",
    "a",
    "an",
    "paper",
    "papers",
    "article",
    "articles",
    "find",
    "search",
}


def contains_cyrillic(value: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", value))


def normalize_query(query: str) -> tuple[str, list[str]]:
    lowered = clean_text(query).lower()
    normalized = lowered
    discovered_terms: list[str] = []
    for pattern, replacements in PATTERN_MAP:
        if re.search(pattern, normalized):
            normalized = re.sub(pattern, replacements[0].lower(), normalized)
            discovered_terms.extend(replacements)
    english_tokens = []
    for token in re.findall(r"[a-z0-9.+-]+", normalized):
        if token not in STOPWORDS:
            english_tokens.append(token)
    return " ".join(english_tokens), discovered_terms


def expand_query(query: str, extra_keywords: list[str], mode: str) -> dict[str, Any]:
    normalized, discovered_terms = normalize_query(query)
    english_core = clean_text(normalized)
    expanded_terms = []
    seen = set()

    def add_term(term: str) -> None:
        cleaned = clean_text(term)
        if cleaned and cleaned.lower() not in seen:
            expanded_terms.append(cleaned)
            seen.add(cleaned.lower())

    if english_core and not contains_cyrillic(english_core):
        add_term(english_core)
    elif not contains_cyrillic(query):
        add_term(clean_text(query))
    for term in discovered_terms:
        add_term(term)
    for keyword in extra_keywords:
        add_term(keyword)

    for trigger, terms in DOMAIN_EXPANSIONS.items():
        if trigger in english_core.lower():
            for term in terms:
                add_term(term)

    if mode == "exploratory":
        for trigger, terms in DOMAIN_EXPANSIONS.items():
            if any(token in english_core.lower() for token in trigger.split()):
                for term in terms:
                    add_term(term)

    if not expanded_terms:
        add_term(clean_text(query))

    return {
        "original_query": clean_text(query),
        "normalized_english_query": english_core,
        "expansion_mode": mode,
        "expanded_terms": expanded_terms,
        "search_clauses": build_search_clauses(expanded_terms, mode),
    }


def build_search_clauses(terms: list[str], mode: str) -> list[str]:
    if not terms:
        return []
    clauses = [f"({terms[0]})"]
    if len(terms) > 1 and mode in {"expanded", "exploratory"}:
        clauses.append("(" + " OR ".join(sorted(set(terms[1:6]))) + ")")
    if mode == "exploratory" and len(terms) > 6:
        clauses.append("(" + " OR ".join(sorted(set(terms[6:12]))) + ")")
    return clauses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="User query in Bulgarian or English")
    parser.add_argument(
        "--mode",
        default="expanded",
        choices=["strict", "expanded", "exploratory"],
        help="Expansion strictness",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Additional keyword to inject into the expansion",
    )
    add_output_argument(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = expand_query(args.query, args.keyword, args.mode)
    dump_json(result, args.output, args.pretty)


if __name__ == "__main__":
    main()
