# Visual analytics & Power BI recommendation

Evaluation only — **nothing in this document is built yet.** It audits the shipped
application against four audiences, compares three directions, and recommends one.

Companions: `docs/product-audit.md` (component reasoning), `docs/design-spec.md` (the
visual system), `docs/assumptions.md` (methodology).

The single test everything below is optimised against:

> Can someone who has never worked in marketing open this project and visually
> understand what went wrong, why it matters, and where to look next?

---

## 0. What the audit actually measured

Counted on the shipped build, per view:

| View | Tables | Rows | SVG charts | Bar visuals | Standalone numbers |
|---|---|---|---|---|---|
| Overview | 0 | 0 | **0** | 23 | 12 |
| **Attention** | 1 | 61 | **0** | **0** | **105** |
| Campaigns (list) | 0 | 0 | 0 | 16 | 8 |
| **Markets** | **2** | 10 | **0** | **0** | 0 |
| Inventory | 1 | 40 | 0 | 0 | 0 |
| Efficiency | 0 | 0 | 0 | 7 | 1 |
| Method | 0 | 0 | 0 | 0 | 0 |

Three facts fall out of that table and drive most of this document:

1. **There is exactly one chart in the entire product** — the campaign trajectory, which
   lives two clicks deep inside campaign drill-down. Every other "visual" is a CSS bar.
2. **The Attention Centre carries 105 standalone numbers and zero visuals.** It is the
   view the product is named for, and it is read entirely numerically.
3. **The Markets view is two bare tables.** Market contribution is inherently spatial and
   comparative, and it is currently the least visual thing in the product.

### A promise the spec made and the build did not keep

`docs/design-spec.md` §13 specified a three-tier progressive disclosure — value, then an
`ⓘ` popover with the plain-English reading, then a methodology link. **`app.js` contains
zero implementations of it.** That is the exact mechanism non-marketing users need, it
was designed, and it was never built. It is the highest-value gap in the product.

---

## 1. Current visualization strengths

- **The campaign pacing bars are genuinely good.** Two bars on one 0–100% scale, with the
  gap between their ends being the pacing gap, is understandable without instruction.
- **The health bar decomposes the hero figure** immediately beneath it, so "97.9%" and
  "but 82 placements are flagged" arrive together.
- **The trajectory chart is honest and well-annotated** — flight-day x-axis, a direct
  "1.8m short" label, fault onsets marked on the axis.
- **Colour is disciplined.** One analytic hue, a fixed status vocabulary, validated for
  colour-vision deficiency, never carrying meaning alone.
- **Ranked contribution bars** on Overview and drill-down answer "where is it worst"
  correctly and without decoration.

## 2. Current visualization weaknesses

| Weakness | Where | Why it matters |
|---|---|---|
| The signature finding exists only as a sentence | Overview, campaign cards | Gross → offset → net is the project's strongest idea and is currently prose plus two numbers. It is inherently a waterfall. |
| 105 numbers, no visual | Attention Centre | "−21.2% · 46% of plan · 20 days left · 168% recovery pace" is four numbers a non-marketer cannot rank or picture |
| Two bare tables | Markets | Campaign × market interaction is invisible; you cannot see that Toronto is bad *across* campaigns |
| No concentration visual | Attention, Markets | The data strongly supports Pareto (top 5 placements = 72–80% of campaign shortfall) and the product never shows it |
| The product's purpose is text | Overview "Why this exists" | Fault → detection → intervention window → campaign end is a timeline, drawn as two rows of words |
| Only one chart, buried | whole app | A viewer who never opens a campaign sees no chart at all |

## 3. Where non-marketing users struggle

The app currently assumes the reader knows: **flight, placement, impression, contracted,
delivery, variance, pacing, CPM, rate card, showing/GRP, reach, frequency, make-good,
reconciliation, masking, exposure.** A glossary exists — in the README, not in the app.

Audited against each audience:

**Non-marketing recruiter.** Can they tell what a campaign is? Partly — campaign names and
client/objective help. What a placement is? **No** — "Toronto · Digital screen ·
Scarborough" is only meaningful if you know a placement is one physical advertising site
booked for one campaign. What "delivery" means? **No** — nothing says impressions are
estimated audience, not clicks or sales. Why averages hide problems? **Yes**, the "…but"
line does this well. What media-value exposure means? **No** — nothing says it is not a
refund. Actionable vs completed? **Yes**, that distinction is clear.

**Marketing / media professional.** Well served. Portfolio → campaign → market → placement
works, filters work, the Attention Centre is ranked correctly for their workflow. The one
gap is comparison *across* campaigns — there is no view where eight campaigns' shapes sit
side by side.

**BI / analytics hiring manager.** Sees data modelling (4 normalised tables), KPI design,
SQL with window functions, a tested Python layer, and custom frontend. Does **not** see:
a semantic model, interactive cross-filtering, root-cause drill, or any named BI tool.
For a BI-titled role, the project currently reads as "analytics engineering + product",
not "business intelligence".

**General user.** Can follow the story from the hero band — that part works. Loses the
thread at the Attention Centre, where the narrative becomes a wall of figures.

---

## 4. Visuals that should be added to the web app

Each with the question it answers and why a visual beats the current treatment.

### P0-1 · Gross-to-net waterfall
**Question:** "How does 10.5m of missing audience become a −2.1% campaign number?"
**Why visual:** A waterfall is the canonical form for *this exact* arithmetic — a starting
bar, a reducing bar, a resulting bar. Today it is a sentence. On campaign *Doors Open
Saturday* it would show 106,841 gross → 87,000 offset → 19,000 net, and the 81% masking
becomes obvious rather than asserted. **Placement:** Overview (portfolio) and campaign
drill-down (per campaign). **Data:** exact, already exported.

### P0-2 · The plain-English layer (`ⓘ`) and an in-app glossary
**Question:** "What does this word mean?"
**Why:** This is the single biggest non-marketing-user win and it was already designed.
Three tiers exactly as specced: the value; a one-sentence plain reading; a link into
Method. Plus a short glossary panel in Method covering the fifteen terms listed in §3.
Example wording:
- *Delivery vs plan* — "How far ahead or behind this placement is against where it should
  be today."
- *Gross shortfall* — "Audience that was missed, counting only the sites that fell behind.
  Sites that over-delivered are not subtracted here."
- *Media-value exposure* — "The value of the media attached to the missing audience. It is
  not automatically a refund or a loss."

### P0-3 · Mini planned-vs-actual bar inside each live issue card
**Question:** "How far behind is this, at a glance?"
**Why visual:** 105 numbers become scannable. One two-row bar per card — expected to date
vs verified — reusing the pacing component already on campaign cards, so no new visual
language. **Data:** already in the payload.

### P0-4 · Flight timeline: fault → detection → intervention window → end
**Question:** "What is this product actually for?"
**Why visual:** This is the thesis. One horizontal timeline with four marks and a shaded
"intervention window" explains the whole project faster than the two-column word diagram
currently there. Uses real medians: fault begins, flagged 2.5 days later, 38 days of
usable flight remain, reconciliation would have found it at day 31. **Placement:**
Overview, replacing the current "Why this exists" columns; repeated in Method.

### P1-5 · Campaign × market heatmap
**Question:** "Is Toronto bad everywhere, or bad on one campaign?"
**Why visual:** An 8 × 6 grid is small, dense and readable, and it answers an interaction
question two separate tables structurally cannot. **Placement:** Markets, above the
existing tables (which stay — analysts need the precision).

### P1-6 · Pareto on exposure
**Question:** "How few placements do I actually need to fix?"
**Why visual:** The data supports it unusually well — five placements carry 72–80% of a
campaign's gross shortfall. A Pareto turns "82 flagged placements" into "fix 11 and you
have addressed most of the money", which is a decision. **Placement:** Attention Centre
header, above the live queue.

### P2-7 · Small multiples of campaign pacing
**Question:** "Which campaigns are shaped differently?"
Eight sparkline-sized trajectories in a row. Legitimate now that faults have onset dates
and the trajectories genuinely differ. Lower priority because the pacing board already
answers most of it.

## 5. Visuals that should be removed or replaced

**Nothing should be removed.** The audit found no decorative or misleading visual in the
shipped build — the weak ones were already cut in `product-audit.md` (the monthly chart,
the Watch tier, the cross-format CPM ranking).

Two **replacements**, not removals:
- The "Why this exists" two-column word diagram → the flight timeline (P0-4).
- The Markets view's two tables → heatmap **above** the tables, tables retained.

### Explicitly NOT to be built

| Visual | Why not |
|---|---|
| **Sankey / flow diagram** | Nothing here is a flow. Shortfall contribution is a partition, not a transfer between states. It would look impressive and mean nothing. |
| **Treemap** | At six markets and four formats, bars are more precise and already in place. A treemap would be a worse bar chart. |
| **Scatter: spend vs delivery variance** | There is no relationship to find, **by construction**: `plan_faults()` draws faulted placements with `random.sample` independently of rate card or spend. The chart's honest message would be "no pattern", which does not earn a panel. |
| **Decomposition tree in the web app** | This is Power BI's job (§6). Rebuilding it in vanilla JS would be a weak copy of a tool that does it natively. |
| **Any donut or pie** | Already excluded by the design system. |
| **Gauges / speedometers** | Same. |
| **A second hero number per view** | The one-hero rule is load-bearing for the hierarchy. |

---

## 6. Should Power BI be added? — Yes, as a separate companion

**Recommendation: yes**, but not because it was asked about. Three reasons it earns its
place, and one real blocker.

### Why it earns its place

**1. It answers a question the web app structurally cannot.** The web app has fixed drill
paths: portfolio → campaign → market/format → placement. A decomposition tree lets a user
choose their own path — exposure → format → market → campaign → placement, or any other
order — and have the tool rank each level by contribution. Building that in vanilla JS is
days of work for a worse version of something Power BI does natively.

**2. The data model is already a star schema waiting to happen.** 4 normalised tables,
clean grain, 318 distinct dates. This is not a case of bending a dataset to fit a tool.

**3. It closes the one real audience gap.** For a BI-titled role the project currently
shows no BI tool and no semantic model. Power BI plus a validated DAX layer closes that
gap precisely.

### The blocker, stated plainly

**Power BI Desktop is Windows-only, and this project is developed on macOS.** There is no
native Mac build and the browser-based service cannot do full model and DAX authoring.
Building the report therefore requires a Windows machine or VM. That gates the work — it
does not change whether the work is worth doing, but it must be planned for rather than
discovered.

If Windows access is not realistically available, the honest alternative is **Tableau
Public** — free, runs natively on macOS, and publishes a genuinely public live link.
It demonstrates BI modelling and visual analytics, though "Power BI" is the stronger
keyword for Canadian agency and media-analytics roles. **Do not fake a Power BI artifact
with screenshots of something never built.**

## 7. What Power BI adds that the web app does not

| # | Question | Answer |
|---|---|---|
| 1 | **Analytical questions it answers better** | Free-form root cause ("show me exposure broken down however the data says is most explanatory"); ad-hoc cross-filtering (click Toronto, every visual refilters); multi-dimension comparison in one view |
| 2 | **Power BI-specific skills demonstrated** | Star-schema modelling, relationship design, DAX measures, field parameters, drill-through pages, decomposition tree, tooltip pages, bookmarks |
| 3 | **Views that would be redundant** | Attention Centre queues, campaign pacing board, the methodology view, the Overview hero. **Do not rebuild these.** |
| 4 | **Views that stay web-only** | The entire monitoring workflow: Attention Centre with its action copy and recovery-pace sentences, the fault-detection timeline, filters-plus-drawer interaction, light/dark product experience |
| 5 | **How it appears** | Repo folder + screenshots + a short interaction GIF, linked from the README and the portfolio projects page. A live public link **only** if publishing actually works (§11) |
| 6 | **Licensing constraints** | "Publish to web" requires Power BI Pro or PPU **and** tenant admin enablement; a free account cannot publish publicly. Power BI Desktop itself is free |
| 7 | **Is public embedding appropriate?** | **Yes, uniquely so** — the dataset is entirely synthetic with invented brands, so the usual confidentiality objection to publishing a BI report does not apply. This is worth stating in the report itself |
| 8 | **Resume value** | Material. It converts the project from "Python analytics + custom frontend" to "end-to-end analytics: modelling, BI, and product", and enables the three-way validation story below |

## 8. Division of responsibility

The two artifacts must have different jobs. One sentence each:

> **The web app is the monitoring product** — it tells you what needs attention today and
> what acting would mean.
>
> **The Power BI report is the analysis surface** — it lets you interrogate why the
> portfolio is behind, in whatever order you want to ask.

| Capability | Web app | Power BI |
|---|---|---|
| Attention queues, action copy | ✅ only | ❌ |
| Fault detection timeline | ✅ only | shows precomputed results |
| Pacing against plan | ✅ only | ❌ |
| Executive one-screen summary | partial | ✅ primary |
| Free-form root-cause drill | ❌ | ✅ only |
| Cross-filtering by click | ❌ | ✅ only |
| Decomposition tree | ❌ | ✅ only |
| Methodology and assumptions | ✅ only | links back |

## 9. Proposed Power BI pages

### Page 1 — Executive campaign health
*Goal: the portfolio in under 30 seconds, for someone who does not know OOH.*
KPI row (delivery vs plan, gross shortfall, net shortfall, masking %, exposure, live vs
completed) · **gross-to-net waterfall** · ranked campaign contribution · campaign × market
heatmap · a plain-English subtitle under every KPI.

### Page 2 — Root cause explorer
*Goal: let the user find the driver themselves.*
**Decomposition tree** on media-value exposure · slicers for campaign / market / format /
status · **field parameter** to switch the analysed measure between exposure, gross
shortfall and placement count · contribution bars · placement detail table ·
**drill-through** to a placement page · **tooltip page** showing a mini trajectory on hover.

### Page 3 — Flight & detection
*Goal: explain early detection.*
Cumulative expected vs actual by flight day · fault onset, alert crossing and recovery as
markers · detection delay vs reconciliation delay as a comparison bar · remaining flight
days at detection · required recovery pace. Precomputed in Python, visualised here.

## 10. Proposed star schema

Deliberately small — five tables, two facts, three dimensions.

```
            DimDate (318 rows)          DimCampaign (8 rows)
          date, year, month,          campaign_id, campaign_name,
          week, day_of_week           client, industry, objective,
                 │                    start_date, end_date
                 │                            │
                 ▼                            ▼
        FactDelivery (27,414) ─────► FactPlacement (595) ◄──── DimSite (120)
        date, placement_id,          placement_id, campaign_id,      site_id, city,
        verified_impressions,        site_id, contracted_impressions, area, format,
        estimated_impressions,       contracted_to_date, verified_to_date,         is_digital
        downtime_hours               spend_to_date, flight_days, elapsed_days,
                                     status, variance_pct,
                                     onset_day, alert_day, detection_delay_days
```

Relationships: `FactDelivery[placement_id] → FactPlacement[placement_id]` (many-to-one),
`FactPlacement[campaign_id] → DimCampaign`, `FactPlacement[site_id] → DimSite`,
`FactDelivery[date] → DimDate`. All single-direction, all one-to-many.

`FactPlacement` is a **fact with attributes**, not a dimension: it carries the additive
measures at placement grain. The precomputed detection columns ride on it because they are
sequential, not additive — see §11.

**Export:** `src/export_powerbi.py` would write five CSVs to `powerbi/data/` from the same
SQLite database and the same `metrics.py` functions, so the BI model and the web app are
fed by one pipeline rather than two.

## 11. Proposed DAX measures — and what should *not* be DAX

**The decision: hybrid.** Reproduce the *additive and ratio* measures in DAX (they
demonstrate real modelling skill and can be validated). **Consume the *sequential* ones
precomputed from Python.**

The reason is technical and worth stating in the report: fault onset is "the first day of
the first run of three consecutive days below 90% of plan". Run-detection over an ordered
partition is painful and slow in DAX and natural in Python. Reimplementing it would
demonstrate stubbornness, not skill.

```dax
Verified Impressions = SUM ( FactDelivery[verified_impressions] )

Contracted To Date =
SUMX ( FactPlacement,
       FactPlacement[contracted_impressions]
       * DIVIDE ( FactPlacement[elapsed_days], FactPlacement[flight_days] ) )

Delivery Variance % =
DIVIDE ( [Verified Impressions] - [Contracted To Date], [Contracted To Date] )

Gross Shortfall =
SUMX ( FactPlacement,
       VAR Short = FactPlacement[contracted_to_date] - FactPlacement[verified_to_date]
       RETURN IF ( Short > 0, Short, 0 ) )

Over-delivery Offset =
SUMX ( FactPlacement,
       VAR Over = FactPlacement[verified_to_date] - FactPlacement[contracted_to_date]
       RETURN IF ( Over > 0, Over, 0 ) )

Net Shortfall     = [Gross Shortfall] - [Over-delivery Offset]
Masked Shortfall % = DIVIDE ( [Over-delivery Offset], [Gross Shortfall] )

Media Value Exposure =
SUMX ( FILTER ( FactPlacement, FactPlacement[status] <> "on_track" ),
       VAR Short = FactPlacement[contracted_to_date] - FactPlacement[verified_to_date]
       RETURN IF ( Short > 0,
                   Short * DIVIDE ( FactPlacement[spend_to_date],
                                    FactPlacement[contracted_to_date] ), 0 ) )

Live Issues           = CALCULATE ( COUNTROWS ( FactPlacement ), FactPlacement[status] = "live_issue" )
Completed Shortfalls  = CALCULATE ( COUNTROWS ( FactPlacement ), FactPlacement[status] = "completed_shortfall" )
Flagged Placements    = [Live Issues] + [Completed Shortfalls]
```

**Stays precomputed in Python, never reimplemented in DAX:** fault onset day, alert
crossing day, recovery day, detection delay, reconciliation delay, days remaining at
detection, required recovery pace, preventable exposure.

## 12. Validation plan — and why it matters, demonstrated

Python remains authoritative. Any DAX duplicate must be checked against it.

| Metric | Python | SQL | Power BI (DAX) | Match |
|---|---|---|---|---|
| Spend billed to date | 5,408,751 | 5,408,751 | *to verify* | ✅ Python = SQL |
| Gross shortfall | 10,532,493 | 10,532,493 | *to verify* | ✅ Python = SQL |
| Over-delivery offset | 1,481,999 | 1,481,999 | *to verify* | ✅ Python = SQL |
| Net shortfall | 9,050,494 | 9,050,494 | *to verify* | ✅ Python = SQL |
| Masked shortfall % | 14.07% | 14.07% | *to verify* | ✅ Python = SQL |
| Media-value exposure | 117,058 | 117,058 | *to verify* | ✅ Python = SQL |
| Flagged placements | 82 | 82 | *to verify* | ✅ Python = SQL |

Python and SQL were cross-checked while writing this document, and the exercise
immediately proved its own worth:

> A first SQL pass returned **$134,655** against Python's **$117,058** for media-value
> exposure — a $17,597 gap. Same formula, different population: the SQL summed all **227**
> placements behind by any amount, Python the **82** that breach the −5% flag line.
> Not a defect, but exactly the kind of silent divergence this table exists to catch, and
> the reason a DAX reimplementation must be validated rather than assumed.

That story — *three independent implementations, one reconciled definition* — is worth
more in an interview than any individual chart.

## 13. User education: the plain-English layer

Beyond the `ⓘ` tooltips (P0-2), three structural additions:

- **A glossary panel in Method**, covering the fifteen terms in §3, each in one sentence.
- **A one-line subtitle under every KPI label.** "Media-value exposure" gains "the value
  of media attached to the missing audience — not automatically a refund".
- **A 30-second "how to read this" strip** on first visit to Overview, dismissible, four
  steps mapping to the story sequence: we booked audience → the campaign number looks fine
  → individual sites fell behind → over-delivery hid it → here is what is still fixable.

Industry terms stay — a media professional should still see "flight" and "CPM". The plain
reading sits beside them, never replacing them.

## 14. Number and table density classification

| Element | View | Verdict |
|---|---|---|
| 97.9% delivery-to-plan hero | Overview | **KEEP AS NUMBER** — the single clearest statement |
| Health segmented bar | Overview | **KEEP** — already the right visual |
| Gross/masked/net sentence | Overview | **ADD VISUAL** — waterfall beside it (P0-1) |
| "Why this exists" word columns | Overview | **REPLACE WITH VISUAL** — flight timeline (P0-4) |
| Campaign pacing bars | Overview, Campaigns | **KEEP** — works |
| Live issue 4-number grid | Attention | **ADD VISUAL** — mini planned-vs-actual bar (P0-3) |
| Live issue ranking | Attention | **ADD VISUAL** — Pareto header (P1-6) |
| Completed shortfalls table | Attention | **KEEP AS TABLE** — reconciliation needs precision |
| Market contribution tables ×2 | Markets | **ADD VISUAL** — heatmap above; tables stay |
| Inventory site table | Inventory | **KEEP AS TABLE** — it is a history, and the null result is text |
| Inventory null-result callout | Inventory | **KEEP** — prose is correct here |
| Static CPM bars | Efficiency | **KEEP** — already visual |
| Digital CPM stat | Efficiency | **KEEP AS NUMBER** — one value |
| CPM premium bars | Efficiency | **KEEP** |
| Assumptions accordion | Method | **KEEP** — plus the glossary (P0-2) |
| Trajectory chart | Drill-down | **KEEP** — strongest existing chart |
| Market/format contribution bars | Drill-down | **KEEP** |

Nothing is classified **REMOVE**.

## 15. Publishing and embedding constraints

| Route | Works? | Notes |
|---|---|---|
| Power BI Desktop (.pbix) in repo | ✅ | Recruiters mostly cannot open it; include anyway as evidence, not as the primary artifact |
| Screenshots in `powerbi/` + README | ✅ | The reliable baseline. Always do this |
| Short interaction GIF | ✅ | Best value-per-effort — shows the decomposition tree actually responding |
| Publish to web (public link) | ⚠️ | Needs Pro/PPU **and** tenant enablement. Verify before promising a link |
| Embed in the portfolio site | ⚠️ | Same licence gate; iframe only works for a published-to-web report |
| Power BI Service share link | ❌ | Requires the viewer to have a licence and tenant access — a dead end for recruiters |

**Rule: never publish a link a recruiter cannot open.** If publish-to-web is unavailable,
ship screenshots plus a GIF and say plainly that the report is available on request.

## 16. Effort against portfolio value

| Item | Effort | Value | Ratio |
|---|---|---|---|
| P0-2 plain-English layer + glossary | S | **Very high** | ★★★★★ |
| P0-1 gross-to-net waterfall | S | **Very high** | ★★★★★ |
| P0-3 mini bars in issue cards | S | High | ★★★★☆ |
| P0-4 flight timeline | M | **Very high** | ★★★★★ |
| P1-5 campaign × market heatmap | M | High | ★★★★☆ |
| P1-6 Pareto | S | Medium-high | ★★★★☆ |
| Power BI star schema + export | M | High | ★★★★☆ |
| Power BI 3-page report | L | **Very high** (BI roles) | ★★★★☆ |
| DAX + validation table | M | **Very high** | ★★★★★ |
| P2-7 small multiples | M | Medium | ★★★☆☆ |

## 17. Priorities

**P0 — do first, unblocked, directly serves the stated goal**
1. Plain-English `ⓘ` layer + in-app glossary *(keeps a promise the spec already made)*
2. Gross-to-net waterfall, Overview and drill-down
3. Mini planned-vs-actual bars in live issue cards
4. Flight timeline replacing the "Why this exists" columns

**P1 — strong additions**
5. Campaign × market heatmap on Markets
6. Pareto on exposure in the Attention Centre
7. Power BI: star-schema export (`src/export_powerbi.py`), model, DAX, validation table,
   three pages, screenshots + GIF, `powerbi/` folder *(gated on Windows access)*

**P2 — only if they still feel missing**
8. Small multiples of campaign pacing
9. Field parameters and bookmarks in Power BI
10. Published-to-web link, if licensing permits

---

## 17b. Implementation status — P0 shipped

All four P0 items are built. Power BI is specified in `docs/powerbi-plan.md` and
deliberately **not** started.

| Item | Status | What shipped |
|---|---|---|
| P0-1 explain layer | ✅ | 110 info affordances across the product, 18 glossary terms, click/keyboard, Esc to close, three levels ending in a methodology link |
| P0-2 Attention Centre visuals | ✅ | Four-row comparison strip per live card: delivery vs expected, flight elapsed, planned vs needed daily pace, and the two money measures on one scale |
| P0-3 gross → offset → net waterfall | ✅ | Portfolio panel on Overview and a per-campaign waterfall in drill-down, each with a generated plain-English reading |
| P0-4 market contribution visual | ✅ | Campaign × market heatmap on Markets, with the ranked tables retained beneath for precision |
| P0-8 exposure definitions | ✅ | Two named measures exported, documented in `assumptions.md` and at the top of `queries.sql` |

### Decisions taken during implementation

- **Both the heatmap and the ranked bars ship**, which §4 left open. They answer different
  questions: the Overview bars rank *where it is worst overall*, the heatmap shows
  *whether a market is behind everywhere or on one campaign*. Toronto turns out to be
  behind on 8 of 8 campaigns — a systemic pattern the bars structurally cannot show.
- **The waterfall's offset bar is grey, not green.** Over-delivery is literally delivering
  more than promised, but in this chart it is the thing *hiding* the problem. Green would
  imply it is a win.
- **Exposure is two bars on one scale, never a stack.** Already-lost and still-preventable
  are different quantities; stacking them would assert a sum that does not exist.
- **Every lane carries its own label.** A first build had unlabelled paired bars — a
  reader could see two bars but not which was expected and which actual.
- **`.info` was renamed `.xpl`.** The new explain-button class collided with the existing
  `.callout.info` variant and was resizing that callout to 16×16px.

### Carried forward, not built

This document's own §4 proposed a **flight timeline** (fault → detection → intervention
window → campaign end) as a P0 item. The approved P0 list replaced it with the market
contribution visual, so it was not built. The "Why this exists" panel still carries the
two-column word diagram and the real medians in prose. It remains the strongest candidate
for the next visual pass, along with the Pareto (§4 P1-6) and small multiples (§4 P2-7).

### Rejected during implementation, as planned

Sankey, treemap, spend-vs-variance scatter, gauges, decorative maps, sparklines on
non-temporal data, forecasting lines and risk scores. None were built.

## 18. Final recommendation

### Recommendation B — web app plus a separate Power BI companion report

With one firm ordering condition: **P0 ships before Power BI starts.**

The reasoning is the single test at the top of this document. A non-marketing viewer's
comprehension is limited today by missing explanation and missing visuals *in the product
they will actually open* — not by the absence of a BI tool. The four P0 items are small,
unblocked, and fix exactly that. Starting with Power BI would add a second artifact while
the first still fails its most important test.

Power BI then earns its place as a genuinely different surface: the web app answers *what
needs attention today*, the report answers *why the portfolio is behind, explored in
whatever order you like*. They share one pipeline, one set of definitions, and a
validation table proving Python, SQL and DAX agree. Neither duplicates the other.

**Not Recommendation A**, because the BI-role audience gap is real and A leaves it open.
**Not Recommendation C**, because public embedding depends on a licence that has not been
confirmed, and committing to an embedded experience risks promising a link that does not
open.

**The one thing to confirm before scheduling P1:** whether a Windows machine or VM is
available. If not, Tableau Public is the macOS-native substitute that still publishes a
live link — weaker as a keyword, stronger as a clickable artifact.
