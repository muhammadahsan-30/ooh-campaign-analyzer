# OOH Campaign Performance Analyzer

Finds under-delivering out-of-home advertising inventory (bulletins, transit shelters,
mall panels) **while the campaign is still running** — instead of at the end, when the
money is already spent.

**[▶ Open the live dashboard](https://muhammadahsan-30.github.io/analyzer/)** — no install, opens in the browser.

Built by [Muhammad Ahsan Sheikh](https://muhammadahsan-30.github.io), Honours Mathematics
and Business Administration (Co-op) at the University of Waterloo.

## The problem

Out-of-home advertising is billed against *estimated* impressions: a bulletin cannot
count who saw it, so the number comes from a traffic count times a visibility factor.
When a site goes dark, a poster tears, or a digital screen drops offline, real delivery
falls below that estimate. Agencies normally catch these gaps by hand during
end-of-campaign reconciliation — weeks after anything can be done about them.

I spent five months at a WPP/GroupM out-of-home agency doing that reconciliation
manually. This tool automates the detection. The synthetic dataset is built on Canadian
OOH market parameters — CMA populations, Canadian format names, rate cards from
published market benchmarks — because that is the market these figures are for.

## The result

On the bundled synthetic dataset — 120 sites, 8 national campaigns, 563 placements,
34,888 daily delivery records:

| Measure | Value |
|---|---|
| Media spend tracked | CAD 7.69m |
| Impressions delivered | 537.2m of 552.5m contracted |
| Placements more than 5% below contract | 57 (10.1%) |
| Billed spend attached to that shortfall | CAD 207,923 |
| Blended CPM | CAD 14.32 (verified delivery) |

The dashboard ranks the 57 flagged placements worst-first and filters to a single
client, city or format. CPM is computed on verified rather than contracted delivery, by
campaign, city and format, so a placement that under-delivered shows its real cost.
Campaign reach is modelled per market and summed, landing at 54.7–88.5% across the eight
campaigns.

## How to run it

Python 3.10+, two dependencies. From a fresh clone:

```bash
git clone https://github.com/muhammadahsan-30/ooh-campaign-analyzer
cd ooh-campaign-analyzer
pip install -r requirements.txt          # pandas, pytest
python src/generate_data.py              # builds data/ooh.db (fixed seed, reproducible)
python src/export_json.py                # writes public/data.json and public/data.js
python -m pytest tests/ -q               # 10 tests
cd public && python -m http.server 8000  # open http://localhost:8000
```

If SQLite cannot take file locks (network drives, some mounts), point the database
elsewhere: `OOH_DB=/tmp/ooh.db python src/generate_data.py` (`export_json.py` honours
it too).

## How it is built

```
src/generate_data.py   synthetic data -> SQLite, fixed seed
src/schema.sql         4 tables (sites, campaigns, placements, delivery), enforced foreign keys
src/metrics.py         delivery variance, CPM, rate efficiency, GRP, reach/frequency
                       one function each, all unit-tested on hand-checkable inputs
src/export_json.py     runs the metrics, writes public/data.{json,js}
src/queries.sql        standalone analytical SQL (CTEs, ROW_NUMBER / LAG window functions)
public/                static dashboard — no server, no build step
```

Metrics are computed once in Python and written to JSON; the browser only renders. One
source of truth for every number, and the figures on screen are the ones the tests
cover.

## A note on the data

**All data is synthetic**, generated from a model of the Canadian OOH market (CMA
populations, Canadian format names, rate cards from published market benchmarks) with a
fixed random seed. All figures are in CAD. No real agency or client data is used
anywhere, and the brand names are invented. Every modelling assumption — visibility
factors, the reach curve, the injected under-delivery rate, the spend basis — is
documented in [docs/assumptions.md](docs/assumptions.md).

## What I would add next

- Attribution: join sales data to exposure windows for a real return-on-ad-spend figure
- Deduplicated reach across cities for multi-market campaigns
- Extend to 10–12 CMAs. At six markets the heaviest campaigns saturate the reach curve
  in Tier 1 cities (see [docs/assumptions.md](docs/assumptions.md)); spreading the same
  spend over ~24m people rather than 18m fixes it without tuning a constant
- Share of voice by city and format against competitor bookings
