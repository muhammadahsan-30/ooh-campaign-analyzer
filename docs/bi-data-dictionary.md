# BI data dictionary

Field-level documentation for `bi/*.csv`, produced by `src/export_bi.py` from the same
SQLite database and the same `src/metrics.py` functions the web dashboard uses.

**Source classification** used throughout:

| Mark | Meaning |
|---|---|
| **G** | Generated — written directly by `generate_data.py` into `ooh.db` |
| **D** | Derived — computed by `metrics.py` from generated data |
| **S** | Structural — a key, label or calendar attribute added for the model |

### What is deliberately absent

`generate_data.py` knows which placements it broke, on which day, how badly, and whether
they were repaired. **That fault plan is evaluation-only.** It is never written to
`ooh.db`, never exported here, and never reaches the BI model.

Everything in `fact_detection_events` is *inferred from the visible daily delivery series*
by `metrics.detection_timeline()` — three consecutive days below 90% of planned delivery.
A real campaign does not come with fault labels, which is exactly why the detector is
built to work without them. Detector-vs-truth evaluation figures live in
`docs/assumptions.md` and the generator's own stdout, clearly labelled as synthetic
validation, and are not part of this model.

---

## `dim_campaign.csv`

**Grain:** one row per campaign · **Rows:** 8 · **PK:** `campaign_id`

| Field | Type | Definition | Src |
|---|---|---|---|
| `campaign_id` | int | Campaign key | G |
| `campaign_name` | text | Human-readable campaign name, e.g. *Signal Everywhere* | G |
| `client_name` | text | Advertiser. Invented brand | G |
| `industry` | text | FMCG, telecom, QSR, automotive, banking, retail | G |
| `objective` | text | awareness, product_launch, retail_drive | G |
| `campaign_start` | date | First day of the booked flight | G |
| `campaign_end` | date | Day after the last booked day | G |
| `budget` | int | Campaign budget, CAD | G |
| `flight_days` | int | `campaign_end − campaign_start` | D |
| `is_in_flight` | bool | Flight had not closed at the as-of date | D |

## `dim_site.csv`

**Grain:** one row per advertising site · **Rows:** 120 · **PK:** `site_id`

| Field | Type | Definition | Src |
|---|---|---|---|
| `site_id` | int | Site key | G |
| `city` | text | One of six Canadian CMAs | G |
| `area` | text | Neighbourhood or roadway | G |
| `format` | text | `bulletin`, `digital_screen`, `transit_shelter`, `mall_panel` | G |
| `is_digital` | bool | Digital face | G |
| `daily_traffic` | int | Estimated people/vehicles passing per day | G |
| `rate_card_monthly` | int | Published 4-week rate card, CAD | G |
| `format_label` | text | Display label, e.g. *Digital screen* | S |
| `media_type` | text | *Digital* / *Static*. **Use this to group CPM** — digital and static CPM are not comparable | S |

## `dim_date.csv`

**Grain:** one row per calendar day · **Rows:** 505 · **PK:** `date`

Continuous across the whole delivery window, including days with no delivery, so time
intelligence behaves and gaps between flights do not break an axis. **Mark as date table
in Power BI.**

| Field | Type | Definition | Src |
|---|---|---|---|
| `date` | date | `YYYY-MM-DD` | S |
| `year` | int | Calendar year | S |
| `month_num` | int | 1–12, for sort order | S |
| `month_name` | text | `Jan`–`Dec` | S |
| `year_month` | text | `YYYY-MM`, sortable | S |
| `quarter` | text | `Q1`–`Q4` | S |
| `day_of_week` | int | 1 = Monday | S |
| `day_name` | text | `Mon`–`Sun` | S |
| `is_weekend` | bool | Saturday or Sunday | S |

## `fact_placement.csv`

**Grain:** one row per placement — one site booked for one campaign over one date window
**Rows:** 595 · **PK:** `placement_id` · **FK:** `campaign_id`, `site_id`

This is a *fact with attributes*: it carries additive measures at placement grain. Every
"to date" figure is measured to the as-of date, **2026-09-10**.

| Field | Type | Definition | Src |
|---|---|---|---|
| `placement_id` | int | Placement key | G |
| `campaign_id` | int | → `dim_campaign` | G |
| `site_id` | int | → `dim_site` | G |
| `start_date` / `end_date` | date | Booked flight window | G |
| `flight_days` | int | Booked length in days | D |
| `elapsed_days` | int | Days run by the as-of date, capped at `flight_days` | D |
| `remaining_days` | int | `flight_days − elapsed_days` | D |
| `in_flight` | bool | Still running at the as-of date | D |
| `contracted_impressions` | float | Impressions owed over the **whole** flight | G |
| `contracted_to_date` | float | **Owed so far**: `contracted × elapsed ÷ flight_days` | D |
| `verified_to_date` | float | Impressions actually delivered so far | G |
| `shortfall` | float | `max(0, contracted_to_date − verified_to_date)`. **Zero when ahead** — this is the gross side of the netting | D |
| `over_delivery` | float | `max(0, verified_to_date − contracted_to_date)`. The offset side | D |
| `negotiated_rate` | int | Agreed 4-week rate, CAD | G |
| `spend_to_date` | float | `negotiated_rate × elapsed_days ÷ 28` | D |
| `contracted_cpm` | float | `spend_to_date ÷ contracted_to_date × 1000` — the rate agreed per thousand | D |
| `billed_shortfall` | float | `shortfall × contracted_cpm ÷ 1000`. Money already spent on undelivered impressions | D |
| `preventable_exposure` | float | **Modelled.** Value that would accrue over the remaining flight at the current rate. Zero for closed flights. **Never add to `billed_shortfall`** | D |
| `variance_pct` | float | `(verified − contracted_to_date) ÷ contracted_to_date × 100` | D |
| `delivery_index` | float | Cumulative `verified ÷ contracted_to_date` | D |
| `current_index` | float | The rate it is running at **now** — the fault-period rate if mid-fault, else cumulative | D |
| `planned_daily` | float | `contracted_impressions ÷ flight_days` | D |
| `required_daily` | float | What it would need daily to finish whole. Null when closed | D |
| `recovery_pace` | float | `required_daily ÷ planned_daily`. 1.68 = would need 168% of plan | D |
| `status` | text | `on_track`, `live_issue`, `completed_shortfall` | D |
| `is_flagged` | bool | Breaches the −5% line. `live_issue` + `completed_shortfall` | D |
| `is_material` | bool | Live issue holding ≥ CAD 1,000 of preventable exposure | D |
| `downtime_hours` | float | Logged digital downtime across the flight | G |

## `fact_delivery.csv`

**Grain:** one row per placement per day · **Rows:** 27,414
**PK:** composite (`placement_id`, `date`) · **FK:** `placement_id`, `date`

Deliberately narrow. Campaign and site attributes are **not** repeated here — they reach
this table through `fact_placement`.

| Field | Type | Definition | Src |
|---|---|---|---|
| `placement_id` | int | → `fact_placement` | G |
| `date` | date | → `dim_date` | G |
| `verified_impressions` | int | Delivered that day | G |
| `estimated_impressions` | int | Expected that day before delivery health | G |
| `downtime_hours` | float | Digital outage hours that day | G |

## `fact_detection_events.csv`

**Grain:** one row per placement **where a fault was detected** · **Rows:** 102
**PK:** `placement_id` · **FK:** `placement_id`

Placements with no detected fault are **absent**, which keeps the grain honest: this is a
table of events, not of placements. All day numbers are 0-based offsets into the flight.

| Field | Type | Definition | Src |
|---|---|---|---|
| `placement_id` | int | → `fact_placement` | G |
| `onset_day` / `onset_date` | int / date | First day of the first run of 3 consecutive days below 90% of planned delivery | D |
| `alert_day` / `alert_date` | int / date | First day cumulative delivery crossed the −5% line, after a 14-day minimum window | D |
| `recovery_day` / `recovery_date` | int / date | First run of 3 days back at or above 95%. Blank if never | D |
| `recovered` | bool | Delivery returned to normal in flight | D |
| `detection_delay_days` | int | `alert_day − onset_day`. **Never negative** — the 14-day window guarantees it | D |
| `reconciliation_delay_days` | int | `flight_days − onset_day`. When end-of-campaign review would have found it | D |
| `days_remaining_at_detection` | int | Flight left to act in when flagged | D |
| `pre_fault_index` | float | Mean daily delivery index before onset | D |
| `fault_index` | float | Mean daily delivery index during the fault | D |

## `validation_expected.csv`

**Grain:** one row per validated metric · **Rows:** 12

Produced by `src/validate_bi.py`. See `docs/powerbi-dax.md` §Validation.

| Field | Definition |
|---|---|
| `metric` | Measure name, matching the DAX measure |
| `python_value` | From `metrics.py` — authoritative |
| `sql_value` | Independent SQL reimplementation. Blank where the concept is Python-only |
| `expected_powerbi_value` | What the DAX measure must return |
| `population_definition` | **Which placements the metric covers.** The field that prevents the two exposure measures being confused |
| `tolerance` | Allowed absolute difference |
| `status` | `MATCH`, `DIVERGENT`, or `PYTHON ONLY` |

---

## Reproducing

```bash
python src/generate_data.py   # rebuild ooh.db from seed 42
python src/export_json.py     # web dashboard payload
python src/export_bi.py       # the six BI tables
python src/validate_bi.py     # validation_expected.csv
```

Deterministic: the same seed produces byte-identical CSVs.
