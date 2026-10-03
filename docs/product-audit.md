# Product audit — OOH Campaign Performance Analyzer

Component-by-component re-evaluation ahead of the redesign. The product identity is
fixed: this is and remains an **OOH Campaign Performance Analyzer**. What is under
review is every component inside it.

Companion documents: `docs/design-spec.md` (visual specification),
`docs/assumptions.md` (modelling assumptions).

---

## 1. Refined thesis

**Current (implicit):**

> An OOH campaign analyzer that compares planned and delivered campaign performance
> and identifies under-delivery.

**Refined:**

> An OOH campaign performance analyzer that measures every placement against the
> impressions contracted *by today*, surfaces under-delivery that campaign-level
> reporting hides, prices it in media value, and separates what can still be fixed
> in flight from what has to be reconciled after it.

Three words carry the upgrade, and each is earned by a measurement below:

- **by today** — the proration mechanism that already exists and stays central.
- **hides** — the gross-vs-net finding in §3.3. Campaign-level variance systematically
  understates the operational problem; the audit quantifies by how much.
- **separates** — live vs completed is a real distinction with different ranking keys,
  not a label.

Everything in this audit is judged against that sentence.

---

## 2. How each component was judged

Five questions, applied to current components and proposed additions alike:

1. What marketing question does it answer?
2. Does the current dataset actually support it?
3. Is the methodology defensible out loud?
4. Does it change a real decision?
5. Can it be explained in an interview in under a minute?

A component that fails **2** is cut regardless of how good it looks. A component that
fails **4** is cut regardless of how defensible it is.

---

## 3. Four findings that changed the plan

### 3.1 The "Watch" tier is 100% false alarms — cut it

I proposed a Watch band (−5% to −2%) in `design-spec.md` as early warning. Tested
against the data, it does not survive.

The generator gives injected faults a health multiplier of 0.55–0.82 and healthy
placements 0.96–1.05, so the realised delivery index separates the two populations
cleanly:

| Band | n | Delivery index | Real faults inside |
|---|---|---|---|
| Flagged (< −5%) | 61 | 0.535 – 0.943 | **60** |
| Watch (−5% to −2%) | 128 | 0.951 – 0.980 | **0** |
| On track (≥ −2%) | 406 | 0.980 – 1.059 | **0** |

A Watch tier would put **128 healthy placements** on screen as early warnings, next to
24 genuine live problems. It would be the single most damaging thing in the product: it
manufactures 128 non-problems and dilutes the 61 real ones by a factor of three.

The bands also show the −5% line is doing its job almost perfectly — the worst unflagged
placement is 0.951 and the best flagged is 0.943, so the threshold sits in a genuine gap
in the distribution, with the one documented false positive.

**Decision: the portfolio has three states, not four — On track (534), Live issue (24),
Completed shortfall (37).** Amber is reassigned to the materiality split *inside* the
live queue (§3.4), where it has real work to do.

*This is a correction to my own specification, made because the data contradicted it.*

### 3.2 The monthly "Delivery against plan" chart measures campaign count — cut it

Panel 02 plots delivered vs planned impressions by calendar month, aggregated across all
eight campaigns.

| Month | Delivered | Campaigns in flight | Delivered ÷ planned |
|---|---|---|---|
| 2025-02 | 35.9m | 1 | 98.9% |
| 2025-05 | 5.2m | 1 | 99.0% |
| 2025-08 | 26.2m | 1 | 96.7% |
| 2026-08 | 47.1m | 3 | 96.2% |

The plotted line swings between 5.2m and 47.1m. That swing is **how much inventory was
in flight that month** — correlation with campaigns-in-flight 0.56, and the rest is
flight length and overlap. The performance signal, delivered ÷ planned, occupies a
**3.5-point band (95.7%–99.1%)** and is invisible at that scale: the two lines sit
visually on top of each other for the entire chart.

Two further problems: it compares verified against `estimated_impressions`, a different
basis from every other number in the product (which uses contracted-to-date); and
calendar months cut across flights that start and end mid-month, so no month is a
like-for-like unit.

The chart cannot show the thing its title claims. **REMOVE.** Replaced by a per-campaign
cumulative delivery trajectory inside drill-down, where the x-axis is flight days and
the comparison is against contracted-to-date.

### 3.3 Gross vs net shortfall is the strongest unexploited analytic — promote it

Campaign-level variance nets over-delivery against under-delivery, which systematically
hides the operational problem:

| Campaign | Reads (net) | Gross shortfall | Masked by over-delivery | Flagged placements |
|---|---|---|---|---|
| 1 | **−1.1%** | 1.04m | **63%** | 7 |
| 3 | **−1.1%** | 1.49m | **48%** | 5 |
| 8 (live) | −3.1% | 2.54m | 26% | 6 |
| 7 (live) | −4.8% | 1.56m | 25% | 11 |
| Portfolio | **−2.9%** | **17.1m** | **26%** | 61 |

Campaign 1 reads −1.1% — comfortably healthy by any campaign-level report — while
carrying 1.04m impressions of real shortfall across seven placements, 63% of it hidden
by other sites running hot. That single row is the product's entire argument.

This is deterministic, needs no new data, is trivially explainable ("over-delivery on
one site does not repair a dark site on another"), and directly supports the word
*hides* in the thesis. **Promote to a headline concept** on the campaign card, the
drill-down, and the portfolio hero.

### 3.4 Downtime explains 7.4% of the problem — demote it, but keep it honest

Digital downtime hours are generated and currently surfaced nowhere. Tested as a causal
explanation on the 14 flagged digital placements:

- Downtime accounts for **7.4%** of their aggregate shortfall
  (450,475 of 6,105,225 impressions), mean 7.0% per placement, range 2.3–13.8%.

So downtime is a real but minor cause. A "Downtime analysis" panel would be a panel
explaining 7% of the problem — that fails question 4.

But as a **line in the placement drawer** it is the only causal decomposition this
dataset supports, and its value is partly that it reports what it *cannot* explain:
"34 logged downtime hours account for 86k of this placement's 1.2m shortfall; the
remaining 1.1m is not explained by downtime." **KEEP at drawer level, REJECT as a
panel.**

---

## 4. Audit of current components

| Component | Verdict | Reasoning |
|---|---|---|
| Synthetic-data banner | **KEEP** | Non-negotiable per `CLAUDE.md`. Restyled, never removed. |
| As-of line | **IMPROVE** | Split: permanent as-of chip in the app bar (it governs every number) + the fuller sentence in Method. |
| KPI card — Under-delivering (61) | **IMPROVE** | Splits into Live issues (24) and Completed shortfalls (37). One number for two different jobs was the original sin. |
| KPI card — Spend at risk ($152,435) | **KEEP** | Still the money headline. Gains a sibling: $60,048 still preventable. The two are never added. |
| KPI card — Spend billed to date | **MOVE** | Secondary. To the Overview tile group, not the hero. |
| KPI card — Impressions delivered | **MERGE** | Becomes the hero's sub-line ("415.1m verified of 427.7m expected"). |
| Rail — Blended CPM | **MOVE** | To Efficiency. It is a pricing metric, not a delivery metric. |
| Rail — Off rate card (20.0%) | **MOVE** | To Efficiency and campaign drill-down. Good metric, wrong altitude — negotiating well is unrelated to delivering. |
| Rail — Contracted to date vs full flight | **MERGE** | Into the hero sub-line and the proration explainer. |
| Rail — Delivery records (27,414) | **REMOVE** | A dataset-size statistic, not an analytical metric. Belongs in Method as build provenance. Answers no marketing question. |
| Filters (3 native selects) | **REPLACE** | Filter bar with custom dropdowns, status filter, search, active-filter chips. |
| Panel 01 — Under-delivering placements | **REPLACE** | Becomes the Attention Centre, split live/completed with different components and different ranking keys. |
| Panel 02 — Delivery against plan (monthly) | **REMOVE** | §3.2. Measures campaign count, not delivery. |
| Panel 03 — Cost efficiency by format | **IMPROVE** | Rank within analytically compatible groups only; digital separated; add delivered-vs-contracted CPM premium. |
| Panel 04 — Campaigns table (12 cols) | **REPLACE** | Campaign cards with pacing bars + full drill-down view. A 12-column table is a data dump, not an analysis. |
| "Why this exists" lede | **IMPROVE** | Becomes the compact reconciliation-timeline diagram. Same argument, one glance instead of two paragraphs. |
| Panel 05 — "How to use this" (4 steps) | **MERGE** | A product needing a four-step manual on the page has an IA problem. Content moves into `ⓘ` popovers and the hero line. |
| Panel 06 — "How it works" (3 tiles) | **MOVE** | To Method. |
| Panel 07 — Assumptions list | **MOVE + IMPROVE** | To Method, as the stepped 01–04 calculation walk-through with expandable formulas. |
| Footer | **KEEP** | Update stack line. |

### Metrics layer (`src/metrics.py`)

| Function | Verdict | Reasoning |
|---|---|---|
| `delivery_vs_contract` | **KEEP** | The core mechanism. Untouched. |
| `flight_progress` | **KEEP** | Untouched. |
| `spend_to_date` | **KEEP** | Untouched. |
| `cpm` | **KEEP** | Untouched. |
| `rate_efficiency` | **KEEP, demote in UI** | Sound metric, over-promoted as a headline card. |
| `daily_grp` | **KEEP, move to drill-down** | A planning metric, only loosely connected to the delivery thesis. Belongs in "Audience & pricing", marked modelled. |
| `reach_frequency` | **KEEP, move to drill-down** | Same. Keep the saturation-curve caveat visible. |
| `delivery_variance_ranked` | **IMPROVE** | Gains the live/completed partition and the new ranking keys. Threshold stays one source of truth. |

### Analytical SQL (`src/queries.sql`)

| Query | Verdict | Reasoning |
|---|---|---|
| 1 — Spend/delivery by client | **KEEP** | Clean aggregate baseline. |
| 2 — Worst 3 sites per campaign (`ROW_NUMBER`) | **KEEP** | Directly backs drill-down placement contribution. |
| 3 — Cumulative spend (`SUM OVER`) | **KEEP** | Backs the trajectory chart. |
| 4 — CPM by format | **IMPROVE** | Add the `is_digital` split so the query itself stops implying a cross-format ranking. |
| 5 — Sites across campaigns | **KEEP** | Directly backs Inventory. |
| 6 — Month-over-month by client (`LAG`) | **REPLACE** | Same calendar-month flaw as §3.2 — month-over-month across campaigns with different flights is not a performance comparison. Replace with a window-function query that keeps the `LAG`/window-function demonstration but asks a real question: shortfall concentration ranked within each campaign. |

---

## 5. Audit of proposed additions

Including the ones I proposed myself that did not survive.

| Addition | Verdict | Reasoning |
|---|---|---|
| Live vs completed split | **ADD** | Different ranking keys, different components, different actions. The core IA change. |
| Preventable exposure ($60,048) | **ADD** | The only metric that makes "live" operationally different rather than differently labelled. Modelled; assumption stated. |
| Required recovery pace | **ADD, reframed** | Ships with the honest framing: a healthy face delivers 0.96–1.05× of plan, so a required 1.17× is not something the booked face can do. |
| Recoverability status bands | **REJECT** | Collapses on contact with the data: required pace on the live set runs 1.06–2.30×, so every flagged live placement lands in "cannot recover unaided". A category with one occupied bucket is not a category. The number plus the sentence says it better. |
| Delivery index | **MERGE** | Algebraically the same as variance (`index = 1 + variance/100`). Useful as internal plumbing; showing both would be two names for one number. |
| Projected end-of-flight shortfall | **MERGE** | Same persistence assumption as preventable exposure. Appears as one clause in the live-issue sentence, not as a separate metric with a separate card. |
| Gross vs net shortfall | **ADD — headline** | §3.3. Strongest available analytic, zero new data. |
| Shortfall concentration (top-N share) | **ADD** | Deterministic, drives the computed callouts (campaign 8: five placements = 72% of gross). |
| Market / format / placement contribution | **ADD** | Core to "which market is responsible". Data strongly supports it — Toronto is 73% of campaign 8's net shortfall. |
| Downtime decomposition | **ADD at drawer level** | §3.4. Minor cause, honest diagnostic, wrong size for a panel. |
| Inventory reliability | **ADD, with its own null result** | §6. Ships the chance baseline alongside the ranking. |
| Watch / early-warning tier | **REJECT** | §3.1. 128 healthy placements, zero real faults. |
| Campaign exception reporting | **MERGE** | This is what the Attention Centre is. A second name for it would be duplication. |
| Sparklines / micro-trend charts | **REJECT** | One health multiplier per placement across the whole flight means there is no temporal signal to draw. |
| Map of under-delivering sites | **REJECT** | Visually impressive, decision-neutral: city is already the actionable geographic unit, and a pin scatter inside Toronto changes nothing about what anyone does. Fails question 4. |
| Media-owner dimension | **DEFER** | Legitimate OOH analysis question, but adds a dimension without adding an answer the product lacks, and edges toward vendor management. Revisit only if the inventory view proves it needs it. |

---

## 6. Metric register

Every metric the redesigned product exposes, with its classification. Formulas live in
`metrics.py` with hand-verifiable unit tests; none is computed in JavaScript.

| Metric | Marketing question | Formula | Class |
|---|---|---|---|
| Contracted to date | What was owed by today? | `contracted × elapsed / flight_days` | Calculated |
| Delivery variance | Are we behind where we should be? | `(verified − contracted_to_date) / contracted_to_date` | Calculated |
| Gross shortfall | How much is actually missing, before netting? | `Σ max(0, contracted_to_date − verified)` | Calculated |
| Masked by over-delivery | How much does the campaign number hide? | `Σ max(0, verified − contracted_to_date)` | Calculated |
| Spend to date | What have we billed so far? | `rate × elapsed / 28` | Calculated |
| Billed shortfall value | What is the shortfall worth? | `shortfall × contracted CPM / 1000` | Calculated |
| Remaining contracted | What is still owed? | `contracted − verified` | Calculated |
| Required daily delivery | What must it now do per day? | `remaining / remaining_days` | Calculated |
| Required recovery pace | What would finishing whole take? | `required_daily / planned_daily` | Calculated |
| Daily bleed | What does each unfixed day cost? | `planned_daily × (1 − delivery_index)` | Calculated |
| **Preventable exposure** | What does acting today still save? | `daily_bleed × remaining_days × contracted CPM / 1000` | **Modelled** |
| Shortfall concentration | How few placements cause most of it? | top-N share of gross shortfall | Calculated |
| Market / format contribution | Which market or format drives it? | share of campaign net shortfall | Calculated |
| Downtime-attributable loss | How much is explained by outages? | `estimated × downtime_hours / (24 × days)` | Calculated |
| Site delivery history | Does this site deliver when we book it? | `Σ verified / Σ contracted_to_date` per site | Calculated |
| CPM | What did a thousand impressions cost? | `spend / verified × 1000` | Calculated |
| CPM premium | How much did under-delivery inflate it? | `delivered CPM / contracted CPM` | Calculated |
| Rate efficiency | How far under rate card did we buy? | `1 − negotiated / rate_card` | Calculated |
| Reach / frequency / showing | How many people, how often? | saturation curve, per market | **Modelled** |

**The one modelled metric that needs its assumption stated on screen.** Preventable
exposure assumes the current shortfall rate persists across the remaining flight. In
this dataset that is true by construction (constant health multiplier), which makes it
exactly right here and an assumption anywhere else. The UI says so; `assumptions.md`
documents it. If fault onset dates are added (§7), it becomes a genuine assumption and
the wording must change with it.

---

## 7. Generator changes — evaluated, not assumed

| Change | Verdict | Reasoning |
|---|---|---|
| **Fault onset dates** | **RECOMMEND** | The strongest available change. Today a fault exists from day 1 of the flight, so "we caught it early" is unmeasurable. With an onset date, the product can state **time to detection**: "this placement went dark on day 12 and crossed the flag line on day 19 — seven days, against 47 days under end-of-campaign reconciliation." That is the project's central claim, made measurable instead of asserted. It also makes the trajectory chart informative and unlocks recovery events. Cost: every published figure changes; `README.md` and `assumptions.md` need rewriting in the same change. |
| **Recovery events** | **RECOMMEND (with onset)** | A fault that is fixed mid-flight makes detect → act → recover visible, and gives the live/completed distinction something to point at. Low marginal cost once onset exists. |
| **Latent site quality** | **RECOMMEND (lower priority)** | Required before inventory reliability means anything: 8 sites are flagged twice against **10.2 expected by chance**, so repeat under-delivery here is currently coincidence. Either add persistent site quality, or ship the panel reporting its own null result — both are honest; the first is more useful. |
| **Digital loop share** | **DEFER** | Done properly it cuts digital impressions ~6–8×, pushing digital CPM to roughly $90–120 and the blended CPM out of the documented CAD 8–15 band unless digital rate cards are recalibrated in the same change. Half-done it is less defensible than the current documented caveat. Its own phase. |
| **Weekday/weekend variability** | **DEFER** | Would break straight-line proration, which is currently *exactly* right because contracted impressions are generated flat. It would require replacing proration with a delivery curve — i.e. rebuilding the core mechanism. Already on the README roadmap; keep it there. |
| **Media owner** | **NO (for now)** | §5. |
| **Location coordinates** | **NO** | §5. Decoration. |

**Recommended sequence:** fault onset + recovery events together (one coherent change,
one documentation rewrite), latent site quality second, loop share as a separate later
phase.

---

## 8. The analytical journey

| Stage | Where it happens | The number that drives it |
|---|---|---|
| Portfolio overview | Overview hero | 97.1% delivery to plan, with 17.1m gross shortfall beneath it |
| Detect | Overview health bar + campaign pacing | 24 live / 37 completed; elapsed vs delivered bars |
| Prioritize | Attention Centre, live queue | Preventable exposure, ranked; 11 issues hold $53.5K of $60.0K |
| Investigate | Campaign drill-down → market / format / placement | Toronto = 73% of campaign 8's net shortfall |
| Understand impact | Everywhere money appears | Billed shortfall value + preventable exposure, never added together |
| Assess actionability | The live/completed split itself | Required recovery pace, days remaining |
| Reconcile | Completed queue + Efficiency | $101,588 across 37 closed placements; CPM premium |

Every surface in `design-spec.md` sits on exactly one of those rows. Anything that did
not was cut in §4 or §5.

---

## 9. Required corrections to `design-spec.md`

1. **Product name.** The spec titled the product "Delivery Monitor" in its heading and
   nav brand. The project is the **OOH Campaign Analyzer** and stays so — the nav brand
   reads `OOH Campaign Analyzer`, and "Delivery Monitor" survives only as the internal
   name of the design system, not as a product name.
2. **Remove the Watch tier** from the hero band, the status vocabulary and the health
   bar. Three segments: On track 534, Live issue 24, Completed shortfall 37.
3. **Reassign amber** from "Watch" to the materiality split inside the live queue
   (11 issues ≥ $1,000 preventable, 13 below).
4. **Re-validate** the health bar with three segments rather than four.
5. **Add gross-vs-net** to the Overview hero band and the campaign card.

---

## 10. Decisions — approved

1. **Theme** — light-first with a persisted dark toggle. Light mode uses refined
   neutral surfaces, not pure white. Both themes are designed, not flipped.
2. **Brand** — graphite/neutral chrome, blue as the single brand and interaction
   accent, kept strictly separate from status colour. Green on track, coral/red needs
   attention, grey completed, amber only where a genuine caution state exists. The
   Watch tier is **not** recreated to give amber something to do.
3. **Campaign names** — added as a human-readable field, with client, objective and
   dates kept separate, so hierarchy reads `Signal Everywhere` /
   `Nimbus Telecom · Product launch`.
4. **Generator** — fault onset dates, recovery events and state-dependent daily
   variation. **Latent persistent site quality is explicitly not added**, so the
   inventory view continues to report its null result rather than ranking noise
   (§7, §3.1 reasoning unchanged).

### What the generator change is for

To make the central product claim *measurable* rather than asserted: the analyzer
detects delivery problems while campaigns are still active, before end-of-campaign
reconciliation. That requires faults to begin on a day.

**Constraint carried into the implementation:** the analyzer derives faults from the
delivery series alone. Ground-truth fault labels are never written to `ooh.db`, never
exported, and never read by the UI. They exist only so the generator can report how
well the detector recovers them.
