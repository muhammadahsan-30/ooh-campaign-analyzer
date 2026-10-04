# Power BI handoff — the one document to follow

Everything that could be prepared without logging in is done. This is the single sheet to
work from. Depth links at the bottom; you should not need them unless something disagrees.

**Environment:** macOS, browser only, Power BI Service at **app.powerbi.com**. No Desktop
required. Sign in with your `@uwaterloo.ca` address — Power BI does not accept personal
email.

**Estimated time:** 2–3 hours. Upload → relate → paste → place → verify.

---

## 0 · Do this first (30 seconds, determines the ending)

Open any report → **File** → look for **Embed report → Publish to web (public)**.

- **Clickable** → you can publish a public link at the end (step 6).
- **Greyed out / absent** → your tenant disabled it. Fine. You ship screenshots + a GIF
  instead. **Do not switch to Tableau over this** — the build is identical either way.

---

## 1 · Upload

**Create → Get data → Text/CSV.** Upload in this order so relationship detection has keys
to match. All six are in `bi/` in this repo.

| # | File | Table name | Expected rows |
|---|---|---|---|
| 1 | `bi/dim_date.csv` | `dim_date` | **505** |
| 2 | `bi/dim_campaign.csv` | `dim_campaign` | **8** |
| 3 | `bi/dim_site.csv` | `dim_site` | **120** |
| 4 | `bi/fact_placement.csv` | `fact_placement` | **595** |
| 5 | `bi/fact_delivery.csv` | `fact_delivery` | **27,414** |
| 6 | `bi/fact_detection_events.csv` | `fact_detection_events` | **102** |

On the last one choose **Create a semantic model only**. Name it `OOH Campaign Model`.

**Check row counts now.** A wrong count means a partial upload — re-upload that file.

**Check data types.** Every `*_date` and `date` column must be **Date**, not Text. Every
`is_*`, `in_flight`, `recovered` column must be **True/False**.

---

## 2 · Model

Switch **Viewing → Editing** (top right).

**Mark the date table:** right-click `dim_date` → *Mark as date table* → column `date`.

**Create five relationships** (ribbon → *Manage relationships* → *New*). Delete anything
auto-detected that is not in this table — it usually invents a second date relationship.

| From | Column | To | Column | Cardinality | Cross-filter |
|---|---|---|---|---|---|
| `fact_placement` | `campaign_id` | `dim_campaign` | `campaign_id` | Many to one | **Single** |
| `fact_placement` | `site_id` | `dim_site` | `site_id` | Many to one | **Single** |
| `fact_delivery` | `placement_id` | `fact_placement` | `placement_id` | Many to one | **Single** |
| `fact_delivery` | `date` | `dim_date` | `date` | Many to one | **Single** |
| `fact_detection_events` | `placement_id` | `fact_placement` | `placement_id` | **One to one** | **Single** |

**Every arrow single-direction.** If any line shows arrows both ways, open Properties and
set cross-filter to Single. Bidirectional filtering is the most common cause of wrong
totals and nothing here needs it.

Why `fact_delivery → fact_placement` rather than straight to the dimensions: `fact_placement`
is the parent grain and owns the dimension keys, so campaign and site filters reach daily
delivery in two hops instead of repeating two keys on 27,414 rows.

---

## 3 · Measures, in dependency order

Create on **`fact_placement`** unless marked otherwise. Paste, press Enter, then drop onto
a blank card and check the number before moving on — later measures build on earlier ones.

Full DAX: **`docs/powerbi-dax.md`**. Copy-paste sheet: **`bi/dax_measures.txt`**.

### Tier 1 — base aggregates (no dependencies)

| Measure | Expected | Population |
|---|---|---|
| `Total Spend` | **5,408,750.68** | all 595 |
| `Contracted Impressions` | **518,781,947** | all 595, **full** flight |
| `Contracted To Date` | **427,728,324** | all 595, prorated |
| `Verified Impressions` | **418,677,830** | all 595 |
| `Gross Shortfall` | **10,532,493** | 227 behind |
| `Over-delivery Offset` | **1,481,999** | 367 ahead |
| `Placements` | **595** | all |
| `Placements Behind` | **227** | behind by any amount |
| `Flagged Placements` | **82** | past the −5% line |
| `Live Issues` | **21** | flagged + in flight |
| `Completed Shortfalls` | **61** | flagged + closed |
| `Total Negative Delivery Exposure` | **134,655.35** | 227 behind |
| `Flagged Media-Value Exposure` | **117,057.70** | 82 flagged |
| `Preventable Exposure` | **36,254.56** | 21 live — **modelled** |
| `Campaigns Affected` | **8** | distinct campaigns with ≥1 flagged |
| `Markets Affected` | **6** | distinct cities with ≥1 flagged |

### Tier 2 — derived (need tier 1)

| Measure | Expected | Built from |
|---|---|---|
| `Net Shortfall` | **9,050,494** | Gross − Offset |
| `Masked Shortfall %` | **14.07%** | Offset ÷ Gross |
| `Delivery Variance %` | **−2.12%** | Verified vs Contracted To Date |
| `Blended CPM` | **12.92** | Spend ÷ Verified × 1000 |

### Tier 3 — on `fact_detection_events`

| Measure | Expected | Population |
|---|---|---|
| `Detection Events` | **102** | all detected faults |
| `Alerted Events` | **90** | detected **and** crossed the alert line |
| `Faults Recovered` | **32** | detected and recovered |
| `Median Detection Delay` | **4** | alerted (90) |
| `Median Reconciliation Delay` | **31** | alerted (90) |
| `Median Days Remaining at Detection` | **35** | alerted **and in flight** (23) |
| `Avg Detection Delay` | **4.82** | alerted (90) |

### Tier 4 — on `fact_delivery`, for the page-3 chart

```dax
Daily Verified = SUM ( fact_delivery[verified_impressions] )

Cumulative Verified =
CALCULATE (
    [Daily Verified],
    FILTER ( ALLSELECTED ( dim_date[date] ), dim_date[date] <= MAX ( dim_date[date] ) )
)

Cumulative Contracted =
VAR DaysSoFar =
    CALCULATE (
        DISTINCTCOUNT ( fact_delivery[date] ),
        FILTER ( ALLSELECTED ( dim_date[date] ), dim_date[date] <= MAX ( dim_date[date] ) )
    )
VAR PlannedPerDay = SUMX ( VALUES ( fact_placement[placement_id] ), fact_placement[planned_daily] )
RETURN DaysSoFar * PlannedPerDay
```

⚠️ `Cumulative Contracted` assumes the page is **filtered to one campaign** — every
placement in a campaign shares its flight window. Page 3 has a campaign slicer defaulting
to *Signal Everywhere*; with that selection the final points are **59,392,728 verified**
against **61,151,454 contracted**, a 1.76m gap. If the two lines look wrong, the filter is
missing.

### Tier 5 — helper tables (ribbon → **New table**)

`Bridge` (waterfall) and `Analysis Measure` (field parameter). Both in
`bi/dax_measures.txt`, ready to paste.

---

## 4 · The three traps

Three measure pairs look alike and cover different populations. If two of them return the
same number, a filter is missing.

| If you see | It means |
|---|---|
| Both exposure measures equal | `Flagged Media-Value Exposure` is missing `is_flagged = TRUE()`. They are **17,598 apart** |
| `Median Days Remaining` = 26 not 35 | Missing the `in_flight` filter. The same column gives 26 over all events, 26 over alerted, **35** over alerted-and-in-flight |
| `Gross` and `Net Shortfall` equal | `Over-delivery Offset` returned 0 — check the column imported as a number |

---

## 5 · Build the report

Ribbon → **New report**. Full spec: **`docs/powerbi-build-guide.md`**. Build in this order.

**Page 1 — `Executive`**
1. Four cards: `Delivery Variance %`, `Gross Shortfall`, `Masked Shortfall %`, `Flagged Media-Value Exposure`
2. **Campaign slicer** (`dim_campaign[campaign_name]`) — this is what makes the page worth
   building: every visual recomputes for a selection, which the web app's static version
   cannot do
3. Waterfall from `Bridge` / `Bridge Value`
4. Bar chart: campaign name × `Gross Shortfall`, sorted descending
5. Matrix: campaigns × `dim_site[city]`, values `Gross Shortfall`, **background gradient**
   conditional formatting, subtotals **off**. Leave interactions ON so clicking a cell
   cross-filters the cards and waterfall

**Page 2 — `Root cause`** — the reason this companion exists
1. Slicers: campaign, market, format, status, and `Analysis Measure[Measure]`
2. **Decomposition tree** — Analyze `Analysis Measure[Measure Fields]`; Explain by campaign
   → city → format_label → area → placement_id
3. ⚠️ Format pane → **Analysis → AI splits OFF**. They do not survive Publish to web, and a
   visual behaving differently in public than in-service is worse than one that is consistent
4. Table of ranked contributors, Top N 15 by exposure, data bars
5. Hidden page `Placement detail` with drill-through field `fact_placement[placement_id]`

**Page 3 — `Flight & detection`**
1. Three cards: detection delay, reconciliation delay, days remaining
2. Campaign slicer, default *Signal Everywhere*
3. Line chart: `dim_date[date]` × `Cumulative Verified` + `Cumulative Contracted`.
   **One y-axis** — both series are impressions
4. Table from `fact_detection_events`
5. **The required text box** (verbatim, non-negotiable):
   > The analyzer detects; it does not repair. A recovery row means delivery returned to
   > normal, not that the tool caused it. Faults are generated in a deterministic synthetic
   > dataset; the detector infers them from the daily delivery series alone and is never
   > shown the generator's fault plan.

**All three pages** also get the synthetic-data footnote from the build guide.

---

## 6 · Capture and publish

**Screenshots** — full page, into `docs/screenshots/` in this repo:
`pbi-01-executive.png`, `pbi-02-rootcause.png`, `pbi-03-detection.png`.
Target ~1600px wide; the portfolio renders them at 760px so detail survives.

**GIF** — ~8 seconds of the decomposition tree being drilled: exposure → campaign → market
→ format. Save as `pbi-decomposition.gif`. **This is the most valuable artifact**, because
it is the one capability the web app does not have.

**If step 0 said yes:** File → Embed report → Publish to web (public) → copy the **link**,
not the iframe. Paste into `docs/powerbi-plan.md`.

**If step 0 said no:** skip. Never ship a link that asks a recruiter to sign in — a dead
link is worse than no link.

---

## 7 · Hand back

When the report exists, these are written and need only your go-ahead:

- `docs/powerbi-portfolio-integration.md` — exact section, heading and copy for `ooh.html`
- `docs/resume-update-backlog.md` — the lines that become safe to claim
- `docs/powerbi-plan.md` — definition-of-done to tick

**Nothing on the portfolio claims Power BI yet**, which is accurate until the report exists.

---

## Validation summary

27 measures prepared. 10 reproduced independently in Python **and** SQL and matching to the
dollar; the rest are Python-only by design because they rest on run-based sequential logic
that DAX would make opaque.

| Measure | Expected | Population | Py | SQL |
|---|---|---|---|---|
| Total Spend | 5,408,750.68 | all 595 | ✅ | ✅ |
| Contracted To Date | 427,728,324 | all 595 | ✅ | ✅ |
| Verified Impressions | 418,677,830 | all 595 | ✅ | ✅ |
| Gross Shortfall | 10,532,493 | 227 behind | ✅ | ✅ |
| Over-delivery Offset | 1,481,999 | 367 ahead | ✅ | ✅ |
| Net Shortfall | 9,050,494 | gross − offset | ✅ | ✅ |
| Masked Shortfall % | 14.07% | offset ÷ gross | ✅ | ✅ |
| **Total Negative Delivery Exposure** | **134,655.35** | **227 behind** | ✅ | ✅ |
| **Flagged Media-Value Exposure** | **117,057.70** | **82 flagged** | ✅ | ✅ |
| Flagged Placements | 82 | past −5% | ✅ | ✅ |
| Placements Behind | 227 | behind by any amount | ✅ | ✅ |
| Live Issues / Completed Shortfalls | 21 / 61 | flagged × in-flight | ✅ | — *status derived in Python* |
| Detection Events / Alerted / Recovered | 102 / 90 / 32 | detected faults | ✅ | — *run-based* |
| Median Detection Delay | 4 | alerted (90) | ✅ | — *run-based* |
| Median Reconciliation Delay | 31 | alerted (90) | ✅ | — *run-based* |
| Median Days Remaining at Detection | 35 | alerted **and in flight** (23) | ✅ | — *run-based* |

Machine-readable: `bi/measure_expected.csv` (27 rows) and `bi/validation_expected.csv`
(12 rows, with tolerances).

---

## Depth, if needed

| Question | Document |
|---|---|
| Can the browser really do this? | `powerbi-mac-feasibility.md` |
| What does each field mean? | `bi-data-dictionary.md` |
| Why this model shape? | `powerbi-star-schema.md` |
| Full DAX with reasoning | `powerbi-dax.md` |
| Visual-by-visual spec | `powerbi-build-guide.md` |
| Every click in order | `powerbi-browser-checklist.md` |
| Where it goes on the site | `powerbi-portfolio-integration.md` |
