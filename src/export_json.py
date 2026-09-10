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
    """One row per placement, with campaign and site attributes joined on."""
    return pd.read_sql_query("""
        SELECT p.placement_id, p.campaign_id, p.site_id,
               p.negotiated_rate,
               -- negotiated_rate is a 4-week (period) rate, but a placement runs
               -- the whole 4-12 week flight and contracted_impressions is counted
               -- over that whole flight. Prorate the rate to the flight length so
               -- spend and impressions share a time base and CPM is not
               -- understated by up to 3x on the longer bookings.
               p.negotiated_rate * (julianday(p.end_date) - julianday(p.start_date)) / 30.0
                   AS spend,
               p.contracted_impressions,
               c.client_name, c.industry, c.objective, c.start_date, c.end_date,
               s.city, s.area, s.format, s.rate_card_monthly,
               SUM(d.verified_impressions)  AS verified_impressions,
               SUM(d.estimated_impressions) AS estimated_impressions,
               SUM(d.downtime_hours)        AS downtime_hours
        FROM placements p
        JOIN campaigns c ON c.campaign_id = p.campaign_id
        JOIN sites     s ON s.site_id     = p.site_id
        JOIN delivery  d ON d.placement_id = p.placement_id
        GROUP BY p.placement_id
    """, con)


def main():
    con = sqlite3.connect(DB)
    df = load(con)

    var  = m.delivery_vs_contract(df)
    cost = m.cpm(df)
    rate = m.rate_efficiency(df)
    df = df.merge(var[["placement_id", "variance_abs", "variance_pct"]], on="placement_id")
    df = df.merge(cost[["placement_id", "cpm"]], on="placement_id")
    df = df.merge(rate[["placement_id", "discount_pct"]], on="placement_id")

    under = df[df["variance_pct"] < -5]

    summary = {
        "sites":       int(pd.read_sql_query("SELECT COUNT(*) n FROM sites", con)["n"][0]),
        "campaigns":   int(df["campaign_id"].nunique()),
        "clients":     int(df["client_name"].nunique()),
        "placements":  int(len(df)),
        "delivery_rows": int(pd.read_sql_query("SELECT COUNT(*) n FROM delivery", con)["n"][0]),
        "spend":       float(df["spend"].sum()),
        "delivered":   float(df["verified_impressions"].sum()),
        "contracted":  float(df["contracted_impressions"].sum()),
        "blended_cpm": float(df["spend"].sum() / df["verified_impressions"].sum() * 1000),
        "under_count": int(len(under)),
        "under_pct":   float(len(under) / len(df) * 100),
        # Impression shortfall on each flagged placement, priced at that
        # placement's CONTRACTED CPM (spend / contracted impressions) -- the rate
        # the client agreed to pay per thousand -- then summed. Delivered CPM
        # would be circular: it is inflated precisely because delivery fell
        # short. Contracted CPM is algebraically identical to spend x shortfall%,
        # so the figure holds up under either framing.
        "value_at_risk": float(((under["contracted_impressions"] - under["verified_impressions"])
                                * (under["spend"] / under["contracted_impressions"] * 1000) / 1000).sum()),
        "shortfall_impressions": float((under["contracted_impressions"]
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
        camps.append({
            "campaign_id": int(cid),
            "client": g["client_name"].iloc[0],
            "industry": g["industry"].iloc[0],
            "objective": g["objective"].iloc[0],
            "start": g["start_date"].iloc[0], "end": g["end_date"].iloc[0],
            "placements": int(len(g)),
            "spend": float(g["spend"].sum()),
            "contracted": float(g["contracted_impressions"].sum()),
            "delivered": float(g["verified_impressions"].sum()),
            "variance_pct": float((g["verified_impressions"].sum() - g["contracted_impressions"].sum())
                                  / g["contracted_impressions"].sum() * 100),
            "cpm": float(g["spend"].sum() / g["verified_impressions"].sum() * 1000),
            "markets": len(markets),
            "market_list": sorted(markets),
            "reach_pct": round(reached_people / market_population * 100, 1) if market_population else 0.0,
            "frequency": round(delivered / reached_people, 1) if reached_people else 0.0,
        })

    def group(col):
        g = df.groupby(col).agg(placements=("placement_id", "count"),
                                spend=("spend", "sum"),
                                delivered=("verified_impressions", "sum"),
                                contracted=("contracted_impressions", "sum")).reset_index()
        g["cpm"] = g["spend"] / g["delivered"] * 1000
        g["variance_pct"] = (g["delivered"] - g["contracted"]) / g["contracted"] * 100
        return g.rename(columns={col: "key"}).to_dict("records")

    # Only placements that actually breach the -5% flag line. Previously this took
    # the 25 worst rows regardless of threshold, which put placements that met
    # contract into a table titled "under-delivering".
    worst = (under.sort_values("variance_pct")
                  [["placement_id", "client_name", "city", "format",
                    "contracted_impressions", "verified_impressions",
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
            "reach_limitation": "Known limitation: on the three heaviest campaigns the modelled reach still saturates in the largest markets (6 of 48 campaign-market pairs exceed 90%, worst 94.1%). In those cells average frequency, not reach, is the informative number. Closing it properly needs more markets rather than a tuned constant.",
            "market_tiers": "Traffic and rate card both scale by market tier - Tier 1 (Toronto, Montreal, Vancouver) 1.0x traffic and upper-half rates; Tier 2 (Calgary, Ottawa, Edmonton) 0.6x traffic and lower-half rates - so CPM stays comparable across markets while volume falls with market size.",
            "under_delivery": "~10% of placements are generated as under-performers, reflecting dark sites, damage and digital downtime.",
            "spend_basis": "Spend prorates each placement's 4-week negotiated rate to its full flight length (rate * days / 30), so spend and impressions share a time base.",
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
    print(f"placements   {s['placements']:>10,}")
    print(f"spend        {s['spend']:>10,.0f} CAD")
    print(f"delivered    {s['delivered']:>10,.0f} impressions")
    print(f"blended CPM  {s['blended_cpm']:>10,.1f} CAD")
    print(f"under-deliv. {s['under_count']:>10} placements ({s['under_pct']:.1f}%)")
    print(f"value at risk{s['value_at_risk']:>10,.0f} CAD")
    print(f"\nwrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
