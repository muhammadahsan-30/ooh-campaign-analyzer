"""
Runs the metrics layer over the database and writes public/data.json,
which the static dashboard reads. Nothing is computed in the browser --
the numbers on screen come from here.
"""
import json, os, sqlite3, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get("OOH_DB", os.path.join(ROOT, "data", "ooh.db"))
OUT  = os.path.join(ROOT, "public", "data.json")


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
               c.client_name, c.industry, c.objective,
               c.start_date AS campaign_start, c.end_date AS campaign_end,
               s.city, s.area, s.format, s.rate_card_monthly,
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


def main():
    con = sqlite3.connect(DB)
    df = load(con)

    # The as-of date: the last day anything was reported. Everything below is
    # measured to this date, not to the end of the contracted flight.
    as_of = m.as_of_date(df)

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

    cost = m.cpm(df)
    rate = m.rate_efficiency(df)
    df = df.merge(cost[["placement_id", "cpm"]], on="placement_id")
    df = df.merge(rate[["placement_id", "discount_pct"]], on="placement_id")

    # Which placements are flagged is decided by the tested function, not by a
    # threshold repeated here. One source of truth for the headline number.
    ranked = m.delivery_variance_ranked(df, as_of=as_of)
    under  = df[df["placement_id"].isin(ranked["placement_id"])]

    summary = {
        "as_of":       as_of.date().isoformat(),
        "in_flight_campaigns": int(df[df["in_flight"]]["campaign_id"].nunique()),
        "sites":       int(pd.read_sql_query("SELECT COUNT(*) n FROM sites", con)["n"][0]),
        "campaigns":   int(df["campaign_id"].nunique()),
        "clients":     int(df["client_name"].nunique()),
        "placements":  int(len(df)),
        "delivery_rows": int(pd.read_sql_query("SELECT COUNT(*) n FROM delivery", con)["n"][0]),
        "spend":       float(df["spend"].sum()),
        "delivered":   float(df["verified_impressions"].sum()),
        "contracted":  float(df["contracted_to_date"].sum()),
        "contracted_full_flight": float(df["contracted_impressions"].sum()),
        "blended_cpm": float(df["spend"].sum() / df["verified_impressions"].sum() * 1000),
        # Spend-weighted, so it reads as "the discount actually achieved on the
        # money spent", not the average of small and large bookings alike.
        "avg_discount_pct": float((df["discount_pct"] * df["spend"]).sum() / df["spend"].sum()),
        "under_count": int(len(under)),
        "under_pct":   float(len(under) / len(df) * 100),
        # Impression shortfall on each flagged placement, priced at that
        # placement's CONTRACTED CPM (spend / contracted-to-date impressions) --
        # the rate the client agreed to pay per thousand -- then summed.
        # Delivered CPM would be circular: it is inflated precisely because
        # delivery fell short. Contracted CPM is algebraically identical to
        # spend x shortfall%, so the figure holds up under either framing.
        "value_at_risk": float(((under["contracted_to_date"] - under["verified_impressions"])
                                * (under["spend"] / under["contracted_to_date"] * 1000) / 1000).sum()),
        "shortfall_impressions": float((under["contracted_to_date"]
                                        - under["verified_impressions"]).sum()),
    }

    # per campaign, with reach built market by market and then aggregated
    camps = []
    for cid, g in df.groupby("campaign_id"):
        # Reach is computed PER MARKET and summed as people, never averaged as
        # percentages. The saturation curve runs against each city's own CMA
        # population using only the impressions delivered in that city, so a
        # national buy cannot saturate one CMA the way it did when every
        # impression was attributed to a single "primary" city.
        #
        # Cross-market duplication is NOT removed: someone who travels between
        # Toronto and Montreal is counted once in each market, so campaign reach
        # is an upper bound. Documented in docs/assumptions.md.
        reached_people   = 0.0
        market_population = 0
        markets = []
        for city, cg in g.groupby("city"):
            pop = m.CITY_POPULATION.get(city, 1_000_000)
            rf_city = m.reach_frequency(float(cg["verified_impressions"].sum()), pop)
            reached_people    += rf_city["reach"]
            market_population += pop
            markets.append(city)
        delivered = float(g["verified_impressions"].sum())
        # Every placement on a campaign shares the campaign's flight window, so
        # the campaign's elapsed and total days are just any row's.
        elapsed = int(g["elapsed_days"].max())
        flight  = int(g["flight_days"].max())
        contracted_to_date = float(g["contracted_to_date"].sum())
        camps.append({
            "campaign_id": int(cid),
            "client": g["client_name"].iloc[0],
            "industry": g["industry"].iloc[0],
            "objective": g["objective"].iloc[0],
            "start": g["campaign_start"].iloc[0], "end": g["campaign_end"].iloc[0],
            "placements": int(len(g)),
            "elapsed_days": elapsed,
            "flight_days": flight,
            "in_flight": bool(g["in_flight"].any()),
            "spend": float(g["spend"].sum()),
            "contracted": contracted_to_date,
            "contracted_full_flight": float(g["contracted_impressions"].sum()),
            "delivered": delivered,
            "variance_pct": float((delivered - contracted_to_date) / contracted_to_date * 100),
            "cpm": float(g["spend"].sum() / delivered * 1000),
            "markets": len(markets),
            "market_list": sorted(markets),
            "reach_pct": round(reached_people / market_population * 100, 1) if market_population else 0.0,
            "frequency": round(delivered / reached_people, 1) if reached_people else 0.0,
            # Daily showing level across the markets the campaign ran in.
            "daily_grp": round(m.daily_grp(delivered, market_population, elapsed), 1),
        })

    def group(col):
        g = df.groupby(col).agg(placements=("placement_id", "count"),
                                spend=("spend", "sum"),
                                delivered=("verified_impressions", "sum"),
                                contracted=("contracted_to_date", "sum"),
                                discount_pct=("discount_pct", "mean")).reset_index()
        g["cpm"] = g["spend"] / g["delivered"] * 1000
        g["variance_pct"] = (g["delivered"] - g["contracted"]) / g["contracted"] * 100
        return g.rename(columns={col: "key"}).to_dict("records")

    # Only placements that actually breach the -5% flag line, in the order the
    # tested ranking function put them in.
    worst = (under.sort_values("variance_pct")
                  [["placement_id", "client_name", "city", "format",
                    "contracted_impressions", "contracted_to_date",
                    "verified_impressions", "in_flight",
                    "elapsed_days", "flight_days",
                    "variance_pct", "spend", "cpm", "downtime_hours"]]
                  .to_dict("records"))

    monthly = pd.read_sql_query("""
        SELECT substr(d.date,1,7) AS month,
               SUM(d.verified_impressions) AS delivered,
               SUM(d.estimated_impressions) AS planned
        FROM delivery d GROUP BY month ORDER BY month
    """, con).to_dict("records")

    payload = {
        "generated_note": "All data synthetic, modelled on the Canadian out-of-home market (CMA populations, Canadian format names, rate cards from published market benchmarks). Figures in CAD. No real agency or client data.",
        "summary": summary,
        "campaigns": camps,
        "by_format": group("format"),
        "by_city": group("city"),
        "by_client": group("client_name"),
        "worst_placements": worst,
        "monthly": monthly,
        "assumptions": {
            "visibility_factors": "Share of passing traffic assumed to see the ad; varies 0.30-0.48 by format.",
            "reach_model": "Computed per market against that CMA's population, then summed as people. reach = population * (1 - (1 - 0.35) ** (impressions / population)). A planning convention, not a measurement. Cross-market duplication is not removed, so national reach is an upper bound.",
            "reach_limitation": "Known limitation: one campaign-market pair still saturates. 1 of 48 models above 90% reach, at 94.0% — Toronto on the heaviest campaign — and nothing exceeds 95%. Tiering traffic and rate by market, and measuring live campaigns to date rather than over their full booked flight, removed the rest. In that one cell average frequency, not reach, is the informative number: the model is saying the campaign hit most reachable people in Toronto about 7 times each. Closing it properly needs more markets rather than a tuned constant.",
            "market_tiers": "Traffic and rate card both scale by market tier - Tier 1 (Toronto, Montreal, Vancouver) 1.0x traffic and upper-half rates; Tier 2 (Calgary, Ottawa, Edmonton) 0.6x traffic and lower-half rates - so CPM stays comparable across markets while volume falls with market size.",
            "under_delivery": "~10% of placements are generated as under-performers, reflecting dark sites, damage and digital downtime.",
            "as_of_basis": f"Everything is measured to {as_of.date().isoformat()}, the last day delivery was reported. A campaign still in the air is compared against its contracted impressions PRORATED to the days elapsed (contracted * elapsed / flight days), not against the full-flight figure — otherwise a healthy placement three weeks into a twelve-week flight would read as -75%. Proration assumes contracted delivery is flat across the flight.",
            "spend_basis": "Spend prorates each placement's 4-week (28-day) negotiated rate to the days that have actually run (rate * elapsed days / 28), so spend and impressions cover the same window.",
            "digital_vs_static_cpm": "A digital face rotates in a shared loop: its impressions are a share of loop time, not the exclusive presence a static bulletin holds for the whole flight. Comparing the two CPMs directly therefore overstates static's efficiency, and the format CPM chart should be read within a format, not across.",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, separators=(",", ":"))

    # Also write data.js. Browsers block fetch() against file:// URLs, so a plain
    # <script> tag is the only way the dashboard opens correctly straight from
    # disk as well as from a web server.
    with open(OUT.replace(".json", ".js"), "w") as f:
        f.write("window.OOH_DATA = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";")
    con.close()

    s = summary
    print(f"as of        {s['as_of']:>10}  ({s['in_flight_campaigns']} campaigns in flight)")
    print(f"placements   {s['placements']:>10,}")
    print(f"spend        {s['spend']:>10,.0f} CAD (to date)")
    print(f"delivered    {s['delivered']:>10,.0f} of {s['contracted']:,.0f} contracted to date")
    print(f"blended CPM  {s['blended_cpm']:>10,.2f} CAD")
    print(f"discount     {s['avg_discount_pct']:>10,.1f} % off rate card")
    print(f"under-deliv. {s['under_count']:>10} placements ({s['under_pct']:.1f}%)")
    print(f"value at risk{s['value_at_risk']:>10,.0f} CAD")
    print(f"\nwrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
