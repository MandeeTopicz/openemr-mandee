# AI Cost Analysis

## Model Configuration
- **Model**: Claude Sonnet 4 (claude-sonnet-4-6)
- **Provider**: Anthropic API
- **Pricing**: $3 per 1M input tokens, $15 per 1M output tokens

## Per-Request Token Estimates

| Component | Input Tokens | Output Tokens |
|-----------|-------------|---------------|
| System prompt | ~6,000 | — |
| User message + history (avg 20 msgs) | ~2,000 | — |
| Tool schemas (12 tools) | ~1,500 | — |
| Tool call + result (avg 1.5 tools/query) | ~500 | ~200 |
| Agent reasoning + response | — | ~400 |
| **Total per request** | **~10,000** | **~600** |

## Per-Request Cost
- Input: 10,000 tokens x $3/1M = **$0.03**
- Output: 600 tokens x $15/1M = **$0.009**
- **Total per request: ~$0.039**

## Development Spend (Actual)
- Eval runs (95 cases x ~5 iterations): ~475 requests = **~$18.50**
- Manual testing during development: ~300 requests = **~$11.70**
- Biologic flow testing (multi-turn, 5-8 messages per flow): ~200 requests = **~$7.80**
- **Total estimated development spend: ~$38**

## User Scaling Projections

Assumptions: average clinic user sends 15 queries/day, 22 working days/month.

| Users | Queries/Month | Monthly Cost | Annual Cost |
|-------|--------------|-------------|-------------|
| 100 | 33,000 | $1,287 | $15,444 |
| 1,000 | 330,000 | $12,870 | $154,440 |
| 10,000 | 3,300,000 | $128,700 | $1,544,400 |
| 100,000 | 33,000,000 | $1,287,000 | $15,444,000 |

## Cost Optimization Strategies

**Prompt caching**: Anthropic's prompt caching could reduce input costs by ~90% for the system prompt (6,000 tokens sent every request). At 1,000 users this saves ~$7,000/month.

**Model tiering**: Route simple queries (drug interactions, provider search) to Claude Haiku ($0.25/$1.25 per 1M tokens) — roughly 10x cheaper. Complex queries (biologic onboarding, multi-tool) stay on Sonnet. Estimated 70% of queries could use Haiku, reducing costs by ~60%.

**Response caching**: Common drug interaction pairs (lisinopril/ibuprofen, warfarin/aspirin) could be cached in Redis. Estimated 20-30% cache hit rate for drug interactions.

**With all optimizations at 1,000 users**: ~$3,200/month (down from $12,870)

## Infrastructure Costs (GCP)
- VM (e2-small, 2 vCPU, 2GB RAM): ~$15/month
- Persistent disk (20GB): ~$2/month
- Network egress: ~$5/month
- **Total infrastructure: ~$22/month**

## Break-Even Analysis
At $50/user/month SaaS pricing:
- 100 users: $5,000 revenue vs $1,309 cost = **$3,691 profit**
- 1,000 users: $50,000 revenue vs $12,892 cost = **$37,108 profit**
