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

# Campaign names. Two per industry x objective, picked by how many times that
# client has already run that objective, so the name is deterministic and no two
# campaigns collide. Deliberately plain trade names -- the kind of thing that
# appears on a media plan, not advertising copy.
CAMPAIGN_NAMES = {
    ("FMCG", "awareness"):            ["Everyday Refresh", "Pour Something Better"],
    ("FMCG", "product_launch"):       ["Zero Sugar Launch", "Introducing Aurora Lite"],
    ("FMCG", "retail_drive"):         ["Cooler Season", "Stock Up Weekend"],
    ("telecom", "awareness"):         ["Coverage You Feel", "Built on Better Network"],
    ("telecom", "product_launch"):    ["Signal Everywhere", "The 5G Upgrade"],
    ("telecom", "retail_drive"):      ["Switch and Save", "Bring Your Own Phone"],
    ("QSR", "awareness"):             ["Made This Morning", "Worth the Walk"],
    ("QSR", "product_launch"):        ["The Winter Menu", "New Breakfast Range"],
    ("QSR", "retail_drive"):          ["Two Blocks Away", "Open Till Late"],
    ("automotive", "awareness"):      ["Built for the Drive", "Every Road North"],
    ("automotive", "product_launch"): ["Introducing the V60", "The Electric Range"],
    ("automotive", "retail_drive"):   ["Year End Event", "Demo Days"],
    ("banking", "awareness"):         ["Banking That Moves", "Ask Us Anything"],
    ("banking", "product_launch"):    ["The No-Fee Account", "Meridian One"],
    ("banking", "retail_drive"):      ["Open in Ten Minutes", "Branch Weekend"],
    ("retail", "awareness"):          ["Nothing Over Fifty", "Closer Than You Think"],
    ("retail", "product_launch"):     ["Autumn Collection", "The New Home Range"],
    ("retail", "retail_drive"):       ["Doors Open Saturday", "Final Markdowns"],
}

# Fraction of the passing audience assumed to actually see the ad.
# Varies by format; documented in docs/assumptions.md.
VISIBILITY = {
    "bulletin": 0.42, "digital_screen": 0.48, "transit_shelter": 0.30,
    "mall_panel": 0.34,
}

# --- the delivery health model ------------------------------------------------
# A placement does not under-deliver from the day it goes up. Something happens
# TO it: a poster tears, a site goes dark, a screen drops offline. So a fault is
# generated as an EVENT with an onset day, and sometimes a repair.
#
# This is what makes the product's central claim measurable rather than asserted.
# With a flight-long multiplier there is no such thing as "caught early" -- the
# problem was there on day one. With an onset day, the gap between when a fault
# starts and when the prorated variance crosses the flag line is a real number,
# and metrics.detection_timeline() recovers it from the delivery rows alone.
FAULT_RATE   = 0.20              # share of placements that develop a fault
RECOVERY_RATE = 0.55             # share of those faults that get repaired in flight
FAULT_ONSET_WINDOW = (0.10, 0.90)  # where in the flight a fault can begin
FAULT_DURATION_DAYS = (5, 21)      # how long a repaired fault lasts

# Daily delivery is drawn around the placement's CURRENT state, not its whole
# flight. The two bands are deliberately separated, and the arithmetic has to be
# checked rather than assumed, because the detector's 0.90 line depends on it:
#
#   healthy day  = est noise x healthy factor, worst case 0.95 x 0.97 = 0.922
#   fault day    = est noise x severity x daily band, best case
#                  1.05 x 0.80 x 1.06 = 0.890
#
# So the 0.90 line metrics.IMPAIRED_INDEX draws between them sits in a genuine
# gap rather than being tuned to a target. Raising FAULT_SEVERITY above 0.80
# closes that gap and the detector starts missing fault days -- if you change
# it, redo the arithmetic. Healthy variation is real variation; it just is not a
# fault, and the detector has to be able to tell the difference.
HEALTHY_BAND     = (0.97, 1.04)
FAULT_SEVERITY   = (0.45, 0.80)  # share of plan delivered while broken
FAULT_DAILY_BAND = (0.94, 1.06)  # day-to-day variation on top of the severity


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
    used = {}                      # (industry, objective) -> how many so far
    for cid in range(1, 9):
        client, industry = CLIENTS[(cid - 1) % len(CLIENTS)]
        weeks = random.choice([4, 6, 8, 12])
        objective = random.choice(["awareness", "product_launch", "retail_drive"])
        live = cid > 8 - len(IN_FLIGHT_PROGRESS)
        if live:
            # Back-date the start so the flight is part way through on AS_OF.
            progress = IN_FLIGHT_PROGRESS[cid - (9 - len(IN_FLIGHT_PROGRESS))]
            s = AS_OF - timedelta(days=int(weeks * 7 * progress))
        else:
            # Completed flights: anywhere in the 14 months before AS_OF, long
            # enough ago that the flight has closed.
            s = first_start + timedelta(days=random.randint(0, 420))
        # Deterministic name: the nth time this client runs this objective takes
        # the nth name from the pool, so re-running the generator never renames
        # a campaign.
        key = (industry, objective)
        names = CAMPAIGN_NAMES[key]
        name = names[used.get(key, 0) % len(names)]
        used[key] = used.get(key, 0) + 1
        rows.append((
            cid, name, client, industry, objective,
            s.isoformat(), (s + timedelta(weeks=weeks)).isoformat(),
            random.randint(2, 40) * 20_000,   # campaign budget, CAD
        ))
    return rows


def make_placements(campaigns, sites):
    """One placement = one site booked for one campaign over a date window."""
    rows, pid = [], 1
    for c in campaigns:
        cid, _, _, _, _, c_start, c_end, _ = c
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


def plan_faults(placements):
    """
    Decide, up front, which placements develop a fault and when.

    Drawn as a fixed sample rather than a per-placement coin flip: a 22% flip
    over ~600 placements lands anywhere from 18% to 26% depending on the seed,
    and the rate written down in docs/assumptions.md should be the rate the data
    actually has.

    Onset is a day in the flight, not a flag on the placement. A fault that
    begins at 80% of a flight still in the air may not have happened yet on
    AS_OF -- that placement simply reads healthy, which is exactly what a live
    book looks like.

    Returns {placement_id: (onset_day, repair_day or None, severity)}.
    """
    n_faults = int(round(len(placements) * FAULT_RATE))
    faulted = sorted(random.sample([p[0] for p in placements], n_faults))

    flight_days = {p[0]: (date.fromisoformat(p[4]) - date.fromisoformat(p[3])).days
                   for p in placements}
    plan = {}
    for pid in faulted:
        total = max(flight_days[pid], 1)
        lo, hi = FAULT_ONSET_WINDOW
        onset = int(total * random.uniform(lo, hi))
        severity = random.uniform(*FAULT_SEVERITY)
        repair = None
        if random.random() < RECOVERY_RATE:
            fixed_on = onset + random.randint(*FAULT_DURATION_DAYS)
            # A repair scheduled past the end of the flight never happens: the
            # fault simply runs out the campaign, which is the completed
            # shortfall case.
            repair = fixed_on if fixed_on < total else None
        plan[pid] = (onset, repair, severity)
    return plan


def make_delivery(placements, site_lookup, faults):
    """
    Daily delivery per placement, driven by the placement's state on each day.

    Each day the placement is either running normally or broken, and the day's
    delivery is drawn around that state. A repaired fault returns to the healthy
    band from the repair day onward, so a placement can read healthy, then
    behind, then recovering -- which is what delivery actually looks like and
    what makes a flight-day trajectory worth plotting.

    A flight still in the air on AS_OF only has delivery reported up to AS_OF.
    Nothing is invented for days that have not happened yet, so verified
    impressions and contracted-to-date impressions cover the same window.
    """
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
        onset, repair, severity = faults.get(pid, (None, None, None))

        for k in range(days):
            day = d0 + timedelta(days=k)
            broken = onset is not None and k >= onset and (repair is None or k < repair)
            # Digital screens drop offline far more often while something is
            # wrong with the site, which is part of why they fall behind.
            downtime = 0.0
            if is_digital and random.random() < (0.12 if broken else 0.03):
                downtime = round(random.uniform(1.0, 9.0), 1)
            factor = (severity * random.uniform(*FAULT_DAILY_BAND) if broken
                      else random.uniform(*HEALTHY_BAND))
            est = int(daily_target * random.uniform(0.95, 1.05))
            ver = int(est * factor * (1 - downtime / 24.0))
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
    faults = plan_faults(placements)
    delivery = make_delivery(placements, lookup, faults)

    con.executemany("INSERT INTO sites VALUES (?,?,?,?,?,?,?,?,?)", sites)
    con.executemany("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)", campaigns)
    con.executemany("INSERT INTO placements VALUES (?,?,?,?,?,?,?)", placements)
    con.executemany("INSERT INTO delivery VALUES (?,?,?,?,?,?)", delivery)
    con.commit()

    live = sum(1 for c in campaigns if date.fromisoformat(c[6]) > AS_OF)
    print(f"as of      {AS_OF.isoformat():>7}  ({live} campaigns still in flight)")
    print(f"sites      {len(sites):>7,}")
    print(f"campaigns  {len(campaigns):>7,}")
    print(f"placements {len(placements):>7,}")
    print(f"delivery   {len(delivery):>7,}")
    report_detection(placements, delivery, faults)
    con.close()


def report_detection(placements, delivery, faults):
    """
    Check what the detector recovers, and say so.

    The fault plan is NOT written to the database. It exists here only so this
    report can measure metrics.detection_timeline() against ground truth -- the
    analyzer itself only ever sees delivery rows, which is the whole point of
    the exercise. If the numbers below are good, it is because delivery problems
    are visible in delivery data, not because the dashboard was handed the
    answer.
    """
    by_placement = {}
    for _, pid, day, _, ver, _ in delivery:
        by_placement.setdefault(pid, []).append(ver)

    began, detected, onset_error, delays, recon = 0, 0, [], [], []
    recovered = continuing = subthreshold = 0
    for p in placements:
        pid, _, _, s, e, _, contracted = p
        flight_days = (date.fromisoformat(e) - date.fromisoformat(s)).days
        series = by_placement.get(pid, [])
        planned_daily = contracted / max(flight_days, 1)
        t = m.detection_timeline(series, planned_daily, flight_days)

        true_onset, repair, _ = faults.get(pid, (None, None, None))
        # A fault scheduled for a day the flight has not reached yet has not
        # happened, and nothing should have detected it.
        if true_onset is None or true_onset >= len(series):
            continue
        began += 1
        if t["observed_onset_day"] is not None:
            detected += 1
            onset_error.append(abs(t["observed_onset_day"] - true_onset))
            if t["recovered"]:
                recovered += 1
            else:
                continuing += 1
        if t["alert_day"] is not None:
            delays.append(t["detection_delay_days"])
            recon.append(t["reconciliation_delay_days"])
        else:
            subthreshold += 1

    def med(xs):
        # A real median, averaging the two middle values on an even count --
        # xs[len // 2] alone disagrees with the figure export_json.py reports
        # for the same population, and two different numbers for one statistic
        # is exactly the kind of thing that gets noticed.
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return float("nan")
        mid = len(xs) // 2
        return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2

    print(f"\nfaults injected      {len(faults):>5}   ({began} began inside the reported window)")
    print(f"  detected from data {detected:>5}   ({detected / began * 100:.1f}% of those that began)")
    print(f"  onset day error    {med(onset_error):>5.0f}   days, median")
    print(f"  repaired in flight {recovered:>5}   still broken {continuing}")
    print(f"  crossed the -5% line, so visible in the Attention Centre: {len(delays)}")
    print(f"  too small to flag  {subthreshold:>5}   (real faults, under the threshold so far)")
    print(f"\ndetection delay      {med(delays):>5.1f}   days from fault to flag, median")
    print(f"reconciliation delay {med(recon):>5.1f}   days from fault to end of flight, median")


if __name__ == "__main__":
    main()
