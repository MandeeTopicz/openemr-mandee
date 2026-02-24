"""
CareTopicz Agent Service - Request metrics and observability.

Tracks latency (LLM+graph, verification), token usage, cost estimation,
and error categorization. Integrates with LangSmith run metadata.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

# Anthropic pricing per 1M tokens (USD, approximate - update as needed)
# Claude Sonnet 4: https://www.anthropic.com/pricing
_ANTHROPIC_COST_PER_1M = {
    "claude-sonnet-4-20250514": (3.0, 15.0),  # input, output
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-3-5-sonnet": (3.0, 15.0),
    "claude-3-opus": (15.0, 75.0),
    "claude-3-haiku": (0.25, 1.25),
}


@dataclass
class RequestMetrics:
    """Metrics for a single chat request."""

    run_id: str | None = None  # LangSmith run ID for feedback linking
    total_ms: float = 0.0
    graph_ms: float = 0.0
    verification_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    error_category: str | None = None
    error_message: str | None = None

    def to_metadata(self) -> dict[str, Any]:
        """Convert to dict for LangSmith run metadata."""
        d: dict[str, Any] = {
            "latency_total_ms": round(self.total_ms, 2),
            "latency_graph_ms": round(self.graph_ms, 2),
            "latency_verification_ms": round(self.verification_ms, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }
        if self.error_category:
            d["error_category"] = self.error_category
        if self.error_message:
            d["error_message"] = self.error_message[:500]  # truncate
        return d


def aggregate_token_usage(messages: list) -> tuple[int, int, int]:
    """
    Aggregate usage_metadata from AIMessages. Returns (input_tokens, output_tokens, total_tokens).
    """
    total_in = 0
    total_out = 0
    for m in messages:
        um = getattr(m, "usage_metadata", None)
        if not um:
            continue
        if isinstance(um, dict):
            total_in += int(um.get("input_tokens", 0) or 0)
            total_out += int(um.get("output_tokens", 0) or 0)
        else:
            total_in += int(getattr(um, "input_tokens", 0) or 0)
            total_out += int(getattr(um, "output_tokens", 0) or 0)
    return total_in, total_out, total_in + total_out


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4-6") -> float:
    """Estimate cost in USD from token counts. Uses default pricing if model unknown."""
    costs = _ANTHROPIC_COST_PER_1M.get(model) or (3.0, 15.0)
    in_per_1m, out_per_1m = costs
    return (input_tokens / 1_000_000 * in_per_1m) + (output_tokens / 1_000_000 * out_per_1m)


def categorize_error(exc: BaseException) -> str:
    """Categorize exception for error tracking."""
    msg = str(exc).lower()
    if "429" in msg or "rate" in msg or "limit" in msg:
        return "rate_limit"
    if "401" in msg or "403" in msg or "api_key" in msg or "auth" in msg:
        return "auth"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "validation" in msg or "value" in msg:
        return "validation"
    if "500" in msg or "502" in msg or "503" in msg:
        return "upstream"
    return "unknown"


@contextmanager
def track_latency_ms(metrics: RequestMetrics, field_name: str):
    """Context manager to measure elapsed time and set field on RequestMetrics."""
    import time

    start = time.perf_counter()
    yield
    elapsed_ms = (time.perf_counter() - start) * 1000
    setattr(metrics, field_name, elapsed_ms)


def update_langsmith_run_metadata(run_id: str | None, metadata: dict[str, Any]) -> None:
    """Update the current LangSmith run with metadata. No-op if tracing disabled."""
    if not run_id:
        return
    try:
        from langsmith import Client

        client = Client()
        client.update_run(run_id, extra={"metadata": metadata})
    except Exception:
        pass  # Don't fail request if LangSmith update fails


def log_eval_summary(
    passed: int,
    failed: int,
    total: int,
    dataset_name: str = "caretopicz-evals",
) -> None:
    """
    Log eval run summary to LangSmith for historical tracking.
    Creates a run with metadata for pass rate, counts, dataset.
    """
    try:
        from datetime import datetime, timezone

        from langsmith import Client

        client = Client()
        project = "caretopicz-evals"
        now = datetime.now(timezone.utc)
        client.create_run(
            name=f"eval_run_{now.strftime('%Y%m%d_%H%M%S')}",
            inputs={"dataset": dataset_name, "passed": passed, "failed": failed, "total": total},
            run_type="chain",
            project_name=project,
            start_time=now,
            end_time=now,
            extra={
                "metadata": {
                    "eval_pass_rate": round(passed / total, 4) if total else 0,
                    "eval_passed": passed,
                    "eval_failed": failed,
                    "eval_total": total,
                    "eval_dataset": dataset_name,
                }
            },
        )
    except Exception:
        pass  # Don't fail eval if LangSmith log fails
