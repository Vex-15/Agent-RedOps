# RedOps — Business Plan

*Prepared for the cfo.ai hackathon track. All figures are honest estimates with stated
assumptions; nothing here is a committed financial forecast.*

---

## 1. Problem

Companies are wiring LLM agents into workflows with real side effects — procurement,
payments, infrastructure changes, customer data access. Unlike classic software, an
agent's "business logic" is a chain of natural-language decisions across multiple agents
and tools, which means:

- **Prompt injection and deceptive tool outputs** can walk an agent straight past its
  authorization rules (our own demo shows a forged approval id and a tampered vendor
  record executing a purchase).
- **Existing AppSec tooling doesn't see it.** DAST/IAST watch requests and code paths;
  they don't understand that an approver agent trusted an unverified tool response.
- **Guardrails vendors filter prompts** at the boundary, but nobody verifies that the
  *pipeline* — requester → vendor lookup → approver → purchaser → auditor — actually
  fails closed end to end.

Security teams currently discover this in production, or not at all.

## 2. Solution

**RedOps is continuous adversarial evaluation for multi-agent systems.**

1. **Attack scenarios** (deterministic, version-controlled) are executed against a
   simulated or mirrored copy of the customer's agent pipeline.
2. The **analyzer** reads full execution traces and detects policy violations —
   authorization bypasses, trust-boundary violations, credit/budget exceedance,
   instruction overrides, malformed-payload crashes.
3. Violations are chained into **attack paths** with root-cause analysis.
4. The **remediation library** maps each finding to a concrete code-level guard, and —
   the differentiator — **re-runs the attack with the guard applied and verifies the
   attack is blocked** (our current suite: 11 scenarios, 48 tests, every attack
   neutralized, positive baseline stays clean, one scenario proves crash → recovery).
5. Every run emits an **evidence package**: nested execution trace, error capture,
   defense verdicts, and exportable JSON/Markdown audit reports. Traces are exported to
   Neatlogs (spans for agents, tools, and guards) and agent sessions are checkpointed
   with Entire, so findings, traces, and code changes link to one another.

**Today's working demo** (hackathon state): 5-stage procurement pipeline, 11 attack
scenarios, 7 composable guards, live FastAPI backend + React console with a trace
explorer, failure-and-recovery evidence, and report export. Everything above already
runs end to end.

## 3. Market

- **Beachhead:** mid-market B2B SaaS and fintech companies (100–2,000 employees) running
  internal agent automation in finance/procurement/IT ops — the teams that already own
  SOC2 obligations and now own agent risk.
- **Expansion:** agent-platform vendors (agent frameworks, RPA, enterprise copilots)
  who need "verified secure" as a buying criterion; auditors and pen-test firms using
  RedOps as an assessment tool.
- **Sizing (assumptions, not citations):** adjacent AppSec/DAST spend is roughly a
  $5–7B global market; agent security is a new segment of it. If 2% of that spend
  shifts to agent-pipeline evaluation within five years, the TAM RedOps targets is
  ~$100–140M. A realistic SAM of 4,000 qualifying mid-market+ buyers at an average
  $30k ACV is ~$120M.

## 4. Product & Packaging

| Tier | What they get | Price |
|---|---|---|
| **Community (OSS)** | Local runner, built-in scenario library, trace explorer, JSON/MD export | Free — funnel & trust |
| **Team** | 5 pipelines, 50 scenarios, CI gating (fail build on new criticals), Neatlogs trace retention, email support | **$999/mo** (annual: $9,990/yr) |
| **Enterprise** | Unlimited pipelines & scenarios, custom scenario authoring SDK, VPC/on-prem deployment, SSO/SAML, audit exports, 24h SLA | **$30k–$60k/yr** by scale |
| **Services** | Scenario-authoring engagements, agent threat modeling, pre-deployment assessments | $15k–$25k fixed, ~1 per quarter |

Assumed blended ACV: **$30k**. Team is the volume tier; Enterprise is the margin tier.

## 5. Go-to-Market

1. **Open-source core** (this repo) as the top of funnel — security engineers run it
   locally in ten minutes.
2. **Design-partner program:** 3 free 90-day pilots with mid-market security teams in
   exchange for case studies and scenario contributions.
3. **Content & benchmarks:** publish an "Agent Attack Benchmark" (how often common
   agent stacks fail our scenario suite) — the report is the sales asset.
4. **Integration-led:** adapters that point RedOps at LangGraph / CrewAI / custom agent
   stacks, listed in framework marketplaces.
5. **Conferences:** agent-security talks at BSides-class and AI-engineering events;
   the failure-and-recovery demo is the hook.

## 6. Cost structure (monthly burn, first 12 months)

| Line item | Month 0–6 | Month 7–12 |
|---|---|---|
| Founders (2, stipend) | $8,000 | $10,000 |
| Contract engineer | $9,000 | $9,000 |
| Cloud + infra (dev/staging, demo envs) | $600 | $1,500 |
| Observability (Neatlogs usage-based tracing) | $200 | $1,000 |
| Tooling (Entire, GitHub, CI, SaaS) | $400 | $800 |
| Go-to-market (events, content) | $0 | $2,000 |
| **Total burn** | **≈ $18,200/mo** | **≈ $24,300/mo** |

Gross margin target: **80%+** (software; usage-based tracing is passed through at
Enterprise tier). Services engagements run ~60% margin and are deliberately capped.

## 7. Revenue model & projections

Assumptions: Team ACV $12k, Enterprise ACV $40k average, 2-month sales cycle for Team,
4-month for Enterprise, 2% monthly logo churn on Team (zero on Enterprise in year 1).

| | Exit M6 | Exit M12 | Exit M24 |
|---|---|---|---|
| Team customers | 3 | 9 | 26 |
| Enterprise customers | 0 | 2 | 7 |
| ARR run-rate | $36k | $188k | $592k |
| Revenue booked YTD | $10k | $95k | $430k |

Path: pilots are free M0–M3; first paid Team deals land M4–M5 (via the benchmark
report); first Enterprise deal M9–M10 (pilot conversion). Nothing here assumes viral
growth — it assumes 2 founders selling directly.

## 8. Runway

- **Raise:** $500k pre-seed (target), plus hackathon prize money as bridge.
- **Burn:** blended ≈ $21k/mo over the year.
- **Runway at M0:** $500k ÷ $21k ≈ **24 months**, extended by revenue: from M6 the
  ~$36k ARR and M12's ~$188k ARR offset burn, so true cash runway to insolvency is
  beyond 28 months under the base case.
- **Default-alive check:** the company reaches ramen profitability (~$40k MRR) around
  **M16–M18** in the base case without additional raise. A bridge is only needed if
  Enterprise sales cycle slips past 6 months.
- **Use of funds:** ~55% product/engineering, ~20% go-to-market, ~15% infra/compliance,
  ~10% buffer.

## 9. Milestones (funded 12 months)

1. **M3:** 3 design partners running RedOps in CI; scenario SDK (customer-authored
   scenarios) in private beta.
2. **M6:** Agent Attack Benchmark v1 published; first 3 paid Team customers.
3. **M9:** Enterprise deployment story (VPC + SSO) shipped; 2 Enterprise pilots.
4. **M12:** $188k ARR run-rate, 11+ customers, zero critical unpatched findings in our
   own supply chain (we run RedOps on RedOps).

## 10. Risks & honest caveats

- **Platform risk:** if one agent framework dominates, we ship deep integration with it
  first — mitigated by keeping the core framework-agnostic (trace-in, policy-in).
- **Build-vs-buy:** guardrails vendors could add pipeline verification. Our moat is the
  *verified-defense* corpus — every scenario ships with the attack, the guard, and the
  proof it blocks — which is data and methodology, not a filter rule.
- **Simulated vs. real pipelines:** the demo evaluates simulated pipelines; the product
  roadmap's adapter layer is the hard part and is funded first with pre-seed.

---

*RedOps — security for the agent era. Demo artifacts (11 scenarios, verified defenses,
failure/recovery evidence, live trace export) are in this repository; see `README.md`.*
