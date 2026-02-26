---
name: CareTopicz status and next steps
overview: "Review of CareTopicz vs PRD, Development Plan, and Pre-Search: current state, gaps, and suggested next steps, with two clarifying questions on priority and demo definition."
todos: []
isProject: false
---

# CareTopicz — Status vs PRD, Development Plan, and Pre-Search

## Current state summary

**Phase 1 (MVP) and Phase 2 (Early Submission)** are effectively complete per [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md): all build-order tasks (1–10), 8 tools, verification layer (fact check, hallucination, confidence, domain rules), OpenEMR module with chat widget, 61 evals across 5 datasets, CI (lint → test → eval 80% gate → build), Docker Compose, and observability are in place. The [PRD](docs/OpenEMR_CareTopicz_PRD.md) Phase 1 feature set (F1.1–F1.12) is implemented; the [Pre-Search](docs/OpenEMR_PreSearch_Document.md) stack and tool inventory match the codebase.

**Phase 3 (Final Submission)** is partially complete. Remaining gaps:

---

## Gaps vs Development Plan / PRD / Pre-Search

### Technical (Phase 3)


| Item                        | Plan                                                      | Status                                                                                                               |
| --------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Eval runner + LangSmith SDK | Phase 2: "Eval runner integrated with LangSmith SDK"      | Not done; evals run via `evals/runner.py` and HTTP, not LangSmith SDK                                                |
| Intermediate verification   | "Intermediate verification between tool calls"            | Verification only at final response; no per-tool-call verification loop                                              |
| Latency tracking            | Single-tool < 5s, multi-step < 15s "tracked in LangSmith" | Targets documented; no formal metrics export or dashboard                                                            |
| Tool success rate > 95%     | Pre-Search performance targets                            | Not systematically measured/reported                                                                                 |
| Publicly accessible demo    | "Publicly accessible demo with sample data"               | GCP at [http://34.139.68.240:8300](http://34.139.68.240:8300) exists but chat 502 until agent URL/reachability fixed |


### Open source and release


| Item                                              | Plan                | Status                                                                                                                                           |
| ------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Eval dataset published (CC BY 4.0)                | Phase 3 Open Source | Dataset in repo with [evals/datasets/LICENSE.md](agent-service/evals/datasets/LICENSE.md); "published" (e.g. standalone repo or Zenodo) not done |
| Module compatible with OpenEMR upstream (GPL-2.0) | Phase 3 Open Source | Unchecked; may require license alignment and upstream contribution process                                                                       |


### Submission deliverables (all unchecked in plan)

- **GitHub repo with setup guide and deployed link** — Repo exists; setup in README; deployed link depends on GCP (or other) being stable and documented.
- **Demo video (3–5 min)** — Not created.
- **Pre-Search document (completed)** — [OpenEMR_PreSearch_Document.md](docs/OpenEMR_PreSearch_Document.md) exists and is complete.
- **Agent Architecture doc (1–2 pages)** — [OpenEMR_Agent_Architecture.md](docs/OpenEMR_Agent_Architecture.md) exists (longer than 1–2 pages; could be summarized).
- **AI Cost Analysis** — Actual dev spend + projections for 100/1K/10K/100K users (PRD and Pre-Search mention this) — not written.
- **Eval dataset: 50+ test cases with results** — 61 cases in repo; "with results" could mean a report or published run (e.g. pass rate, breakdown).
- **Open source: published module + eval dataset** — Code is open; formal "publish" (e.g. OpenEMR PR, dataset repo or Zenodo) not done.
- **Deployed application: publicly accessible** — Tied to fixing 502 and documenting the GCP (or other) URL.
- **Social post (X or LinkedIn)** — Not done.

---

## Doc alignment

- **PRD:** Chat widget is described as "React-based" in the PRD; implementation is vanilla JS. Functionally aligned; doc could be updated for accuracy.
- **Architecture doc:** Still says "React embedded" in one place; implementation is vanilla JS. Otherwise matches current design (sidecar, LangGraph, verification, tools).
- **Pre-Search:** Matches stack, tools, verification design, and eval approach. Performance targets and open-source plan are consistent with the Development Plan.

---

## Suggested next-step categories

1. **Stabilize deployment** — Resolve chat 502 on GCP (agent URL, agent running, firewall) so the deployed app is usable. Document the public URL and any setup (e.g. in README or a short deployment note).
2. **Submission package** — Produce the deliverables: demo video, AI Cost Analysis doc, 1–2 page architecture summary (optional), eval results summary (61 cases, pass rate, categories). Add "deployed link" and "setup guide" to README if not already clear.
3. **Technical hardening (optional before submission)** — LangSmith SDK eval integration; optional intermediate verification; formal latency/success metrics (if you want these in the narrative or video).
4. **Open source and community** — Publish eval dataset (e.g. CC BY 4.0 repo or Zenodo); consider OpenEMR upstream contribution (GPL-2.0, compatibility); social post.

---

## Clarifying questions

Before locking next steps, two decisions would help:

1. **Immediate priority:** Is the goal to **finish the submission checklist** (demo video, cost analysis, deployed link, eval results summary) as-is, or do you want to **close technical gaps first** (e.g. LangSmith eval integration, intermediate verification, or latency/success tracking) and then do the submission package?
2. **Demo definition:** Does **GCP at [http://34.139.68.240:8300](http://34.139.68.240:8300)** (once the agent 502 is fixed) satisfy "publicly accessible demo with sample data," or do you want a separate demo setup (e.g. Railway, dedicated demo subdomain, or different instance)?

Answers will determine whether the next concrete steps are deployment + docs + video + cost analysis, or a mix of technical work and submission deliverables.