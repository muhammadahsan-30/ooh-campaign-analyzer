"""
BI export layer: star-schema CSVs for the Power BI companion.

Additive. This script reads the same SQLite database and calls the same
src/metrics.py functions the web dashboard uses, so the BI model and the
product are fed by one pipeline and one set of definitions. It changes nothing
in the analytical source of truth.

Division of labour, deliberately:

  * SEQUENTIAL / EVENT logic stays in Python. Fault onset, alert crossing,
    recovery, detection delay and days-remaining-at-detection are run-based
    over an ordered series -- natural here, painful and opaque in DAX. They are
    computed once and exported as facts.
  * ADDITIVE / RATIO measures are NOT precomputed into aggregates. The grain is
    exported and DAX does the aggregating, which is the part worth
    demonstrating.

What is deliberately NOT exported: the generator's fault plan. generate_data.py
knows which placements it broke and when; that plan is evaluation-only and is
never written to the database, never exported here, and never reaches the BI
model. Everything in fact_detection_events is inferred from the visible daily
delivery series by metrics.detection_timeline().

Run:  python src/export_bi.py
"""
import os, sqlite3, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get("OOH_DB", os.path.join(ROOT, "data", "ooh.db"))
OUT  = os.path.join(ROOT, "bi")

# Keep in step with export_json.py -- the Attention Centre's materiality cut.
MATERIAL_EXPOSURE = 1_000.0


def load(con):
    """One row per placement with campaign and site attributes joined on."""
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


def enrich(df, daily, as_of):
    """Every per-placement metric, from the tested functions in metrics.py."""
    var   = m.delivery_vs_contract(df, as_of)
    money = m.spend_to_date(df, as_of)
    df = df.merge(var[["placement_id", "flight_days", "elapsed_days", "in_flight",
                       "contracted_to_date", "variance_pct"]], on="placement_id")
    df = df.merge(money[["placement_id", "spend"]], on="placement_id")

    mismatch = df[df["elapsed_days"] != df["delivery_days"]]
    if len(mismatch):
        raise SystemExit("elapsed_days disagrees with delivery rows on "
                         f"{len(mismatch)} placements")

    pace = m.pacing(df, as_of)
    df = df.merge(pace[["placement_id", "remaining_days", "planned_daily",
                        "delivery_index", "required_daily", "recovery_pace"]],
                  on="placement_id")

    # Detection, from the delivery series alone.
    series = daily.groupby("placement_id")["verified_impressions"].apply(list)
    rows = []
    for r in df.itertuples():
        t = m.detection_timeline(series.get(r.placement_id, []),
                                 r.planned_daily, r.flight_days)
        t["placement_id"] = r.placement_id
        rows.append(t)
    df = df.merge(pd.DataFrame(rows), on="placement_id")

    broken = df["observed_onset_day"].notna() & ~df["recovered"]
    df["current_index"] = df["delivery_index"].where(~broken, df["fault_index"])
    expo = m.exposure(df, as_of, current_index=df["current_index"])
    df = df.merge(expo[["placement_id", "shortfall", "contracted_cpm",
                        "billed_shortfall", "preventable_exposure"]],
                  on="placement_id")

    flagged = set(m.delivery_variance_ranked(df, as_of=as_of)["placement_id"])
    df["is_flagged"] = df["placement_id"].isin(flagged)
    df["status"] = "on_track"
    df.loc[df["is_flagged"] & df["in_flight"], "status"] = "live_issue"
    df.loc[df["is_flagged"] & ~df["in_flight"], "status"] = "completed_shortfall"
    df["is_material"] = df["preventable_exposure"] >= MATERIAL_EXPOSURE
    # Both sides of the netting, at placement grain, so DAX can sum either one
    # without needing a conditional it cannot explain.
    df["over_delivery"] = (df["verified_impressions"] - df["contracted_to_date"]).clip(lower=0)
    return df


def write(name, frame):
    path = os.path.join(OUT, name)
    frame.to_csv(path, index=False)
    print(f"  {name:28s} {len(frame):>7,} rows  {len(frame.columns):>2} cols")
    return len(frame)


def main():
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
    daily = pd.read_sql_query(
        "SELECT placement_id, date, verified_impressions, estimated_impressions, "
        "downtime_hours FROM delivery ORDER BY placement_id, date", con)
    df = load(con)
    as_of = m.as_of_date(df)
    df = enrich(df, daily, as_of)
    print(f"as of {as_of.date().isoformat()}\n")

    counts = {}

    # ---- dimensions ---------------------------------------------------------
    camp = pd.read_sql_query("""
        SELECT campaign_id, campaign_name, client_name, industry, objective,
               start_date AS campaign_start, end_date AS campaign_end, budget
        FROM campaigns ORDER BY campaign_id""", con)
    camp["flight_days"] = ((pd.to_datetime(camp["campaign_end"])
                            - pd.to_datetime(camp["campaign_start"])).dt.days)
    camp["is_in_flight"] = pd.to_datetime(camp["campaign_end"]) > as_of
    counts["dim_campaign"] = write("dim_campaign.csv", camp)

    site = pd.read_sql_query("""
        SELECT site_id, city, area, format, is_digital, daily_traffic,
               rate_card_monthly
        FROM sites ORDER BY site_id""", con)
    site["format_label"] = site["format"].str.replace("_", " ").str.capitalize()
    site["media_type"] = site["is_digital"].map({1: "Digital", 0: "Static"})
    counts["dim_site"] = write("dim_site.csv", site)

    # A continuous calendar across the delivery window, so time intelligence
    # behaves and gaps between flights do not break the axis.
    lo = pd.to_datetime(daily["date"]).min()
    hi = pd.to_datetime(daily["date"]).max()
    cal = pd.DataFrame({"date": pd.date_range(lo, hi, freq="D")})
    cal["date_key"]   = cal["date"].dt.strftime("%Y-%m-%d")
    cal["year"]       = cal["date"].dt.year
    cal["month_num"]  = cal["date"].dt.month
    cal["month_name"] = cal["date"].dt.strftime("%b")
    cal["year_month"] = cal["date"].dt.strftime("%Y-%m")
    cal["quarter"]    = "Q" + cal["date"].dt.quarter.astype(str)
    cal["day_of_week"]  = cal["date"].dt.dayofweek + 1
    cal["day_name"]     = cal["date"].dt.strftime("%a")
    cal["is_weekend"]   = cal["date"].dt.dayofweek >= 5
    cal = cal.drop(columns=["date"]).rename(columns={"date_key": "date"})
    counts["dim_date"] = write("dim_date.csv", cal)

    # ---- facts --------------------------------------------------------------
    placement = df[[
        "placement_id", "campaign_id", "site_id",
        "start_date", "end_date",
        "flight_days", "elapsed_days", "remaining_days", "in_flight",
        "contracted_impressions", "contracted_to_date", "verified_impressions",
        "shortfall", "over_delivery",
        "negotiated_rate", "spend", "contracted_cpm",
        "billed_shortfall", "preventable_exposure",
        "variance_pct", "delivery_index", "current_index",
        "planned_daily", "required_daily", "recovery_pace",
        "status", "is_flagged", "is_material",
        "downtime_hours",
    ]].copy().rename(columns={
        "verified_impressions": "verified_to_date",
        "spend": "spend_to_date",
    })
    counts["fact_placement"] = write("fact_placement.csv", placement)

    delivery = daily.rename(columns={"date": "date"})[
        ["placement_id", "date", "verified_impressions",
         "estimated_impressions", "downtime_hours"]]
    counts["fact_delivery"] = write("fact_delivery.csv", delivery)

    # Detection events: one row per placement where a fault was DETECTED from
    # the delivery series. Placements with no detected fault are absent, which
    # keeps the grain honest -- the table is "events", not "placements".
    ev = df[df["observed_onset_day"].notna()].copy()
    start = pd.to_datetime(ev["start_date"])
    ev["onset_date"]    = (start + pd.to_timedelta(ev["observed_onset_day"], "D")).dt.strftime("%Y-%m-%d")
    ev["alert_date"]    = (start + pd.to_timedelta(ev["alert_day"], "D")).dt.strftime("%Y-%m-%d")
    ev["recovery_date"] = (start + pd.to_timedelta(ev["recovery_day"], "D")).dt.strftime("%Y-%m-%d")
    events = ev[[
        "placement_id",
        "observed_onset_day", "onset_date",
        "alert_day", "alert_date",
        "recovery_day", "recovery_date", "recovered",
        "detection_delay_days", "reconciliation_delay_days",
        "days_remaining_at_detection",
        "pre_fault_index", "fault_index",
    ]].rename(columns={"observed_onset_day": "onset_day"})
    counts["fact_detection_events"] = write("fact_detection_events.csv", events)

    con.close()
    return counts, df, as_of


if __name__ == "__main__":
    main()
