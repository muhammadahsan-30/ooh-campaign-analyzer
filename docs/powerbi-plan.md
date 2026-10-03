# Power BI companion — specification

**Status: NOT BUILT.** This is a specification for a report that does not yet exist. No
`.pbix` file is in this repository, no screenshots of it exist, and nothing in the README
or the portfolio claims a Power BI implementation. When it is built in Power BI Desktop
and tested, this file gets a results section and the claim can be made — not before.

Decided in `docs/visual-analytics-recommendation.md` §18 (Recommendation B). The web app
stays the primary product; this is a second surface with a different job.

---

## 1. The division of labour

> **The web app is the monitoring product** — what needs attention today, and what acting
> would mean.
>
> **The Power BI report is the analysis surface** — why the portfolio is behind, explored
> in whatever order the analyst wants to ask.

Nothing is built twice. Specifically **not** rebuilt in Power BI: the Attention Centre
queues and their action copy, campaign pacing bars, the fault-detection trajectory, the
methodology view.

## 2. Known blocker

**Power BI Desktop is Windows-only; this project is developed on macOS.** Building the
report needs a Windows machine or VM. Power BI Desktop itself is free; the constraint is
the operating system, not the licence.

If that is not available, **Tableau Public** is the macOS-native substitute that still
publishes a genuinely public link. Weaker keyword for Canadian agency roles, stronger as
a clickable artifact. Either way: **do not fabricate screenshots of a report that was
never built.**

## 3. Star schema

Five tables, two facts, three dimensions. Deliberately small — the model should be
readable at a glance, not a demonstration of how many tables can be related.

```
            DimDate (318 rows)                 DimCampaign (8 rows)
         date · year · month · week          campaign_id · campaign_name
         · day_of_week · is_weekend          · client · industry · objective
                   │                          · start_date · end_date
                   │                                   │
                   ▼                                   ▼
        FactDelivery (27,414) ──────────► FactPlacement (595) ◄────── DimSite (120)
        date · placement_id               placement_id · campaign_id        site_id · city
        · verified_impressions            · site_id · contracted_impressions · area · format
        · estimated_impressions           · contracted_to_date · verified_to_date · is_digital
        · downtime_hours                  · spend_to_date · flight_days · elapsed_days
                                          · remaining_days · status · variance_pct
                                          · onset_day · alert_day · recovery_day
                                          · detection_delay_days · required_daily
                                          · planned_daily · preventable_exposure
```

**Relationships** — all single-direction, all one-to-many, no bidirectional filters:

| From | To | Cardinality |
|---|---|---|
| `FactDelivery[placement_id]` | `FactPlacement[placement_id]` | many → one |
| `FactDelivery[date]` | `DimDate[date]` | many → one |
| `FactPlacement[campaign_id]` | `DimCampaign[campaign_id]` | many → one |
| `FactPlacement[site_id]` | `DimSite[site_id]` | many → one |

`FactPlacement` is a **fact with attributes**, not a dimension: it carries additive
measures at placement grain. The precomputed detection columns ride on it because they
are sequential rather than additive (§5).

`DimDate` is marked as the date table. 318 distinct delivery dates across two calendar
years; generate the full continuous range so time intelligence behaves.

## 4. Export

`src/export_powerbi.py` (not yet written) writes five CSVs to `powerbi/data/` **from the
same SQLite database and the same `metrics.py` functions the web app uses**. The BI model
and the dashboard are fed by one pipeline, not two — which is what keeps the definitions
from drifting.

## 5. What is reproduced in DAX, and what is not

**Reproduce in DAX** — additive and ratio measures. These demonstrate real modelling and
can be validated against Python:
contracted to date · verified impressions · delivery variance % · gross shortfall ·
over-delivery offset · net shortfall · masked shortfall % · media-value exposure ·
placement and flagged counts.

**Keep precomputed in Python** — sequential measures:
fault onset day · alert crossing day · recovery day · detection delay ·
reconciliation delay · days remaining at detection · required recovery pace ·
preventable exposure.

The reason is technical and worth stating in the report itself: fault onset is *the first
day of the first run of three consecutive days below 90% of plan*. Run-detection over an
ordered partition is natural in Python and painful and slow in DAX. Reimplementing it
would demonstrate stubbornness, not skill.

## 6. Proposed DAX

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

Net Shortfall      = [Gross Shortfall] - [Over-delivery Offset]
Masked Shortfall % = DIVIDE ( [Over-delivery Offset], [Gross Shortfall] )

-- NOTE the filter. This is the FLAGGED population (82 placements), which is a
-- different measure from Total Negative Delivery Exposure below. See section 7.
Flagged Media-Value Exposure =
SUMX ( FILTER ( FactPlacement, FactPlacement[status] <> "on_track" ),
       VAR Short = FactPlacement[contracted_to_date] - FactPlacement[verified_to_date]
       RETURN IF ( Short > 0,
                   Short * DIVIDE ( FactPlacement[spend_to_date],
                                    FactPlacement[contracted_to_date] ), 0 ) )

-- Every placement behind by any amount (227), matching the population that
-- Gross Shortfall is measured over.
Total Negative Delivery Exposure =
SUMX ( FactPlacement,
       VAR Short = FactPlacement[contracted_to_date] - FactPlacement[verified_to_date]
       RETURN IF ( Short > 0,
                   Short * DIVIDE ( FactPlacement[spend_to_date],
                                    FactPlacement[contracted_to_date] ), 0 ) )

Live Issues          = CALCULATE ( COUNTROWS ( FactPlacement ), FactPlacement[status] = "live_issue" )
Completed Shortfalls = CALCULATE ( COUNTROWS ( FactPlacement ), FactPlacement[status] = "completed_shortfall" )
Flagged Placements   = [Live Issues] + [Completed Shortfalls]
Placements Behind    = CALCULATE ( COUNTROWS ( FactPlacement ), FactPlacement[variance_pct] < 0 )
```

## 7. The naming rule these measures inherit

Two populations, two names, enforced across Python, SQL, the interface and DAX alike:

| Name | Population | Value |
|---|---|---|
| **Flagged media-value exposure** | the 82 placements past the −5% attention line | CAD 117,058 |
| **Total negative delivery exposure** | all 227 placements behind by any amount | CAD 134,655 |

Gross shortfall, over-delivery offset and net shortfall are all measured over the
**behind** population, so they are comparable with the second figure, not the first.
A draft SQL query written during the audit summed exposure over all 227 and compared it
against Python's 82 — a CAD 17,598 gap that looks like a reconciliation failure and is
actually a definitional one. Documented in `docs/assumptions.md` and at the top of
`src/queries.sql`.

## 8. Validation plan

Python stays authoritative. Every DAX duplicate is checked against it and the result
published in the report itself.

| Metric | Python | SQL | Power BI (DAX) | Match |
|---|---|---|---|---|
| Spend billed to date | 5,408,751 | 5,408,751 | *pending* | Python = SQL ✅ |
| Gross shortfall | 10,532,493 | 10,532,493 | *pending* | Python = SQL ✅ |
| Over-delivery offset | 1,481,999 | 1,481,999 | *pending* | Python = SQL ✅ |
| Net shortfall | 9,050,494 | 9,050,494 | *pending* | Python = SQL ✅ |
| Masked shortfall % | 14.07% | 14.07% | *pending* | Python = SQL ✅ |
| Flagged media-value exposure | 117,058 | 117,058 | *pending* | Python = SQL ✅ |
| Total negative delivery exposure | 134,655 | 134,655 | *pending* | Python = SQL ✅ |
| Flagged placements | 82 | 82 | *pending* | Python = SQL ✅ |

Tolerance: exact to the dollar and the impression; percentages to two decimals.

## 9. Report pages

### Page 1 — Executive campaign health
The portfolio in under 30 seconds, for someone who does not know OOH. KPI row with a
plain-English subtitle under every label · gross-to-net waterfall · ranked campaign
contribution · campaign × market heatmap · live vs completed split.

### Page 2 — Root cause explorer
**Decomposition tree** on media-value exposure — the one capability the web app cannot
offer, because the user chooses the drill order. Slicers for campaign, market, format and
status · **field parameter** switching the analysed measure between exposure, gross
shortfall and placement count · **drill-through** to a placement detail page ·
**tooltip page** with a mini trajectory on hover.

### Page 3 — Flight & detection
Cumulative expected against actual by flight day · fault onset, alert crossing and
recovery as markers · detection delay against reconciliation delay · remaining flight at
detection · required recovery pace. All precomputed in Python, visualised here.

## 10. Publishing

| Route | Viable | Note |
|---|---|---|
| Screenshots in `powerbi/` + README | ✅ | The reliable baseline |
| Short interaction GIF | ✅ | Best value-per-effort — shows the decomposition tree responding |
| `.pbix` committed to the repo | ✅ | Evidence, not the primary artifact; most recruiters cannot open it |
| Publish to web (public link) | ⚠️ | Needs Pro/PPU **and** tenant enablement. Verify before promising a link |
| Power BI Service share link | ❌ | Viewer needs a licence and tenant access — a dead end |

Publishing is **safe** here in a way it usually is not: the dataset is entirely synthetic
with invented brands, so there is no confidentiality objection. Worth stating on page 1
of the report.

**Rule: never publish a link a recruiter cannot open.**

## 11. Definition of done

- [ ] `src/export_powerbi.py` writes five CSVs from the existing pipeline
- [ ] Model built with the relationships in §3, `DimDate` marked as the date table
- [ ] DAX measures from §6 implemented
- [ ] §8 validation table completed — every row matching Python
- [ ] Three pages built per §9
- [ ] Screenshots and a GIF committed under `powerbi/`
- [ ] README and portfolio updated **only then**, describing what actually exists
