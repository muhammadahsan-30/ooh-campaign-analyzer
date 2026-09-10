"""
Synthetic data generator for the OOH Campaign Performance Analyzer.

All data here is INVENTED. It is modelled on how out-of-home advertising is
actually structured (sites, placements, daily delivery) in the CANADIAN market:
CMA populations, Canadian format names, and rate cards built from published
Canadian market benchmarks (per four-week period, CAD). No real agency or client
data is used anywhere in this project.

The impression model is documented in docs/assumptions.md.
"""
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as m           # single source of truth for CMA populations

SEED = 42                      # fixed so the dataset is reproducible
random.seed(SEED)

# The "today" the dataset is generated as of. Fixed rather than date.today() so
# the database stays reproducible. Campaigns that are still in the air on this
# date only have delivery reported up to it, which is what a live book looks
# like and what the prorated variance in metrics.delivery_vs_contract measures
# against.
AS_OF = date(2026, 9, 10)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# OOH_DB lets you point the database somewhere else (useful on network drives,
# where SQLite cannot take the file locks it needs).
DB   = os.environ.get("OOH_DB", os.path.join(ROOT, "data", "ooh.db"))

# --- market structure (Canada) --------------------------------------------
# Inventory is allocated strictly in proportion to CMA population (see
# allocate_cities), so no market is over- or under-weighted by a random draw.
#
# Market tiers. A Calgary bulletin carries less traffic AND commands a lower rate
# than a downtown Toronto one, so cost per thousand stays broadly comparable
# across markets while impression volume falls with market size.
TIER1 = {"Toronto", "Montreal", "Vancouver"}   # traffic x1.0, upper half of rate band
TIER2 = {"Calgary", "Ottawa", "Edmonton"}      # traffic x0.6, lower half of rate band
TIER2_TRAFFIC = 0.60

AREAS = {
    "Toronto":   ["Yonge & Dundas", "Gardiner Expressway", "King West", "Yorkville", "Scarborough"],
    "Montreal":  ["Downtown", "Plateau", "Blvd Saint-Laurent", "Decarie", "Old Port"],
    "Vancouver": ["Downtown", "Granville St", "Broadway", "Kingsway", "Marine Drive"],
    "Calgary":   ["Downtown Core", "Macleod Trail", "Deerfoot Trail", "17th Ave SW"],
    "Ottawa":    ["Downtown", "Queensway", "Bank St", "Rideau"],
    "Edmonton":  ["Downtown", "Whyte Ave", "Anthony Henday", "Jasper Ave"],
}

# format -> (is_digital, size range ft, traffic range/day, rate range CAD per 4 weeks)
# Rate ranges are built from published Canadian market benchmarks, not converted
# from anything. Rate and traffic ranges together are calibrated so the blended
# CPM lands in the CAD 8-15 band that COMMB market data implies, on a 28-day
# rate period. See docs/assumptions.md.
FORMATS = {
    # Static roadside: low end = suburban / secondary market, high end = urban.
    "bulletin":        (0, (14, 48), (20_000, 75_000),  (1_200, 10_000)),
    # Large-format digital, premium placements.
    "digital_screen":  (1, (10, 30), (35_000, 120_000), (10_000, 21_000)),
    "transit_shelter": (0, (4, 6),   (8_000,  33_000),  (1_000, 2_900)),
    "mall_panel":      (0, (3, 6),   (5_000,  23_000),  (850, 2_500)),
}
FORMAT_MIX = ["bulletin"]*12 + ["digital_screen"]*6 + ["transit_shelter"]*7 \
           + ["mall_panel"]*5

# Fictional brands — deliberately not real clients.
CLIENTS = [
    ("Aurora Beverages", "FMCG"),
    ("Nimbus Telecom",   "telecom"),
    ("Copper Kettle",    "QSR"),
    ("Vantage Motors",   "automotive"),
    ("Meridian Bank",    "banking"),
    ("Solstice Retail",  "retail"),
]

# Fraction of the passing audience assumed to actually see the ad.
# Varies by format; documented in docs/assumptions.md.
VISIBILITY = {
    "bulletin": 0.42, "digital_screen": 0.48, "transit_shelter": 0.30,
    "mall_panel": 0.34,
}

# Share of placements deliberately generated as under-performers.
UNDER_DELIVERY_RATE = 0.10


def allocate_cities(n):
    """
    Site counts strictly proportional to CMA population, by largest remainder.
    Deterministic on purpose: a random draw left small markets over-weighted,
    which inflated their modelled reach.
    """
    total = sum(m.CITY_POPULATION.values())
    exact  = {c: n * p / total for c, p in m.CITY_POPULATION.items()}
    counts = {c: int(v) for c, v in exact.items()}
    short  = n - sum(counts.values())
    for c, _ in sorted(exact.items(), key=lambda kv: -(kv[1] % 1))[:short]:
        counts[c] += 1
    return [c for c, k in counts.items() for _ in range(k)]


def make_sites(n=120):
    rows = []
    for sid, city in enumerate(allocate_cities(n), start=1):
        fmt = random.choice(FORMAT_MIX)
        is_digital, size_r, traffic_r, rate_r = FORMATS[fmt]
        # Tier 2 markets: less traffic past the site, and a rate card drawn from
        # the lower half of the band rather than the upper.
        lo, hi = rate_r
        mid = (lo + hi) // 2
        rate_r = (mid, hi) if city in TIER1 else (lo, mid)
        traffic_mult = 1.0 if city in TIER1 else TIER2_TRAFFIC
        w = round(random.uniform(*size_r), 1)
        h = round(w / random.uniform(1.8, 3.0), 1)
        rows.append((
            sid, city, random.choice(AREAS[city]), fmt, is_digital, w, h,
            int(random.randint(*traffic_r) * traffic_mult),
            # round the 4-week rate card to the nearest CAD 100
            int(round(random.randint(*rate_r), -2)),
        ))
    return rows


# Five campaigns have finished. Three are still in the air on AS_OF, caught at
# roughly a quarter, a half and three quarters of the way through their flight.
# Those three are the ones that exercise the prorated variance path: measured
# against the full contracted figure they would all read as heavily
# under-delivering purely because they are not finished yet.
IN_FLIGHT_PROGRESS = [0.25, 0.50, 0.75]


def make_campaigns():
    rows, first_start = [], date(2025, 1, 6)
    for cid in range(1, 9):
        client, industry = CLIENTS[(cid - 1) % len(CLIENTS)]
        weeks = random.choice([4, 6, 8, 12])
        live = cid > 8 - len(IN_FLIGHT_PROGRESS)
        if live:
            # Back-date the start so the flight is part way through on AS_OF.
            progress = IN_FLIGHT_PROGRESS[cid - (9 - len(IN_FLIGHT_PROGRESS))]
            s = AS_OF - timedelta(days=int(weeks * 7 * progress))
        else:
            # Completed flights: anywhere in the 14 months before AS_OF, long
            # enough ago that the flight has closed.
            s = first_start + timedelta(days=random.randint(0, 420))
        rows.append((
            cid, client, industry,
            random.choice(["awareness", "product_launch", "retail_drive"]),
            s.isoformat(), (s + timedelta(weeks=weeks)).isoformat(),
            random.randint(2, 40) * 20_000,   # campaign budget, CAD
        ))
    return rows


def make_placements(campaigns, sites):
    """One placement = one site booked for one campaign over a date window."""
    rows, pid = [], 1
    for c in campaigns:
        cid, _, _, _, c_start, c_end, _ = c
        # National campaigns for blue-chip clients book most of the inventory,
        # and sites are rebooked across campaigns (realistic for OOH).
        chosen = random.sample(sites, random.randint(56, 84))
        for s in chosen:
            site_id, _, _, fmt, _, _, _, traffic, rate_card = s
            days = (date.fromisoformat(c_end) - date.fromisoformat(c_start)).days
            # Contracted impressions = traffic x visibility factor x days.
            contracted = int(traffic * VISIBILITY[fmt] * days)
            discount = random.uniform(0.62, 0.95)          # agencies rarely pay rate card
            rows.append((pid, cid, site_id, c_start, c_end,
                         int(rate_card * discount), contracted))
            pid += 1
    return rows


def make_delivery(placements, site_lookup):
    """
    Daily delivery per placement.

    Most placements land within a few percent of plan. Roughly 10% materially
    under-deliver — sites go dark, posters get damaged, digital screens have
    downtime. Finding those is the point of the whole tool.

    A flight that is still in the air on AS_OF only has delivery reported up to
    AS_OF. Nothing is invented for days that have not happened yet, so verified
    impressions and contracted-to-date impressions cover the same window.
    """
    # Exactly 10% of placements under-deliver, drawn up front rather than by a
    # per-placement coin flip. A 10% flip over ~500 placements lands anywhere
    # from 6% to 14% depending on the seed, and the rate written down in
    # docs/assumptions.md should be the rate the data actually has.
    n_under = int(round(len(placements) * UNDER_DELIVERY_RATE))
    under_ids = set(random.sample([p[0] for p in placements], n_under))

    rows, did = [], 1
    for p in placements:
        pid, _, site_id, s, e, _, contracted = p
        fmt, is_digital = site_lookup[site_id]
        d0 = date.fromisoformat(s)
        flight_days = (date.fromisoformat(e) - d0).days
        # Days actually reported: the whole flight, or up to and including
        # AS_OF if the flight has not closed yet.
        days = min(flight_days, (AS_OF - d0).days + 1)
        daily_target = contracted / max(flight_days, 1)

        underperformer = pid in under_ids
        # Health multiplier applied across the whole flight.
        health = random.uniform(0.55, 0.82) if underperformer else random.uniform(0.96, 1.05)

        for k in range(days):
            day = d0 + timedelta(days=k)
            downtime = 0.0
            if is_digital and random.random() < (0.12 if underperformer else 0.03):
                downtime = round(random.uniform(1.0, 9.0), 1)
            est = int(daily_target * random.uniform(0.95, 1.05))
            ver = int(est * health * (1 - downtime / 24.0))
            rows.append((did, pid, day.isoformat(), est, max(ver, 0), downtime))
            did += 1
    return rows


def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(ROOT, "src", "schema.sql")) as f:
        con.executescript(f.read())

    sites = make_sites()
    campaigns = make_campaigns()
    placements = make_placements(campaigns, sites)
    lookup = {s[0]: (s[3], s[4]) for s in sites}
    delivery = make_delivery(placements, lookup)

    con.executemany("INSERT INTO sites VALUES (?,?,?,?,?,?,?,?,?)", sites)
    con.executemany("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?)", campaigns)
    con.executemany("INSERT INTO placements VALUES (?,?,?,?,?,?,?)", placements)
    con.executemany("INSERT INTO delivery VALUES (?,?,?,?,?,?)", delivery)
    con.commit()

    live = sum(1 for c in campaigns if date.fromisoformat(c[5]) > AS_OF)
    print(f"as of      {AS_OF.isoformat():>7}  ({live} campaigns still in flight)")
    print(f"sites      {len(sites):>7,}")
    print(f"campaigns  {len(campaigns):>7,}")
    print(f"placements {len(placements):>7,}")
    print(f"delivery   {len(delivery):>7,}")
    con.close()


if __name__ == "__main__":
    main()
