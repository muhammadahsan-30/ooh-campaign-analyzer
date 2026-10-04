# Power BI semantic model — star schema

Six tables: three dimensions, three facts. Small on purpose. The model should be
explainable in an interview in under a minute, not demonstrate how many tables can be
related.

---

## Diagram

```
        ┌──────────────────┐                      ┌────────────────────┐
        │   dim_date       │                      │   dim_campaign     │
        │   505 rows       │                      │   8 rows           │
        │   PK: date       │                      │   PK: campaign_id  │
        │   ★ date table   │                      │                    │
        └────────┬─────────┘                      └─────────┬──────────┘
                 │ 1                                      1 │
                 │                                          │
                 │ ∗                                      ∗ │
        ┌────────┴──────────────┐   ∗          1  ┌─────────┴──────────┐        ┌──────────────────┐
        │   fact_delivery       ├─────────────────┤  fact_placement    ├────────┤   dim_site       │
        │   27,414 rows         │                 │  595 rows          │ ∗    1 │   120 rows       │
        │   placement × day     │                 │  PK: placement_id  │        │   PK: site_id    │
        └───────────────────────┘                 └─────────┬──────────┘        └──────────────────┘
                                                          1 │
                                                            │ 1
                                                  ┌─────────┴──────────────┐
                                                  │ fact_detection_events  │
                                                  │ 102 rows               │
                                                  │ one per detected fault │
                                                  └────────────────────────┘

        ∗ = many          1 = one          all filters flow left-to-right / top-down
```

## Relationships

| From | To | Cardinality | Cross-filter | Active |
|---|---|---|---|---|
| `fact_placement[campaign_id]` | `dim_campaign[campaign_id]` | Many-to-one | Single | Yes |
| `fact_placement[site_id]` | `dim_site[site_id]` | Many-to-one | Single | Yes |
| `fact_delivery[placement_id]` | `fact_placement[placement_id]` | Many-to-one | Single | Yes |
| `fact_delivery[date]` | `dim_date[date]` | Many-to-one | Single | Yes |
| `fact_detection_events[placement_id]` | `fact_placement[placement_id]` | **One-to-one** | Single | Yes |

**Every relationship is single-direction.** No bidirectional filtering anywhere — it is
not needed here and it is the most common source of ambiguous models.

### Why these directions

- **Dimensions filter facts, never the reverse.** Selecting *Toronto* in a `dim_site`
  slicer filters `fact_placement`, and from there `fact_delivery` and
  `fact_detection_events`. The chain works because each hop is many-to-one in the same
  direction.
- **`fact_delivery → fact_placement` is a fact-to-fact relationship**, which is
  unusual-looking but correct: `fact_placement` is the parent grain and carries the
  dimension keys, so routing through it avoids repeating `campaign_id` and `site_id` on
  27,414 delivery rows. Campaign and site filters reach daily delivery in two hops.
- **`fact_detection_events` is one-to-one** with `fact_placement` because a placement has
  at most one detected fault episode in this dataset. Only 102 of 595 placements appear —
  absence means no fault was detected, which is information, not a gap.

### Grain, stated plainly

| Table | One row is… |
|---|---|
| `fact_placement` | one site booked for one campaign over one date window |
| `fact_delivery` | one placement on one day |
| `fact_detection_events` | one detected fault episode on one placement |
| `dim_campaign` | one campaign |
| `dim_site` | one physical advertising site |
| `dim_date` | one calendar day |

### Attribute ownership

Each attribute lives in exactly one place. Nothing is duplicated.

| Attribute | Owner | Note |
|---|---|---|
| Campaign name, client, industry, objective, budget | `dim_campaign` | Not repeated on `fact_placement` |
| City, area, format, media type, rate card, traffic | `dim_site` | Market and format come from the **site**, not the placement — a placement inherits them |
| Flight dates, elapsed/remaining days, contracted and verified impressions, spend, status | `fact_placement` | Placement-grain measures |
| Daily delivery, estimates, downtime | `fact_delivery` | |
| Calendar attributes | `dim_date` | |
| Fault onset, alert, recovery, delays | `fact_detection_events` | Derived in Python from the delivery series, never from generator labels |

**`media_type` on `dim_site`** (*Digital* / *Static*) exists because digital and static CPM
are not comparable — the model does not represent digital share-of-loop. Any CPM visual
must be split or filtered by it. This is the one modelling decision carrying a
methodological warning, and it is documented in `docs/assumptions.md`.

## Date table

Mark `dim_date` as the date table on the `date` column (*right-click the table → Mark as
date table*). It is continuous across the whole delivery window including days with no
delivery, so a line chart by date has no gaps and time intelligence behaves.

`dim_date` relates only to `fact_delivery`. It deliberately does **not** relate to
`fact_placement` — a placement spans a *range* of dates, not one date, and relating it to
any single date (start? end?) would be a model that lies. Placement-level time questions
are answered by the stored day counts instead.

## What was rejected, and why

| Considered | Rejected because |
|---|---|
| A `dim_placement` dimension separate from the fact | `fact_placement` is already one row per placement. Splitting its keys from its measures would add a table and remove nothing |
| Snowflaking `dim_site` into city / format lookups | Six cities and four formats. A lookup table for six rows is complexity with no payoff |
| Repeating `campaign_id` / `site_id` on `fact_delivery` | 27,414 rows × 2 redundant keys, and two ways to reach the same filter. The two-hop chain is correct and cheaper |
| A single wide flat table | Would remove the entire point of the exercise, and would make digital/static CPM trivially mis-aggregated |
| Bidirectional cross-filtering | Not required by any visual in the build guide; invites ambiguity |

## Load order

Load dimensions before facts so relationship auto-detection has keys to match:
`dim_date`, `dim_campaign`, `dim_site`, then `fact_placement`, `fact_delivery`,
`fact_detection_events`. Verify every auto-detected relationship against the table above —
auto-detection can guess wrong on `date`.
