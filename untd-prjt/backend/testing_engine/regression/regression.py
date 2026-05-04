"""
Regression Testing — Stores and compares test results across runs.
Uses a local JSON file to persist previous results.
"""

import json
import os
import hashlib
import time
from pathlib import Path

REGRESSION_STORE = Path(__file__).resolve().parent / "regression_data.json"


def _load_store() -> dict:
    """Load the regression data store."""
    if REGRESSION_STORE.exists():
        try:
            with open(REGRESSION_STORE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_store(data: dict):
    """Persist the regression data store."""
    try:
        with open(REGRESSION_STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _code_hash(code: str) -> str:
    """Generate a stable hash for the code content."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def run_regression_check(code: str, language: str, current_results: list) -> dict:
    """
    Compare current test results against previously stored results.
    Returns regression analysis with newly failed, newly passed, and stable tests.
    """
    code_id = _code_hash(code)
    store = _load_store()

    previous = store.get(code_id, {}).get("results", [])
    prev_map = {r["name"]: r for r in previous}

    regressions = []
    improvements = []
    stable = []
    new_tests = []

    for test in current_results:
        name = test.get("name", "")
        passed = test.get("passed", False)

        if name in prev_map:
            prev_passed = prev_map[name].get("passed", False)
            if prev_passed and not passed:
                regressions.append({
                    "name": name,
                    "category": "Regression",
                    "passed": False,
                    "input_data": test.get("input_data", ""),
                    "actual": test.get("actual", ""),
                    "message": f"REGRESSION: Previously passed, now fails. {test.get('message', '')}"
                })
            elif not prev_passed and passed:
                improvements.append({
                    "name": name,
                    "category": "Improvement",
                    "passed": True,
                    "input_data": test.get("input_data", ""),
                    "actual": test.get("actual", ""),
                    "message": f"IMPROVEMENT: Previously failed, now passes. {test.get('message', '')}"
                })
            else:
                stable.append(name)
        else:
            new_tests.append(name)

    # Store current results for next comparison
    store[code_id] = {
        "language": language,
        "timestamp": time.time(),
        "results": current_results,
    }
    _save_store(store)

    total_changes = len(regressions) + len(improvements)

    return {
        "has_previous": len(previous) > 0,
        "previous_count": len(previous),
        "current_count": len(current_results),
        "regressions": regressions,
        "improvements": improvements,
        "stable_count": len(stable),
        "new_tests_count": len(new_tests),
        "tests": regressions + improvements,
        "summary": (
            f"Regression analysis: {len(regressions)} regressions, {len(improvements)} improvements, "
            f"{len(stable)} stable, {len(new_tests)} new tests."
            if len(previous) > 0
            else "First run — baseline established. Re-run analysis to see regression comparisons."
        ),
    }
