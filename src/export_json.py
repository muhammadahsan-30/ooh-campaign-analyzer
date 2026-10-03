"""
Runs the metrics layer over the database and writes public/data.json and
public/data.js, which the static dashboard reads.

Nothing is computed in the browser. Every figure the interface shows is produced
here by calling src/metrics.py, which is where the formulas live and where the
unit tests point. This file assembles and validates; it never re-implements a
metric inline.
"""
import json, os, sqlite3, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get("OOH_DB", os.path.join(ROOT, "data", "ooh.db"))
OUT  = os.path.join(ROOT, "public", "data.json")

# A live issue holding less than this much preventable exposure is real but not
# worth a phone call today. It splits the live queue into what to act on now and
# what to keep an eye on -- a materiality cut, not a severity one.
MATERIAL_EXPOSURE = 1_000.0      # CAD


def load(con):
    """
    One row per placement, with campaign and site attributes joined on.

    Spend is NOT computed here. The rate is a four-week figure and a placement
    may still be in the air, so turning it into money needs the elapsed-days
    logic that lives in metrics.spend_to_date() and is unit-tested there.
    """
    return pd.read_sql_query("""
        SELECT p.placement_id, p.campaign_id, p.site_id,
               p.negotiated_rate, p.contracted_impressions,
               p.start_date, p.end_date,
               c.campaign_name, c.client_name, c.industry, c.objective,
               c.start_date AS campaign_start, c.end_date AS campaign_end,
               s.city, s.area, s.format, s.is_digital, s.rate_card_monthly,
               SUM(d.verified_impressions)  AS verified_impressions,
               SUM(d.estimated_impressions) AS estimated_impressions,
               SUM(d.downtime_hours)        AS downtime_hours,
               COUNT(d.date)                AS delivery_days,
               MAX(d.date)                  AS last_delivery_date
        FROM placements p
        JOIN campaigns c ON c.campaign_id = p.campaign_id
        JOIN sites     s ON s.site_id     = p.site_id
        JOIN delivery  d ON d.placement_id = p.placement_id
        GROUP BY p.placement_id
    """, con)


def load_daily(con):
    """Every delivery row, in date order, for the day-by-day fault detection."""
    return pd.read_sql_query("""
        SELECT placement_id, date, verified_impressions
        FROM delivery ORDER BY placement_id, date
    """, con)


def enrich(df, daily, as_of):
    """Every per-placement metric the payload needs, merged onto one frame."""
    var   = m.delivery_vs_contract(df, as_of)
    money = m.spend_to_date(df, as_of)
    df = df.merge(var[["placement_id", "flight_days", "elapsed_days", "in_flight",
                       "contracted_to_date", "variance_abs", "variance_pct"]],
                  on="placement_id")
    df = df.merge(money[["placement_id", "spend"]], on="placement_id")

    # The elapsed-day arithmetic and the delivery table have to agree, or every
    # "to date" figure on the page is measured over the wrong window.
    mismatch = df[df["elapsed_days"] != df["delivery_days"]]
    if len(mismatch):
        raise SystemExit(f"elapsed_days disagrees with delivery rows on "
                         f"{len(mismatch)} placements: {list(mismatch['placement_id'][:5])}")

    pace = m.pacing(df, as_of)
    cost = m.cpm(df)
    rate = m.rate_efficiency(df)
    for frame, cols in ((pace, ["remaining_days", "planned_daily", "delivery_index",
                                "remaining_contracted", "required_daily", "recovery_pace"]),
                        (cost, ["cpm"]), (rate, ["discount_pct"])):
        df = df.merge(frame[["placement_id"] + cols], on="placement_id")

    # Day-by-day fault detection, from the delivery rows alone. The generator's
    # fault plan is never written to the database and is never read here.
    series = daily.groupby("placement_id")["verified_impressions"].apply(list)
    timelines = []
    for row in df.itertuples():
        t = m.detection_timeline(series.get(row.placement_id, []),
                                 row.planned_daily, row.flight_days)
        t["placement_id"] = row.placement_id
        timelines.append(t)
    df = df.merge(pd.DataFrame(timelines), on="placement_id")

    # The rate each placement is running at NOW. A placement still inside an
    # unrepaired fault is losing impressions at the fault's rate, not at the
    # cumulative average its healthy early weeks flatter. Exposure for the rest
    # of the flight has to be priced on the former.
    broken = df["observed_onset_day"].notna() & ~df["recovered"]
    df["current_index"] = df["delivery_index"].where(~broken, df["fault_index"])
    expo = m.exposure(df, as_of, current_index=df["current_index"])
    df = df.merge(expo[["placement_id", "shortfall", "contracted_cpm",
                        "billed_shortfall", "daily_bleed", "preventable_exposure"]],
                  on="placement_id")

    # Which placements are flagged is decided by the tested function, not by a
    # threshold repeated here. One source of truth for the headline number.
    flagged = set(m.delivery_variance_ranked(df, as_of=as_of)["placement_id"])
    df["flagged"] = df["placement_id"].isin(flagged)
    df["status"] = "on_track"
    df.loc[df["flagged"] & df["in_flight"], "status"] = "live_issue"
    df.loc[df["flagged"] & ~df["in_flight"], "status"] = "completed_shortfall"
    df["material"] = df["preventable_exposure"] >= MATERIAL_EXPOSURE
    return df


def num(x):
    """JSON-safe float: pandas NA becomes null rather than NaN."""
    return None if pd.isna(x) else float(x)


def placement_record(r):
    """One placement, as the Attention Centre and drill-down tables need it."""
    return {
        "placement_id": int(r.placement_id),
        "campaign_id": int(r.campaign_id),
        "campaign_name": r.campaign_name,
        "client": r.client_name,
        "objective": r.objective,
        "city": r.city, "area": r.area, "format": r.format,
        "site_id": int(r.site_id),
        "is_digital": bool(r.is_digital),
        "status": r.status, "material": bool(r.material),
        "flight_days": int(r.flight_days), "elapsed_days": int(r.elapsed_days),
        "remaining_days": int(r.remaining_days),
        "in_flight": bool(r.in_flight),
        "start": r.start_date, "end": r.end_date,
        "contracted_impressions": float(r.contracted_impressions),
        "contracted_to_date": float(r.contracted_to_date),
        "verified_impressions": float(r.verified_impressions),
        "variance_pct": num(r.variance_pct),
        "delivery_index": num(r.delivery_index),
        "shortfall": float(r.shortfall),
        "spend": float(r.spend),
        "cpm": num(r.cpm),
        "billed_shortfall": float(r.billed_shortfall),
        "preventable_exposure": float(r.preventable_exposure),
        "required_daily": num(r.required_daily),
        "planned_daily": num(r.planned_daily),
        "recovery_pace": num(r.recovery_pace),
        "downtime_hours": float(r.downtime_hours),
        # Detection history, derived from the daily delivery series.
        "onset_day": None if pd.isna(r.observed_onset_day) else int(r.observed_onset_day),
        "alert_day": None if pd.isna(r.alert_day) else int(r.alert_day),
        "recovered": bool(r.recovered),
        "detection_delay_days": None if pd.isna(r.detection_delay_days) else int(r.detection_delay_days),
        "reconciliation_delay_days": None if pd.isna(r.reconciliation_delay_days) else int(r.reconciliation_delay_days),
        "days_remaining_at_detection": None if pd.isna(r.days_remaining_at_detection) else int(r.days_remaining_at_detection),
        "fault_index": num(r.fault_index),
        "pre_fault_index": num(r.pre_fault_index),
    }


def downtime_attribution(r):
    """
    How much of a digital placement's shortfall its logged outages explain.

    Downtime removes delivery pro rata on the day it happens, so the impressions
    lost to it are recoverable exactly:

        lost = estimated impressions x downtime hours / (24 x days reported)

    Reported alongside what it does NOT explain, because on this dataset it is a
    minor cause and claiming otherwise would be the more impressive answer and
    the wrong one.
    """
    if not r.is_digital or r.shortfall <= 0 or r.elapsed_days <= 0:
        return None
    lost = r.estimated_impressions * r.downtime_hours / (24 * r.elapsed_days)
    return {"hours": float(r.downtime_hours), "impressions": float(lost),
            "share_of_shortfall_pct": float(lost / r.shortfall * 100)}


def contribution(g, key):
    """
    Which markets (or formats) a campaign's shortfall actually comes from.

    Reported as gross, offset and net per group, because a market can be carrying
    real shortfall that the campaign total nets away. Sorted by net, worst first.
    """
    rows = []
    for k, sub in g.groupby(key):
        d = m.shortfall_decomposition(sub)
        rows.append({
            "key": k,
            "placements": int(len(sub)),
            "gross_shortfall": d["gross_shortfall"],
            "net_shortfall": d["net_shortfall"],
            "masking_pct": d["masking_pct"],
            "variance_pct": d["variance_pct"],
            "billed_shortfall": float(sub["billed_shortfall"].sum()),
            "flagged": int(sub["flagged"].sum()),
        })
    rows.sort(key=lambda r: -r["net_shortfall"])
    total = sum(r["net_shortfall"] for r in rows if r["net_shortfall"] > 0)
    for r in rows:
        r["share_pct"] = (r["net_shortfall"] / total * 100) if total > 0 else 0.0
    return rows


def trajectory(daily_campaign, cid, contracted_total, flight_days):
    """
    Cumulative delivery against the cumulative contracted line, by flight day.

    Flight day rather than calendar date, so the chart is about this campaign's
    progress rather than about which month it happened to run in. The expected
    line is the contracted total spread evenly across the booked flight -- the
    same straight-line proration every other figure uses.
    """
    g = daily_campaign[daily_campaign["campaign_id"] == cid].sort_values("date")
    per_day = float(contracted_total) / max(flight_days, 1)
    actual, expected, running = [], [], 0.0
    for k, v in enumerate(g["verified_impressions"]):
        running += float(v)
        actual.append(round(running))
        expected.append(round(per_day * (k + 1)))
    return {"actual": actual, "expected": expected}


def build_campaigns(df, daily_campaign):
    """One record per campaign, including everything the drill-down view needs."""
    out = []
    for cid, g in df.groupby("campaign_id"):
        d = m.shortfall_decomposition(g)
        # Reach is computed PER MARKET and summed as people, never averaged as
        # percentages, so a national buy cannot saturate one CMA. Cross-market
        # duplication is not removed, so campaign reach is an upper bound.
        reached, population, markets = 0.0, 0, []
        for city, cg in g.groupby("city"):
            pop = m.CITY_POPULATION.get(city, 1_000_000)
            reached += m.reach_frequency(float(cg["verified_impressions"].sum()), pop)["reach"]
            population += pop
            markets.append(city)
        delivered = float(g["verified_impressions"].sum())
        elapsed, flight = int(g["elapsed_days"].max()), int(g["flight_days"].max())
        contracted_full = float(g["contracted_impressions"].sum())

        onsets = g["observed_onset_day"].dropna().astype(int)
        out.append({
            "campaign_id": int(cid),
            "name": g["campaign_name"].iloc[0],
            "client": g["client_name"].iloc[0],
            "industry": g["industry"].iloc[0],
            "objective": g["objective"].iloc[0],
            "start": g["campaign_start"].iloc[0], "end": g["campaign_end"].iloc[0],
            "in_flight": bool(g["in_flight"].any()),
            "placements": int(len(g)),
            "elapsed_days": elapsed, "flight_days": flight,
            "progress_pct": elapsed / flight * 100 if flight else 0.0,
            # Delivered as a share of the WHOLE contract, so it sits on the same
            # 0-100% scale as flight progress and the two bars can be compared.
            "delivered_pct": delivered / contracted_full * 100 if contracted_full else 0.0,
            "spend": float(g["spend"].sum()),
            "contracted_to_date": float(g["contracted_to_date"].sum()),
            "contracted_full_flight": contracted_full,
            "delivered": delivered,
            "variance_pct": d["variance_pct"],
            "gross_shortfall": d["gross_shortfall"],
            "over_delivery_offset": d["over_delivery_offset"],
            "net_shortfall": d["net_shortfall"],
            "masking_pct": d["masking_pct"],
            "placements_behind": d["placements_behind"],
            "live_issues": int((g["status"] == "live_issue").sum()),
            "completed_shortfalls": int((g["status"] == "completed_shortfall").sum()),
            "billed_shortfall": float(g.loc[g["flagged"], "billed_shortfall"].sum()),
            "preventable_exposure": float(g["preventable_exposure"].sum()),
            "cpm": float(g["spend"].sum() / delivered * 1000) if delivered else None,
            "discount_pct": float((g["discount_pct"] * g["spend"]).sum() / g["spend"].sum()),
            "markets": len(markets), "market_list": sorted(markets),
            "reach_pct": round(reached / population * 100, 1) if population else 0.0,
            "frequency": round(delivered / reached, 1) if reached else 0.0,
            "daily_grp": round(m.daily_grp(delivered, population, elapsed), 1),
            "by_market": contribution(g, "city"),
            "by_format": contribution(g, "format"),
            "trajectory": trajectory(daily_campaign, cid, contracted_full, flight),
            # When faults started, by flight day. Real temporal signal now that
            # faults have onset dates; empty for a campaign that never broke.
            "fault_onsets": [[int(k), int(v)] for k, v in
                             sorted(onsets.value_counts().items())],
        })
    out.sort(key=lambda c: (not c["in_flight"], -c["billed_shortfall"]))
    return out


def build_inventory(df):
    """
    Site-level delivery history, and an honest test of whether it means anything.

    Sites are rebooked across campaigns, so "does this site deliver when we book
    it?" is answerable. Whether the answer carries information is a separate
    question, and it is tested rather than assumed: if repeat flagging is no more
    common than chance, the panel says so instead of ranking noise.
    """
    rows = []
    for sid, g in df.groupby("site_id"):
        contracted = float(g["contracted_to_date"].sum())
        rows.append({
            "site_id": int(sid), "city": g["city"].iloc[0], "area": g["area"].iloc[0],
            "format": g["format"].iloc[0], "is_digital": bool(g["is_digital"].iloc[0]),
            "campaigns_booked": int(g["campaign_id"].nunique()),
            "placements": int(len(g)),
            # Impression-weighted, not a mean of ratios: a site's big bookings
            # should count for more than its small ones.
            "delivery_pct": float(g["verified_impressions"].sum() / contracted * 100)
                            if contracted else None,
            "times_flagged": int(g["flagged"].sum()),
            "downtime_hours_per_day": float(g["downtime_hours"].sum() / g["elapsed_days"].sum())
                                      if bool(g["is_digital"].iloc[0]) else None,
        })
    rows.sort(key=lambda r: r["delivery_pct"] if r["delivery_pct"] is not None else 999)

    # Chance baseline. If each booking independently had the overall flag rate,
    # how many sites would be flagged twice or more anyway?
    p = float(df["flagged"].mean())
    expected = 0.0
    for r in rows:
        n = r["placements"]
        # P(at least two flags) = 1 - P(none) - P(exactly one)
        none_ = (1 - p) ** n
        one   = n * p * (1 - p) ** (n - 1) if n else 0.0
        expected += 1 - none_ - one
    observed = sum(1 for r in rows if r["times_flagged"] >= 2)
    return rows, {"observed_repeat_sites": observed,
                  "expected_by_chance": round(expected, 1),
                  "flag_rate_pct": p * 100}


def build_efficiency(df):
    """
    Cost per thousand, grouped so that only comparable things sit on one axis.

    A digital face rotates in a shared loop: an advertiser buys a share of loop
    time, not the exclusive presence a static bulletin holds for the whole
    flight. This model does not represent share of loop, so digital and static
    CPM are NOT directly comparable and are not ranked against each other.
    Static formats are ranked among themselves, digital is reported on its own,
    and the limitation is stated rather than hidden.

    The CPM premium is the one figure that IS comparable across formats, because
    it is a within-format ratio: delivered CPM / contracted CPM, which is simply
    contracted-to-date over delivered. It answers "how much more did a thousand
    impressions actually cost than we booked it for", and under-delivery is the
    only thing that moves it.
    """
    def group(sub):
        rows = []
        for k, g in sub.groupby("format"):
            delivered = float(g["verified_impressions"].sum())
            contracted = float(g["contracted_to_date"].sum())
            spend = float(g["spend"].sum())
            rows.append({
                "key": k, "placements": int(len(g)), "spend": spend,
                "delivered": delivered, "contracted_to_date": contracted,
                "cpm": spend / delivered * 1000 if delivered else None,
                "contracted_cpm": spend / contracted * 1000 if contracted else None,
                "cpm_premium_pct": (contracted / delivered - 1) * 100 if delivered else None,
            })
        rows.sort(key=lambda r: r["cpm"] if r["cpm"] is not None else 0)
        return rows

    return {"static": group(df[df["is_digital"] == 0]),
            "digital": group(df[df["is_digital"] == 1]),
            "premium_all": sorted(group(df), key=lambda r: -(r["cpm_premium_pct"] or 0))}


def build_summary(df, con, as_of):
    """The portfolio headline: one honest topline, and what it is hiding."""
    d = m.shortfall_decomposition(df)
    flagged = df[df["flagged"]]
    live = flagged[flagged["in_flight"]]
    done = flagged[~flagged["in_flight"]]
    material = live[live["material"]]
    delivered = float(df["verified_impressions"].sum())
    contracted = float(df["contracted_to_date"].sum())

    # Detection, measured across the placements that actually broke. This is the
    # project's central claim, and it is a measurement rather than a slogan.
    caught = df[df["detection_delay_days"].notna()]
    return {
        "as_of": as_of.date().isoformat(),
        "campaigns": int(df["campaign_id"].nunique()),
        "in_flight_campaigns": int(df[df["in_flight"]]["campaign_id"].nunique()),
        "clients": int(df["client_name"].nunique()),
        "sites": int(pd.read_sql_query("SELECT COUNT(*) n FROM sites", con)["n"][0]),
        "placements": int(len(df)),
        "live_placements": int(df["in_flight"].sum()),
        "closed_placements": int((~df["in_flight"]).sum()),
        "delivery_rows": int(pd.read_sql_query("SELECT COUNT(*) n FROM delivery", con)["n"][0]),
        "spend": float(df["spend"].sum()),
        "delivered": delivered,
        "contracted": contracted,
        "contracted_full_flight": float(df["contracted_impressions"].sum()),
        "delivery_to_plan_pct": delivered / contracted * 100 if contracted else 0.0,
        "variance_pct": d["variance_pct"],
        # What the headline would read if over-delivery did not net off against
        # shortfall. The interface shows the two side by side; neither is
        # derived in the browser.
        "gross_shortfall_pct": -d["gross_shortfall"] / contracted * 100 if contracted else 0.0,
        "blended_cpm": float(df["spend"].sum() / delivered * 1000),
        # Spend-weighted, so it reads as the discount achieved on the money spent.
        "avg_discount_pct": float((df["discount_pct"] * df["spend"]).sum() / df["spend"].sum()),
        # The tension the whole product exists to surface.
        "gross_shortfall": d["gross_shortfall"],
        "over_delivery_offset": d["over_delivery_offset"],
        "net_shortfall": d["net_shortfall"],
        "masking_pct": d["masking_pct"],
        "placements_behind": d["placements_behind"],
        "on_track": int((df["status"] == "on_track").sum()),
        "live_issues": int(len(live)),
        "completed_shortfalls": int(len(done)),
        # TWO NAMED MEASURES OVER TWO POPULATIONS. They are not interchangeable
        # and must never share a label:
        #
        #   flagged media-value exposure  - the 82 placements that breach the -5%
        #                                   attention line. This is the number the
        #                                   Attention Centre acts on.
        #   total negative delivery       - every placement behind by any amount
        #     exposure                      (227 here), which is the population
        #                                   gross_shortfall is also measured over.
        #
        # Reporting the first beside gross shortfall without saying so compares a
        # 227-placement impression figure against an 82-placement money figure.
        # Both are exported so the interface can be explicit about which is which.
        "total_negative_exposure": float(df["billed_shortfall"].sum()),
        "billed_shortfall": float(flagged["billed_shortfall"].sum()),
        "billed_shortfall_live": float(live["billed_shortfall"].sum()),
        "billed_shortfall_completed": float(done["billed_shortfall"].sum()),
        "preventable_exposure": float(live["preventable_exposure"].sum()),
        "material_issues": int(len(material)),
        "material_exposure": float(material["preventable_exposure"].sum()),
        "material_threshold": MATERIAL_EXPOSURE,
        "detection": {
            "faults_detected": int(df["observed_onset_day"].notna().sum()),
            "faults_recovered": int(df["recovered"].sum()),
            "alerted": int(len(caught)),
            "median_detection_delay_days": num(caught["detection_delay_days"].median()),
            "median_reconciliation_delay_days": num(caught["reconciliation_delay_days"].median()),
            "median_days_remaining_at_detection": num(
                caught[caught["in_flight"]]["days_remaining_at_detection"].median()),
        },
    }


def slim(r):
    """A placement as a contribution-table row: identity, size, and impact."""
    return {
        "placement_id": int(r.placement_id), "campaign_id": int(r.campaign_id),
        "city": r.city, "area": r.area, "format": r.format, "site_id": int(r.site_id),
        "status": r.status, "in_flight": bool(r.in_flight),
        "variance_pct": num(r.variance_pct), "shortfall": float(r.shortfall),
        "contracted_to_date": float(r.contracted_to_date),
        "verified_impressions": float(r.verified_impressions),
        "spend": float(r.spend), "billed_shortfall": float(r.billed_shortfall),
        "preventable_exposure": float(r.preventable_exposure),
    }


ASSUMPTIONS = {
    "as_of_basis": "Everything is measured to {as_of}, the last day delivery was reported. A campaign still in the air is compared against its contracted impressions PRORATED to the days elapsed (contracted x elapsed / flight days), not the full-flight figure - otherwise a healthy placement three weeks into a twelve-week flight would read as -75%. Proration assumes contracted delivery is flat across the flight.",
    "gross_vs_net": "Campaign and portfolio variance NET over-delivery against under-delivery. Gross shortfall is the sum of shortfalls on placements that are behind, with no credit for placements running hot: over-delivery on one site does not repair a dark site on another. Both figures are reported everywhere, because the gross one is operational and the net one is accounting.",
    "fault_model": "Under-delivery is generated as an EVENT with an onset day, not as a flight-long multiplier. A placement runs healthy, then something happens to it, and sometimes it is repaired. Faults are detected from the daily delivery series alone - three consecutive days below 90% of planned daily delivery - and the generator's fault plan is never written to the database or read by the analyzer.",
    "detection": "Detection delay is the days between a fault starting and cumulative prorated delivery crossing the -5% line, which is the day this tool would have shown the problem. Reconciliation delay is the days between the fault starting and the end of the flight, which is when an end-of-campaign reconciliation would have found it by hand. The gap between the two is the time the tool buys.",
    "preventable_exposure": "MODELLED. The media value that accrues over the remaining flight if a live issue is not fixed, priced at the placement's contracted CPM. It assumes today's shortfall rate continues for the days that are left, which is a statement about the future. It is never added to billed shortfall: one is money already spent on impressions not delivered, the other is money not yet lost.",
    "recovery_pace": "Required daily delivery divided by planned daily delivery - what finishing the contract whole would TAKE, not a forecast that it will happen. A healthy face in this model delivers 0.96-1.05 of plan, so a pace much above 1.05 is beyond what the booked face can do and the gap closes with added weight or a make-good.",
    "visibility_factors": "Share of passing traffic assumed to see the ad; varies 0.30-0.48 by format. A planning convention, not a measurement.",
    "reach_model": "MODELLED. Computed per market against that CMA's population, then summed as people: reach = population x (1 - (1 - 0.35) ** (impressions / population)). A planning convention. Cross-market duplication is not removed, so national reach is an upper bound.",
    "market_tiers": "Traffic and rate card both scale by market tier - Tier 1 (Toronto, Montreal, Vancouver) 1.0x traffic and upper-half rates; Tier 2 (Calgary, Ottawa, Edmonton) 0.6x traffic and lower-half rates - so CPM stays comparable across markets while volume falls with market size.",
    "spend_basis": "Spend prorates each placement's 4-week (28-day) negotiated rate to the days that have actually run (rate x elapsed days / 28), so spend and impressions cover the same window.",
    "digital_vs_static_cpm": "A digital face rotates in a shared loop: its impressions are a share of loop time, not the exclusive presence a static bulletin holds for the whole flight. This model does not represent share of loop, so digital and static CPM are NOT ranked against each other. Static formats are compared among themselves; digital is reported separately. The CPM premium - delivered CPM against contracted CPM - is comparable across formats, because it is a within-format ratio.",
    "inventory_reliability": "Sites are rebooked across campaigns, so repeat under-delivery is measurable. Whether it is MEANINGFUL is tested rather than assumed: the generator gives no site a persistent quality, so repeat flagging should be no more common than chance, and the panel reports that comparison instead of ranking noise.",
    "downtime": "Digital downtime removes delivery pro rata on the day it occurs, so impressions lost to it are computed exactly. It explains only a minority of digital shortfall, and is reported alongside what it does not explain.",
}


def main():
    con = sqlite3.connect(DB)
    df = load(con)
    daily = load_daily(con)
    as_of = m.as_of_date(df)
    df = enrich(df, daily, as_of)

    # Daily totals per campaign, for the flight-day trajectory.
    daily_campaign = (daily.merge(df[["placement_id", "campaign_id"]], on="placement_id")
                           .groupby(["campaign_id", "date"], as_index=False)
                           ["verified_impressions"].sum())

    live = df[df["status"] == "live_issue"].sort_values("preventable_exposure", ascending=False)
    done = df[df["status"] == "completed_shortfall"].sort_values("billed_shortfall", ascending=False)
    campaigns = build_campaigns(df, daily_campaign)
    inventory, baseline = build_inventory(df)

    # Top contributors per campaign, for the drill-down placement table. The
    # whole 595 would triple the payload to show rows nobody scrolls to.
    top = {}
    for cid, g in df.groupby("campaign_id"):
        rows = g.sort_values("shortfall", ascending=False).head(10)
        top[str(int(cid))] = [slim(r) for r in rows.itertuples()]

    payload = {
        "generated_note": "All data synthetic, modelled on the Canadian out-of-home market (CMA populations, Canadian format names, rate cards from published market benchmarks). Figures in CAD. No real agency or client data.",
        "summary": build_summary(df, con, as_of),
        "campaigns": campaigns,
        "attention": {
            "live": [placement_record(r) for r in live.itertuples()],
            "completed": [placement_record(r) for r in done.itertuples()],
        },
        "downtime": {str(int(r.placement_id)): downtime_attribution(r)
                     for r in df[df["is_digital"] == 1].itertuples()
                     if downtime_attribution(r)},
        "by_market": contribution(df, "city"),
        "by_format": contribution(df, "format"),
        "by_client": contribution(df, "client_name"),
        "top_placements": top,
        "inventory": inventory,
        "inventory_baseline": baseline,
        "efficiency": build_efficiency(df),
        "assumptions": {k: v.format(as_of=as_of.date().isoformat())
                        for k, v in ASSUMPTIONS.items()},
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    # data.js as well: browsers block fetch() against file:// URLs, so a plain
    # <script> tag is the only way the dashboard opens straight from disk.
    with open(OUT.replace(".json", ".js"), "w") as f:
        f.write("window.OOH_DATA = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";")
    con.close()

    s = payload["summary"]
    print(f"as of          {s['as_of']:>12}  ({s['in_flight_campaigns']} of {s['campaigns']} campaigns in flight)")
    print(f"placements     {s['placements']:>12,}  ({s['live_placements']} live, {s['closed_placements']} closed)")
    print(f"delivery       {s['delivery_to_plan_pct']:>12.1f} % of plan to date")
    print(f"gross short    {s['gross_shortfall']:>12,.0f}  ({s['masking_pct']:.0f}% masked by over-delivery)")
    print(f"live issues    {s['live_issues']:>12}  ({s['material_issues']} material, ${s['material_exposure']:,.0f} preventable)")
    print(f"completed      {s['completed_shortfalls']:>12}  (${s['billed_shortfall_completed']:,.0f} to reconcile)")
    print(f"detection      {s['detection']['median_detection_delay_days']:>12.1f}  days median, vs "
          f"{s['detection']['median_reconciliation_delay_days']:.0f} to reconciliation")
    print(f"\nwrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
