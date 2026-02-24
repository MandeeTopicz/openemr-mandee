#!/usr/bin/env python3
"""
CareTopicz Eval Runner - Execute test cases against the agent service.

Usage:
    python evals/runner.py [--dataset evals/datasets/mvp.json] [--url http://localhost:8000]

Requires agent service running (uvicorn or similar).
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

# Project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dataset(path: Path) -> list[dict]:
    """Load test cases from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array of test cases")
    return data


def run_single(
    client: httpx.Client,
    base_url: str,
    case: dict,
) -> tuple[bool, str, str]:
    """
    Run one test case. Returns (passed, response, reason).
    """
    name = case.get("name", "unnamed")
    user_input = case.get("input", "")
    expected_contains = case.get("expected_contains", [])
    expected_contains_any = case.get("expected_contains_any", [])
    expected_not_contains = case.get("expected_not_contains", [])
    min_length = case.get("min_length", 1)
    allow_empty = case.get("allow_empty_response", False)

    try:
        resp = client.post(
            f"{base_url.rstrip('/')}/chat",
            json={"message": user_input},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        response_text = data.get("response", "")
    except httpx.HTTPStatusError as e:
        return False, "", f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except httpx.RequestError as e:
        return False, "", f"Request failed: {e}"
    except json.JSONDecodeError as e:
        return False, "", f"Invalid JSON: {e}"

    # Allow empty/short response for edge cases
    if allow_empty:
        return True, response_text, "OK (empty allowed)"

    if len(response_text) < min_length:
        return False, response_text, f"Response too short (min {min_length})"

    for sub in expected_contains:
        if sub.lower() not in response_text.lower():
            return False, response_text, f"Missing required: '{sub}'"

    for sub in expected_not_contains:
        if sub.lower() in response_text.lower():
            return False, response_text, f"Forbidden found: '{sub}'"

    if expected_contains_any:
        found = any(s.lower() in response_text.lower() for s in expected_contains_any)
        if not found:
            return (
                False,
                response_text,
                f"Missing any of: {expected_contains_any}",
            )

    return True, response_text, "OK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CareTopicz evals")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_PROJECT_ROOT / "evals" / "datasets" / "mvp.json",
        help="Path to dataset JSON",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Agent service base URL",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print full response for each case",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}")
        return 1

    cases = load_dataset(args.dataset)
    print(f"Running {len(cases)} test cases from {args.dataset}")
    print(f"Agent URL: {args.url}\n")

    passed = 0
    failed = 0

    with httpx.Client() as client:
        # Quick health check
        try:
            r = client.get(f"{args.url.rstrip('/')}/health", timeout=5.0)
            r.raise_for_status()
        except Exception as e:
            print(f"Agent service not reachable at {args.url}: {e}")
            return 1

        for case in cases:
            name = case.get("name", "unnamed")
            ok, response, reason = run_single(client, args.url, case)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failed += 1

            print(f"  [{status}] {name}: {reason}")
            if args.verbose or not ok:
                preview = (response[:200] + "...") if len(response) > 200 else response
                print(f"       Response: {preview!r}\n")

    print(f"\n--- Results: {passed} passed, {failed} failed of {len(cases)} total ---")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
