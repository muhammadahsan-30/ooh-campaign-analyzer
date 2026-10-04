# Power BI report — build sheet

Three pages, specified visual by visual. Pair this with
`docs/powerbi-browser-checklist.md`, which is the click-by-click order.

**Report name:** `OOH Campaign Performance — Executive & Root Cause`

**Global settings**
- Page size 16:9, canvas background `#FCFCFB`, 8px grid snap on.
- Every page gets a text box bottom-left, 9pt grey:
  *All data synthetic, generated with a fixed seed from a model of the Canadian
  out-of-home market. No real agency or client data.*
- Interactions: default cross-filtering. Do **not** add bidirectional filters.

---

# PAGE 1 — Executive campaign health

**Audience:** a recruiter or manager with no out-of-home background.
**Goal:** understand the portfolio in 20 seconds.

### Row 1 — four cards

| Card | Measure | Title | Subtitle | Format |
|---|---|---|---|---|
| 1 | `Delivery Variance %` | Delivery vs plan | How far the book is from what was owed by today | % 1dp, −2.1% |
| 2 | `Gross Shortfall` | Impressions short | Counting only placements that are behind | 10.5m |
| 3 | `Masked Shortfall %` | Hidden by over-delivery | Cancelled out on paper by sites running ahead | % 0dp, 14% |
| 4 | `Flagged Media-Value Exposure` | Media value at risk | Across the 82 placements past the −5% line | CAD, 0dp |

Conditional formatting: card 1 font red when `Delivery Variance % < 0`.
**Question answered:** is the book healthy, and what is the headline hiding?

### Row 1b — campaign slicer

- **Visual:** Slicer · **Field:** `dim_campaign[campaign_name]` · Style: dropdown
- **Why it is here:** without it, the waterfall and the matrix below merely reproduce
  visuals the web app already has. With it, every figure on the page recomputes for any
  campaign selection — which is the thing a static dashboard cannot do and the reason this
  page is worth building. Leave visual interactions ON throughout.

### Row 2 — waterfall: gross → offset → net

- **Visual:** Waterfall chart
- **Category:** a small disconnected table `Bridge` (see checklist step 9)
- **Y:** `Bridge Value` measure
- **Title:** *Why the campaign number looks healthier than the book*
- **Subtitle:** *Over-delivery on one site does not repair a dark site on another*
- Colours: increase `#D03B3B`, decrease `#898781`, total `#E39A9A`
- **Question answered:** how does 10.5m become 9.1m?

### Row 3 — campaign comparison

- **Visual:** Clustered bar chart, horizontal
- **Y:** `dim_campaign[campaign_name]` · **X:** `Gross Shortfall`
- **Secondary:** add `Flagged Placements` as a tooltip field
- Sort: `Gross Shortfall` descending
- **Title:** *Which campaigns carry the shortfall*
- **Question answered:** where is it concentrated?

### Row 4 — campaign × market matrix (the heatmap)

- **Visual:** Matrix
- **Rows:** `dim_campaign[campaign_name]` · **Columns:** `dim_site[city]`
- **Values:** `Gross Shortfall`
- **Conditional formatting →** Background colour → Format style *Gradient*, based on
  `Gross Shortfall`, lowest `#FCFCFB`, highest `#2A78D6`
- Turn **off** row/column subtotals — they invite adding a heatmap's cells, which is not
  a meaningful total here
- **Title:** *Is a market behind everywhere, or on one campaign?*
- **Expected finding:** Toronto is non-zero on 8 of 8 campaigns
- **Question answered:** systemic or isolated?

### Removed during blueprint QA

A stacked bar of `Live Issues` vs `Completed Shortfalls` was specified here and has been
**cut**. It encodes two numbers — 21 and 61 — and a chart of two numbers communicates
nothing a pair of cards does not, while spending a row of the most valuable page. The
live/completed split is a web-app workflow concept and it is already told there properly.

---

# PAGE 2 — Root cause explorer

**Audience:** analyst or hiring manager.
**Goal:** let the user find the driver themselves, in whatever order they choose.
**This page is the reason the Power BI companion exists** — the web app has fixed drill
paths and cannot offer this.

### Slicers — left rail, vertical

| Slicer | Field | Style |
|---|---|---|
| Campaign | `dim_campaign[campaign_name]` | Vertical list, multi-select |
| Market | `dim_site[city]` | Vertical list |
| Format | `dim_site[format_label]` | Vertical list |
| Status | `fact_placement[status]` | Tile |
| Measure | `Analysis Measure[Measure]` | Tile — the field parameter |

### Centre — decomposition tree

- **Visual:** Decomposition tree
- **Analyze:** `Analysis Measure[Measure Fields]` (the field parameter, so the slicer
  switches what is being decomposed)
- **Explain by**, in this order: `dim_campaign[campaign_name]`, `dim_site[city]`,
  `dim_site[format_label]`, `dim_site[area]`, `fact_placement[placement_id]`
- **Formatting → Analysis → AI splits: OFF.** They do not survive Publish to web, and a
  visual that behaves differently in public than in-service is worse than one that is
  consistent. Manual drilling is the capability being demonstrated.
- Lock the first level to `campaign_name` so the path always starts somewhere sensible
- **Title:** *Explore the exposure in any order*
- **Question answered:** which campaign → market → format → placement combination
  actually drives it?

### Right — ranked contributors

- **Visual:** Table
- **Columns:** `dim_site[city]`, `dim_site[format_label]`,
  `fact_placement[placement_id]`, `Flagged Media-Value Exposure`, `fact_placement[variance_pct]`
- Sort by exposure descending, top 15 via Filters pane (Top N)
- Conditional formatting: data bars on the exposure column
- **Title:** *Worst placements in the current selection*

### Drill-through page — `Placement detail` (hidden)

- **Drill-through field:** `fact_placement[placement_id]`
- Cards: `Verified Impressions`, `Contracted To Date`, `Delivery Variance %`,
  `Flagged Media-Value Exposure`, `Preventable Exposure`
- Line chart: `fact_delivery[verified_impressions]` by `dim_date[date]`
- Table from `fact_detection_events`: onset date, alert date, recovery date,
  detection delay, days remaining at detection
- **Title:** *Placement [placement_id]*
- ⚠️ Do not use the field parameter as the drill-through field — unsupported.

---

# PAGE 3 — Flight and detection

**Audience:** anyone asking why early detection matters.
**Goal:** fault begins → delivery deteriorates → detector flags → time still remained.

### Row 1 — three cards

| Card | Measure | Title |
|---|---|---|
| 1 | `Median Detection Delay` | Days from fault to flag |
| 2 | `Median Reconciliation Delay` | Days from fault to end of flight |
| 3 | `Median Days Remaining at Detection` | Flight left when flagged |

Subtitle under the row: *Medians across the 90 detected faults that crossed the −5% line.
Card 3 covers the 23 of those still in flight.*
**Question answered:** how much earlier is "in flight" than "at reconciliation"?

### Row 2 — cumulative delivery against plan

- **Visual:** Line chart
- **X:** `dim_date[date]`
- **Y:** `Cumulative Verified` and `Cumulative Contracted` — both defined in
  `bi/dax_measures.txt` tier 4. The blueprint originally said "a running total" without
  specifying how; that gap is now closed.
- Filter the page to one campaign via a slicer (`dim_campaign[campaign_name]`), default
  *Signal Everywhere* — it is live, 84 days, and has a detected fault that recovered
- ⚠️ `Cumulative Contracted` **requires the single-campaign filter**. Every placement in a
  campaign shares its flight window, which is what makes days × planned-per-day valid.
  Expected final points with that selection: **59,392,728** verified against
  **61,151,454** contracted, a gap of **1,758,726**.
- **Title:** *Cumulative delivery against what was contracted*
- ⚠️ One y-axis only. Both series are impressions.

### Row 3 — detection events table

- **Visual:** Table from `fact_detection_events` joined through `fact_placement`
- **Columns:** campaign name, city, format, onset date, alert date, recovery date,
  detection delay, days remaining at detection
- Sort by onset date
- Conditional formatting: `recovered` TRUE → green dot icon
- **Title:** *Every detected fault, and what happened next*

### Row 4 — text box, required

> The analyzer **detects**; it does not repair. A recovery row means delivery returned to
> normal, not that the tool caused it. Faults, onsets and recoveries are generated in a
> deterministic synthetic dataset; the detector infers them from the daily delivery series
> alone and is never shown the generator's fault plan.

**This text is not optional.** Without it the page implies causation it cannot support.

---

## Formatting conventions

| Element | Setting |
|---|---|
| Title font | Segoe UI Semibold 14pt, `#141413` |
| Subtitle | Segoe UI 10pt, `#52514E` |
| Card value | Segoe UI Bold 28pt |
| Impressions | Thousands separator, 0dp, auto-abbreviate to m |
| Currency | `CAD`, 0dp on cards, 2dp in tables |
| Percentages | 1dp for variance, 0dp for masking |
| Accent | `#2A78D6` · alert `#D03B3B` · neutral `#898781` |

Deliberately **not** used: pie and donut charts, dual-axis combo charts, gauges, 3D, custom
visuals from AppSource (they can break under Publish to web).
