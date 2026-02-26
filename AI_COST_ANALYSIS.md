# CareTopicz AI Cost Analysis

Cost analysis for the CareTopicz agent service: development spend, per-query estimates, scaling projections, and optimization strategies.

---

## 1. Actual Development Spend

| Category | Notes | Estimate (USD) |
|----------|--------|----------------|
| **API costs during development** | Anthropic Claude (Sonnet) for local runs, evals, debugging. ~50–200K input + 20–80K output tokens over project lifecycle. | $5–25 |
| **GCP / infrastructure** | Single VM (e.g. e2-medium) for OpenEMR + agent + MySQL; ~$30–50/month if run 24/7. For dev/demo, partial month or free tier. | $0–50 (one-time demo) |
| **LangSmith** | Tracing/history; free tier typically sufficient for dev. | $0 |
| **Other** | No other paid AI or infra assumed. | $0 |
| **Total development** | | **~$5–75** |

---

## 2. Per-Query Cost Estimate

- **Model:** Claude Sonnet 4 (e.g. claude-sonnet-4-6). Pricing (approximate): **$3 / 1M input tokens**, **$15 / 1M output tokens** (see [Anthropic pricing](https://www.anthropic.com/pricing)).
- **Typical single-turn query (with tools):**
  - Input: system prompt (~1.5K) + user message (~50) + tool results (~0.5–2K) → **~2–4K input tokens**.
  - Output: one response (~200–600 tokens) → **~200–600 output tokens**.
- **Per-query estimate:**  
  - Low: 2K in × $3/1M + 200 out × $15/1M ≈ **$0.006**.  
  - High: 4K in × $3/1M + 600 out × $15/1M ≈ **$0.012**.  
- **Average per query:** **~$0.008–0.01** (about 1 cent per query for typical usage).

---

## 3. Projections for 100 / 1,000 / 10,000 / 100,000 Concurrent Users

Assumptions:

- “Concurrent users” here = peak concurrent *sessions* that could send a request in a short window.
- Average **queries per user per day** ≈ 5–10; peak concurrency ≈ 5–10% of daily active users.
- One “query” = one agent turn (one LLM call + tool use + verification).

| Scale | Approx. daily queries | Monthly API (approx.) | Notes |
|-------|------------------------|------------------------|--------|
| **100 concurrent** | ~5K–20K/day | ~$1.2K–$6K | Single region, 1–2 agent replicas. |
| **1,000 concurrent** | ~50K–200K/day | ~$12K–$60K | Multiple agent replicas, load balancer, rate limits. |
| **10,000 concurrent** | ~500K–2M/day | ~$120K–$600K | Multi-region, reserved capacity, enterprise rate limits. |
| **100,000 concurrent** | ~5M–20M/day | ~$1.2M–$6M | Dedicated infra, quota agreements, caching and batching. |

*Ranges reflect low/high token usage and query volume.*

---

## 4. Infrastructure Scaling Assumptions

- **Compute:** Agent is stateless; scale horizontally (more containers/VMs). OpenEMR and MySQL need vertical scaling and/or read replicas at higher load.
- **Database:** MySQL for OpenEMR; agent does not persist conversation in DB by default. At 10K+ concurrent, consider connection pooling and read replicas.
- **API rate limits:** Anthropic tier limits (RPM/TPM) will require higher tiers or reserved capacity at 1K+ concurrent.
- **Caching:** No response caching in the current design; adding caching for common read-only tool results (e.g. drug interactions) could reduce token usage and cost.
- **Networking:** Agent ↔ OpenEMR on same VPC or private network; no egress cost for internal traffic.

---

## 5. Cost Optimization Strategies Considered or Implemented

| Strategy | Status | Effect |
|----------|--------|--------|
| **Token usage tracking** | Implemented | RequestMetrics and LangSmith metadata track input/output tokens and estimated cost per request. |
| **Model choice** | Implemented | Claude Sonnet used for quality; Haiku could be tried for simple tool-only flows to reduce cost. |
| **Verification and tool gating** | Implemented | Reduces low-value or repeated calls by refusing low-confidence or rule-breaking responses. |
| **Caching of tool results** | Considered | Cache read-only tool outputs (e.g. drug interaction checks) by query key to avoid duplicate LLM + tool cost. |
| **Prompt compression** | Considered | Shorter system prompt or summarized history to lower input tokens at scale. |
| **Reserved / committed capacity** | Considered | At 1K+ concurrent, negotiate committed throughput with Anthropic for lower unit cost. |
| **Eval gate (80%)** | Implemented | CI prevents regressions that could increase retries or failed flows and wasted tokens. |

---

## Summary

- **Development:** on the order of **$5–75** (API + optional GCP).
- **Per query:** **~$0.008–0.01** (typical single-turn with tools).
- **Scale:** 100 concurrent ≈ **$1.2K–$6K/month** API; 100K concurrent ≈ **$1.2M–$6M/month** API, with infra and rate limits driving architecture.
- **Optimization:** Tracking and gating in place; caching, model mix, and reserved capacity are the main levers for production scaling.
