# Power BI Service — click-by-click checklist (macOS, browser only)

Written assuming no prior Power BI experience. Nothing here needs Power BI Desktop.
Every expected number is given so a wrong result is caught immediately.

**Before you start:** the six CSVs are in `bi/` in the analyzer repo. Regenerate with
`python src/export_bi.py` if needed.

---

## Part A — account and workspace

**STEP 1.** Go to **app.powerbi.com** and sign in with your `@uwaterloo.ca` account.
A free licence is enough. (Power BI will not accept a personal Gmail address.)

**STEP 2.** Left rail → **Workspaces** → **+ New workspace**. Name it
`OOH Analyzer`. Leave everything else default. *(If workspace creation is blocked by your
tenant, use **My workspace** instead — everything below still works.)*

**STEP 3 — do this now, it determines the ending.** Check whether public sharing is
available to you: open any existing report → **File** menu → look for
**Embed report → Publish to web (public)**.

- **Present and clickable** → you will be able to publish a public link at the end.
- **Greyed out or absent** → your tenant has it disabled. Not a problem: you will ship
  screenshots and a GIF instead. See `powerbi-mac-feasibility.md` § *If Publish to web is
  unavailable*. **Do not switch to Tableau over this.**

---

## Part B — load the data

**STEP 4.** Left rail → **Create** → **Get data** → **Text/CSV**.

**STEP 5.** Upload in **this order** (dimensions first, so relationship detection has keys
to match):

1. `bi/dim_date.csv`
2. `bi/dim_campaign.csv`
3. `bi/dim_site.csv`
4. `bi/fact_placement.csv`
5. `bi/fact_delivery.csv`
6. `bi/fact_detection_events.csv`

For each: after upload, Power Query previews it → check the header row was detected →
**Create**. On the final one choose **Create a semantic model only** (not "Create a
report" — the model comes first).

**STEP 6.** Name the semantic model `OOH Campaign Model`.

**STEP 7 — verify row counts.** In the model view, click each table and check:

| Table | Rows |
|---|---|
| `dim_campaign` | 8 |
| `dim_site` | 120 |
| `dim_date` | 505 |
| `fact_placement` | 595 |
| `fact_delivery` | 27,414 |
| `fact_detection_events` | 102 |

A wrong count means the CSV did not fully upload. Re-upload that one.

**STEP 8 — check data types.** Click each date column (`date`, `start_date`, `end_date`,
`onset_date`, `alert_date`, `recovery_date`, `campaign_start`, `campaign_end`) and confirm
**Date** in the Properties pane, not Text. Fix any that imported as text.
Confirm `is_flagged`, `is_material`, `in_flight`, `recovered`, `is_weekend`,
`is_in_flight`, `is_digital` are **True/False**.

---

## Part C — the model

**STEP 9.** Toggle **Viewing** → **Editing** (top right).

**STEP 10 — mark the date table.** Right-click `dim_date` in the Data pane →
**Mark as date table** → column `date` → OK.

**STEP 11 — create relationships.** Ribbon → **Manage relationships** → **New**, five
times. All are **Many-to-one**, **Single** cross-filter direction, **Active**:

| From table | From column | To table | To column | Cardinality |
|---|---|---|---|---|
| `fact_placement` | `campaign_id` | `dim_campaign` | `campaign_id` | Many to one |
| `fact_placement` | `site_id` | `dim_site` | `site_id` | Many to one |
| `fact_delivery` | `placement_id` | `fact_placement` | `placement_id` | Many to one |
| `fact_delivery` | `date` | `dim_date` | `date` | Many to one |
| `fact_detection_events` | `placement_id` | `fact_placement` | `placement_id` | **One to one** |

**Delete any relationship Power BI auto-created that is not in this table.** Auto-detection
often guesses a second date relationship — remove it.

**STEP 12 — check for bidirectional arrows.** In the diagram, every relationship line
should show a single arrow. If any shows arrows both ways, open its Properties and set
cross-filter direction to **Single**.

---

## Part D — measures

**STEP 13.** Select `fact_placement` → ribbon **New measure** → paste → Enter. Repeat for
every measure in `docs/powerbi-dax.md` §1–§4. Create the §5 detection measures on
`fact_detection_events`.

**STEP 14 — verify as you go.** Drop each new measure onto a blank card visual and check
against this table. **Stop and fix immediately on any mismatch** — later measures build on
earlier ones.

| Measure | Expected |
|---|---|
| Total Spend | 5,408,750.68 |
| Contracted To Date | 427,728,324 |
| Verified Impressions | 418,677,830 |
| Delivery Variance % | −2.1% |
| Gross Shortfall | 10,532,493 |
| Over-delivery Offset | 1,481,999 |
| Net Shortfall | 9,050,494 |
| Masked Shortfall % | 14.1% |
| Placements | 595 |
| Placements Behind | 227 |
| Flagged Placements | 82 |
| Live Issues | 21 |
| Completed Shortfalls | 61 |
| **Total Negative Delivery Exposure** | **134,655.35** |
| **Flagged Media-Value Exposure** | **117,057.70** |
| Preventable Exposure | 36,254.56 |
| Detection Events | 102 |
| Alerted Events | 90 |
| Faults Recovered | 32 |
| Median Detection Delay | 4 |
| Median Reconciliation Delay | 31 |
| Median Days Remaining at Detection | 35 |

**If the two exposure measures return the same number, one is missing its filter.** They
are 17,598 apart and cover different populations — that is the whole point.

**If Median Days Remaining returns 26 instead of 35**, the `in_flight` filter is missing.

**STEP 15 — the bridge table for the waterfall.** Ribbon → **New table**:

```dax
Bridge =
DATATABLE (
    "Step", STRING, "Order", INTEGER,
    { { "Gross shortfall", 1 }, { "Offset by over-delivery", 2 }, { "Net shortfall", 3 } }
)
```

Then a measure on `Bridge`:

```dax
Bridge Value =
SWITCH (
    SELECTEDVALUE ( Bridge[Order] ),
    1, [Gross Shortfall],
    2, -[Over-delivery Offset],
    3, [Net Shortfall]
)
```

Sort `Step` by `Order` (select the column → **Sort by column** → `Order`).

**STEP 16 — the field parameter.** Ribbon → **New table**, paste the `Analysis Measure`
definition from `powerbi-dax.md` §6, then rename `Value1`→`Measure`,
`Value2`→`Measure Fields`, `Value3`→`Measure Order`, and sort `Measure` by `Measure Order`.

---

## Part E — the report

**STEP 17.** Ribbon → **New report**. Build the three pages exactly as specified in
`docs/powerbi-build-guide.md`. Rename pages: `Executive`, `Root cause`, `Flight & detection`,
plus a hidden `Placement detail`.

**STEP 18 — the one setting people forget.** On Page 2, select the decomposition tree →
Format pane → **Analysis** → turn **AI splits OFF**.

**STEP 19 — drill-through.** On the hidden `Placement detail` page, Visualizations pane →
**Drill through** → add `fact_placement[placement_id]`. Hide the page (right-click the tab
→ Hide).

**STEP 20 — the synthetic-data note.** Add the text box from the build guide to all three
visible pages. Non-negotiable.

**STEP 21.** **Save**, naming the report
`OOH Campaign Performance — Executive & Root Cause`.

---

## Part F — publish and capture

**STEP 22 — screenshots.** Full-page capture of each of the three pages, light background.
Save into the analyzer repo as:
`docs/screenshots/pbi-01-executive.png`, `pbi-02-rootcause.png`, `pbi-03-detection.png`.

**STEP 23 — the GIF.** Record ~8 seconds of the decomposition tree being drilled:
exposure → campaign → market → format. This is the single most valuable artifact, because
it shows the one capability the web app does not have. Save as
`docs/screenshots/pbi-decomposition.gif`.

**STEP 24 — public link, if STEP 3 said yes.** **File → Embed report → Publish to web
(public)** → create embed code → copy the **link** (not the iframe). Paste it into
`docs/powerbi-plan.md` under a new *Published* heading.

**STEP 25 — if STEP 3 said no.** Skip. The screenshots and GIF are the artifact. Do not
publish a link that needs a login — a dead link is worse than none.

---

## Part G — hand back

When the report exists, the following are ready to action and need only your go-ahead:

1. `docs/powerbi-portfolio-integration.md` — exact copy and placement for the new section
   in `ooh.html`
2. `docs/resume-update-backlog.md` — the lines that become safe to claim
3. `docs/powerbi-plan.md` — definition-of-done checklist to tick off

**Do not update the portfolio or README before the report exists.** Everything currently
says the companion is *prepared*, not *built*, and that is accurate.

---

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| A measure returns blank | Measure created on the wrong table | Delete, recreate on the table named in `powerbi-dax.md` |
| Both exposure measures equal | Missing `is_flagged` filter | Recheck §4 |
| Median days remaining = 26 | Missing `in_flight` filter | Recheck §5 |
| Totals double | A duplicate or bidirectional relationship | STEP 11–12 |
| Decomposition tree greyed out | No measure in **Analyze** | Needs a measure or aggregate, not a column |
| Line chart has date gaps | `dim_date` not marked as date table | STEP 10 |
| Numbers right, matrix blank | `fact_delivery` has no direct campaign key — by design | Filter through `fact_placement`, not directly |
