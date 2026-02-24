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
import time
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

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            resp = client.post(
                f"{base_url.rstrip('/')}/chat",
                json={"message": user_input},
                timeout=60.0,
            )
            if resp.status_code == 429 and attempt < max_retries - 1:
                time.sleep(30)
                continue
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            break
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(30)
                continue
            return False, "", f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except httpx.RequestError as e:
            return False, "", f"Request failed: {e}"
        except json.JSONDecodeError as e:
            return False, "", f"Invalid JSON: {e}"
    # Exhausted retries on 429 (should not reach here; last 429 attempt returns above)
    if last_error:
        return False, "", f"HTTP 429 (rate limit) after {max_retries} retries: {last_error.response.text[:200]}"

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
        default=None,
        help="Path to dataset JSON (default: mvp.json)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all datasets in evals/datasets/ (correctness, edge_cases, adversarial, multi_step)",
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
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="Log eval summary to LangSmith for historical tracking",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Pass if passed/total >= RATE (e.g. 0.8 for 80%%). Default: require all to pass.",
    )
    args = parser.parse_args()

    if args.all:
        datasets_dir = _PROJECT_ROOT / "evals" / "datasets"
        dataset_paths = sorted(datasets_dir.glob("*.json"))
        if not dataset_paths:
            print(f"No datasets found in {datasets_dir}")
            return 1
    else:
        dataset_path = args.dataset or (_PROJECT_ROOT / "evals" / "datasets" / "mvp.json")
        if not dataset_path.exists():
            print(f"Dataset not found: {dataset_path}")
            return 1
        dataset_paths = [dataset_path]

    all_cases: list[tuple[Path, dict]] = []
    for p in dataset_paths:
        for c in load_dataset(p):
            all_cases.append((p, c))

    cases = [c for _, c in all_cases]
    print(f"Running {len(cases)} test cases from {len(dataset_paths)} dataset(s)")
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

    if args.langsmith:
        try:
            from app.observability.metrics import log_eval_summary

            dataset_name = "+".join(p.stem for p in dataset_paths)
            log_eval_summary(passed=passed, failed=failed, total=len(cases), dataset_name=dataset_name)
            print("  (Eval summary logged to LangSmith)")
        except Exception as e:
            print(f"  (LangSmith log skipped: {e})")

    if args.min_pass_rate is not None:
        rate = passed / len(cases) if cases else 0.0
        if rate >= args.min_pass_rate:
            print(f"  Pass rate {rate:.1%} >= {args.min_pass_rate:.0%} (gate passed)")
            return 0
        print(f"  Pass rate {rate:.1%} < {args.min_pass_rate:.0%} (gate failed)")
        return 1
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
