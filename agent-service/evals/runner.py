#!/usr/bin/env python3
"""
CareTopicz Eval Runner - Execute test cases via LangSmith SDK (in-process) or HTTP.

Default: in-process invocation so each eval run is traced in LangSmith.
Use --url to run against a live agent service (HTTP) instead.

Usage:
    python -m evals.runner --all --min-pass-rate 0.8
    python -m evals.runner --all --url http://localhost:8000
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Project root for imports (agent-service)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def load_dataset(path: Path) -> list[dict]:
    """Load test cases from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array of test cases")
    return data


def evaluate_response(response_text: str, case: dict) -> tuple[bool, str]:
    """
    Evaluate agent response against case expectations. Returns (passed, reason).
    """
    expected_contains = case.get("expected_contains", [])
    expected_contains_any = case.get("expected_contains_any", [])
    expected_not_contains = case.get("expected_not_contains", [])
    min_length = case.get("min_length", 1)
    allow_empty = case.get("allow_empty_response", False)

    if allow_empty:
        return True, "OK (empty allowed)"

    if len(response_text) < min_length:
        return False, f"Response too short (min {min_length})"

    for sub in expected_contains:
        if sub.lower() not in response_text.lower():
            return False, f"Missing required: '{sub}'"

    for sub in expected_not_contains:
        if sub.lower() in response_text.lower():
            return False, f"Forbidden found: '{sub}'"

    if expected_contains_any:
        found = any(s.lower() in response_text.lower() for s in expected_contains_any)
        if not found:
            return False, f"Missing any of: {expected_contains_any}"

    return True, "OK"


def run_single_inprocess(case: dict) -> tuple[bool, str, str]:
    """
    Run one test case by invoking the graph in-process (traced in LangSmith).
    Returns (passed, response, reason).
    """
    from app.agent.graph import invoke_graph

    user_input = case.get("input", "")
    try:
        response_text, _metrics, _tools_used = invoke_graph(user_input)
        # invoke_graph returns (response, metrics, tools_used)
        passed, reason = evaluate_response(response_text or "", case)
        return passed, response_text or "", reason
    except Exception as e:
        return False, "", str(e)


def run_single_http(base_url: str, case: dict) -> tuple[bool, str, str]:
    """
    Run one test case via HTTP /chat. Returns (passed, response, reason).
    """
    import httpx

    user_input = case.get("input", "")
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            with httpx.Client() as client:
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
            passed, reason = evaluate_response(response_text, case)
            return passed, response_text, reason
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

    if last_error:
        return (
            False,
            "",
            f"HTTP 429 (rate limit) after {max_retries} retries: {last_error.response.text[:200]}",
        )
    return False, "", "Unknown error"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CareTopicz evals (LangSmith SDK / in-process or HTTP)")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to dataset JSON (default: mvp.json)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all datasets in evals/datasets/",
    )
    parser.add_argument(
        "--url",
        default=None,
        metavar="URL",
        help="Agent base URL (e.g. http://localhost:8000). If unset, run in-process (SDK/traced).",
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
    use_http = args.url is not None
    print(f"Running {len(cases)} test cases from {len(dataset_paths)} dataset(s)")
    if use_http:
        print(f"Mode: HTTP @ {args.url}\n")
        # Health check
        try:
            import httpx
            with httpx.Client() as client:
                r = client.get(f"{args.url.rstrip('/')}/health", timeout=5.0)
                r.raise_for_status()
        except Exception as e:
            print(f"Agent service not reachable at {args.url}: {e}")
            return 1
    else:
        print("Mode: in-process (LangSmith SDK; set LANGCHAIN_TRACING_V2=true for traces)\n")

    passed = 0
    failed = 0

    for case in cases:
        name = case.get("name", "unnamed")
        if use_http:
            ok, response, reason = run_single_http(args.url, case)
        else:
            ok, response, reason = run_single_inprocess(case)

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
