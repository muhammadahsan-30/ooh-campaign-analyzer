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
# from anything. Traffic ranges are calibrated so the blended CPM lands in the
# CAD 8-15 band that COMMB market data implies. See docs/assumptions.md.
FORMATS = {
    # Static roadside: low end = suburban / secondary market, high end = urban.
    "bulletin":        (0, (14, 48), (20_000, 75_000),  (1_500, 12_000)),
    # Large-format digital, premium placements.
    "digital_screen":  (1, (10, 30), (35_000, 120_000), (12_000, 25_000)),
    "transit_shelter": (0, (4, 6),   (8_000,  33_000),  (1_200, 3_500)),
    "mall_panel":      (0, (3, 6),   (5_000,  23_000),  (1_000, 3_000)),
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


def make_campaigns():
    rows, start = [], date(2025, 1, 6)
    for cid in range(1, 9):
        client, industry = CLIENTS[(cid - 1) % len(CLIENTS)]
        s = start + timedelta(days=random.randint(0, 420))
        weeks = random.choice([4, 6, 8, 12])
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
    """
    rows, did = [], 1
    for p in placements:
        pid, _, site_id, s, e, _, contracted = p
        fmt, is_digital = site_lookup[site_id]
        days = (date.fromisoformat(e) - date.fromisoformat(s)).days
        daily_target = contracted / max(days, 1)

        underperformer = random.random() < 0.10
        # Health multiplier applied across the whole flight.
        health = random.uniform(0.55, 0.82) if underperformer else random.uniform(0.96, 1.05)

        d0 = date.fromisoformat(s)
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

    print(f"sites      {len(sites):>7,}")
    print(f"campaigns  {len(campaigns):>7,}")
    print(f"placements {len(placements):>7,}")
    print(f"delivery   {len(delivery):>7,}")
    con.close()


if __name__ == "__main__":
    main()
