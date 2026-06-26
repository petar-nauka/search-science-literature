#!/usr/bin/env python3
"""Deprecated v1 entry point — kept as a thin wrapper around search_orchestrator.

The orchestrator lives in `search_orchestrator.py`. This shim exists only so
external scripts that still call `python search_scholarly.py ...` keep working.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parent / "search_orchestrator.py"
    spec = importlib.util.spec_from_file_location("search_orchestrator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


if __name__ == "__main__":
    main()
