# Resume update backlog

**`resume.pdf` is not edited by this backlog.** It dates from 11 September 2026 and
predates the detection work, the gross/net decomposition, the flight timeline and the test
count reaching 44. This file lists what *could* change, with every number verified against
the current build on 4 October 2026.

Classification: **SAFE NOW** · **SAFE AFTER POWER BI EXISTS** · **DO NOT CLAIM**

---

## The framing rule

The project runs on a **deterministic synthetic dataset**. Every figure below is real
output from real code, but it describes a modelled environment, not a client engagement.
Any resume line must make that legible without a footnote — because an interviewer *will*
ask, and the answer should already be in the sentence.

The reliable construction is: **what was built → what it was evaluated against → the
result**, with "synthetic" inside the clause rather than appended to it.

### The phrasing to avoid

> ~~"Achieved 98.1% fault detection accuracy"~~

It reads as a production ML result. It is a reconstruction rate against known injected
events in data the same project generated. Preferred:

> *"Evaluated detection logic against hidden synthetic fault events, recovering 102 of the
> 104 that occurred from the delivery series alone."*

Longer, and it survives the follow-up question.

---

## SAFE NOW

| # | Line | Verified |
|---|---|---|
| 1 | Built an out-of-home campaign analyzer in Python, SQL and SQLite that measures 595 placements against the impressions contracted to date, across a synthetic 8-campaign, 120-site book and 27,414 daily delivery records | ✅ |
| 2 | Designed a gross-versus-net shortfall decomposition showing that campaign-level reporting hid 10.5m impressions of under-delivery across 227 placements, 14% of it offset on paper by over-delivering sites | ✅ |
| 3 | Evaluated detection logic against hidden synthetic fault events, recovering 102 of the 104 that occurred from the daily delivery series alone, with a median error of 0 days in the inferred start date | ✅ |
| 4 | Reduced median time-to-detection to 4 days against the 31 days an end-of-campaign reconciliation would have taken, in a modelled campaign environment | ✅ |
| 5 | Wrote 44 unit tests on hand-verifiable inputs and cross-validated 10 business metrics independently in Python and SQL, agreeing to the dollar | ✅ |
| 6 | Separated two exposure measures over different populations — total negative delivery exposure (227 placements, CAD 134.7k) and flagged media-value exposure (82, CAD 117.1k) — after a cross-system check surfaced a CAD 17.6k definitional divergence | ✅ |
| 7 | Built and deployed a seven-view static analytical interface with no framework or charting library, including hand-built SVG visualisations, light/dark themes and a colour-vision-validated status palette | ✅ |
| 8 | Prepared a BI-ready star schema (3 dimensions, 3 facts) exported from the same pipeline, with a documented data dictionary and DAX specification | ✅ |

**Note on #4.** "In a modelled campaign environment" is doing necessary work. Without it
the line implies a measured operational improvement.

**Note on #6.** This is the strongest line for an analytics or BI role. It is about
*noticing* a semantic problem, which is rarer than building something.

---

## SAFE AFTER POWER BI EXISTS

Do not add any of these until the report is built and verified in Power BI Service.

| # | Line | Blocked on |
|---|---|---|
| 9 | Modelled the same dataset as a Power BI star schema with DAX measures, validating Python, SQL and DAX against one another | report built |
| 10 | Built a three-page Power BI report — executive health, root-cause decomposition, and detection timing — on a semantic model authored entirely in Power BI Service | report built |
| 11 | Add `Power BI` and `DAX` to the skills line | report built |
| 12 | Add a link to the published report | report built **and** publish-to-web permitted by the tenant |

---

## DO NOT CLAIM

| Claim | Why not |
|---|---|
| "98.1% accuracy" unqualified | Reconstruction rate against self-generated events. See the framing rule |
| Any figure as a client or employer result | All synthetic. CAD 5.4m of tracked spend is modelled; the **real** media figure is the CAD 1m+ reconciled at Kinetic |
| "Reduced reconciliation time by 27 days" | No operational baseline was measured; the comparison is between two measurements inside the model |
| "Machine learning" / "anomaly detection model" | It is a stated rule: three consecutive days below 90% of plan. Calling it ML would be false and would collapse under one question |
| "Forecasting" or "predictive" | Preventable exposure extends the current rate; it is explicitly not a forecast |
| "Real-time" | Batch, against a fixed as-of date |
| Power BI, DAX, or star-schema **implementation** | Prepared, not built. Currently a specification |
| Chart.js | Removed. The dashboard uses hand-built SVG |
| "19 tests" or any earlier count | Now 44 |

---

## Also worth correcting when the resume is next touched

- The analyzer description predates gross/net, detection, the Attention Centre and the
  case study — it likely still describes the prorated-variance tool alone.
- Kinetic's bullet could carry the **→ analyzer** link explicitly; the origin story is the
  strongest thing in the project and a resume reader will not infer it.
- BarakahLink is **food-surplus redistribution in Kitchener–Waterloo**, not a generic
  donation platform. The portfolio was corrected on 4 Oct 2026; the resume may not be.
