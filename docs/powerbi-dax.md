# DAX measures

Every measure to be created in Power BI Service web modeling, with its exact expected
value on the current dataset. Paste, then check the number.

**Create all measures on `fact_placement`** unless stated otherwise, so the Fields pane
has one obvious home for them. Create a display folder per group.

---

## The naming rule this file exists to enforce

Three pairs of measures below look similar and cover **different populations**. They must
never share a label, and a visual must never mix them without saying so.

| Measure | Population | Value |
|---|---|---|
| **Total Negative Delivery Exposure** | every placement behind by any amount (227) | 134,655.35 |
| **Flagged Media-Value Exposure** | only those past the −5% line (82) | 117,057.70 |

| Measure | Population | Value |
|---|---|---|
| **Gross Shortfall** | shortfalls only, no credit for over-delivery | 10,532,493 |
| **Net Shortfall** | gross minus over-delivery offset | 9,050,494 |

| Measure | Population | Value |
|---|---|---|
| **Median Reconciliation Delay** | detection events that **alerted** (90) | 31 days |
| **Median Days Remaining at Detection** | alerted events **still in flight** (23) | 35 days |

That last pair is the sharpest trap in the model: the same column, `days_remaining_at_detection`,
yields **26** over all 102 detection events, **26** over the 90 that alerted, and **35**
over the 23 that alerted while still in flight. The published figure is 35. Filter
explicitly, every time.

---

## 1 · Volume and money

```dax
Total Spend = SUM ( fact_placement[spend_to_date] )
```
Media spend billed to the as-of date. **Expected: 5,408,750.68**

```dax
Contracted Impressions = SUM ( fact_placement[contracted_impressions] )
```
Impressions owed across the **whole** booked flight. **Expected: 518,781,947**

```dax
Contracted To Date = SUM ( fact_placement[contracted_to_date] )
```
Impressions owed **so far** — the full booking prorated to elapsed days. This, not
`Contracted Impressions`, is the denominator for anything "to date".
**Expected: 427,728,324**

```dax
Verified Impressions = SUM ( fact_placement[verified_to_date] )
```
Delivered so far. **Expected: 418,677,830**

```dax
Blended CPM = DIVIDE ( [Total Spend], [Verified Impressions] ) * 1000
```
Cost per thousand on verified delivery. **Expected: 12.92**
⚠️ Never show this across `media_type` — digital and static CPM are not comparable.

---

## 2 · The gross / net story

```dax
Delivery Variance % =
DIVIDE ( [Verified Impressions] - [Contracted To Date], [Contracted To Date] )
```
Format as percentage, 1 decimal. **Expected: −2.1%**

```dax
Gross Shortfall = SUM ( fact_placement[shortfall] )
```
Impressions missed, counting **only** placements that are behind. The column is already
floored at zero, so no conditional is needed — which also means a reader can verify the
measure without reading DAX. **Expected: 10,532,493**

```dax
Over-delivery Offset = SUM ( fact_placement[over_delivery] )
```
Impressions delivered **above** contract elsewhere. **Expected: 1,481,999**

```dax
Net Shortfall = [Gross Shortfall] - [Over-delivery Offset]
```
What campaign-level reporting shows. **Expected: 9,050,494**

```dax
Masked Shortfall % = DIVIDE ( [Over-delivery Offset], [Gross Shortfall] )
```
Share of the real gap cancelled out on paper. Format as percentage, 0 decimals.
**Expected: 14.1%**

---

## 3 · Counts

```dax
Placements = COUNTROWS ( fact_placement )
```
**Expected: 595**

```dax
Placements Behind =
CALCULATE ( COUNTROWS ( fact_placement ), fact_placement[shortfall] > 0 )
```
Behind by **any** amount. **Expected: 227**

```dax
Flagged Placements =
CALCULATE ( COUNTROWS ( fact_placement ), fact_placement[is_flagged] = TRUE() )
```
Past the −5% line. **Expected: 82**

```dax
Live Issues =
CALCULATE ( COUNTROWS ( fact_placement ), fact_placement[status] = "live_issue" )
```
**Expected: 21**

```dax
Completed Shortfalls =
CALCULATE ( COUNTROWS ( fact_placement ), fact_placement[status] = "completed_shortfall" )
```
**Expected: 61**

```dax
Campaigns Affected =
CALCULATE ( DISTINCTCOUNT ( fact_placement[campaign_id] ), fact_placement[is_flagged] = TRUE() )
```
**Expected: 8** — every campaign has at least one flagged placement.

```dax
Markets Affected =
CALCULATE ( DISTINCTCOUNT ( dim_site[city] ), fact_placement[is_flagged] = TRUE() )
```
**Expected: 6**

---

## 4 · Exposure — read §"naming rule" first

```dax
Total Negative Delivery Exposure = SUM ( fact_placement[billed_shortfall] )
```
Every placement behind by any amount, priced at its contracted CPM.
**Population: 227 placements. Expected: 134,655.35**

```dax
Flagged Media-Value Exposure =
CALCULATE ( SUM ( fact_placement[billed_shortfall] ), fact_placement[is_flagged] = TRUE() )
```
Only the 82 past the attention line. **This is the number the Attention Centre acts on.**
**Population: 82 placements. Expected: 117,057.70**

```dax
Preventable Exposure =
CALCULATE ( SUM ( fact_placement[preventable_exposure] ), fact_placement[status] = "live_issue" )
```
**Modelled.** What would further accrue over the remaining flight at the current rate.
**Never add this to either exposure measure above** — one is spent, this has not happened.
Title any visual using it "modelled". **Expected: 36,254.56**

---

## 5 · Detection — create on `fact_detection_events`

The base table holds 102 detected faults, of which **90 crossed the alert line**. Rows
that never alerted have blank `detection_delay_days`.

```dax
Detection Events = COUNTROWS ( fact_detection_events )
```
**Expected: 102**

```dax
Alerted Events =
CALCULATE (
    COUNTROWS ( fact_detection_events ),
    NOT ISBLANK ( fact_detection_events[detection_delay_days] )
)
```
**Expected: 90**

```dax
Faults Recovered =
CALCULATE ( COUNTROWS ( fact_detection_events ), fact_detection_events[recovered] = TRUE() )
```
**Expected: 32**

```dax
Median Detection Delay =
MEDIANX (
    FILTER ( fact_detection_events, NOT ISBLANK ( fact_detection_events[detection_delay_days] ) ),
    fact_detection_events[detection_delay_days]
)
```
Days from a fault starting to the analyzer flagging it. **Population: alerted events (90).
Expected: 4**

```dax
Median Reconciliation Delay =
MEDIANX (
    FILTER ( fact_detection_events, NOT ISBLANK ( fact_detection_events[detection_delay_days] ) ),
    fact_detection_events[reconciliation_delay_days]
)
```
Days from a fault starting to the flight closing — when an end-of-campaign review would
have found it. **Population: alerted events (90). Expected: 31**

The pair *4 against 31* is the project's headline. Put both on the same card row.

```dax
Median Days Remaining at Detection =
MEDIANX (
    FILTER (
        fact_detection_events,
        NOT ISBLANK ( fact_detection_events[detection_delay_days] )
            && RELATED ( fact_placement[in_flight] ) = TRUE()
    ),
    fact_detection_events[days_remaining_at_detection]
)
```
⚠️ **Both filters are required.** Alerted-only gives 26; alerted **and still in flight**
gives 35, which is the published figure. **Population: 23 events. Expected: 35**

```dax
Avg Detection Delay =
AVERAGEX (
    FILTER ( fact_detection_events, NOT ISBLANK ( fact_detection_events[detection_delay_days] ) ),
    fact_detection_events[detection_delay_days]
)
```
**Expected: 4.82.** Prefer the median on cards — the mean is pulled by a long tail.

---

## 6 · Field parameter for the Root Cause Explorer

There is no *New parameter* button in web modeling, but a field parameter is just a
calculated table. Create via **New table** on the model (not on `fact_placement`):

```dax
Analysis Measure =
{
    ( "Flagged media-value exposure", NAMEOF ( [Flagged Media-Value Exposure] ), 0 ),
    ( "Gross shortfall",              NAMEOF ( [Gross Shortfall] ),              1 ),
    ( "Placements behind",            NAMEOF ( [Placements Behind] ),            2 ),
    ( "Verified impressions",         NAMEOF ( [Verified Impressions] ),         3 )
}
```

Then rename the generated columns: `Value1` → `Measure`, `Value2` → `Measure Fields`,
`Value3` → `Measure Order`; sort `Measure` by `Measure Order`; mark `Measure Fields` as a
field-parameter column in Properties. Drop `Measure` on a slicer and `Measure Fields` into
a visual's value well.

⚠️ Field parameters cannot be the linked field of a drill-through or tooltip page. Use the
underlying measure there instead.

---

## Validation

`bi/validation_expected.csv` holds the authoritative expected value, the independent SQL
value, the population definition and a tolerance for each metric. Current state: **10 of
12 metrics reproduced independently in Python and SQL and matching; 2 are Python-only**
(`Live Issues`, `Completed Shortfalls`) because `status` is derived from the in-flight
test rather than from a single SQL predicate.

After building the measures, compare each card against that file. A mismatch is almost
always a **population** error — a missing `is_flagged` filter, or the wrong one of the
three detection populations — not an arithmetic one.
