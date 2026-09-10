"""
Metric calculations for the OOH Campaign Performance Analyzer.

Each function does one thing. The per-placement metrics take a pandas DataFrame
and return a DataFrame; the two audience estimators (reach_frequency, daily_grp)
take plain numbers, because they are applied one market at a time. Where a
metric rests on an assumption, the assumption is stated in a comment here and in
docs/assumptions.md.
"""
import pandas as pd

# Population estimates used as the denominator for reach and GRP.
# Canadian census metropolitan area (CMA) populations, rounded to the nearest
# 100k. Any reach figure built on these is an ESTIMATE.
CITY_POPULATION = {
    "Toronto": 6_400_000,
    "Montreal": 4_300_000,
    "Vancouver": 2_700_000,
    "Calgary": 1_600_000,
    "Ottawa": 1_500_000,
    "Edmonton": 1_500_000,
}

# A rate card is quoted per four-week period. Four weeks is 28 days, not 30.
RATE_PERIOD_DAYS = 28


def as_of_date(df, as_of=None):
    """
    The date every "to date" figure is measured at.

    Given explicitly, that date wins. Otherwise it is the latest delivery date
    present in the data (the last day anything was reported), falling back to
    the latest flight end date if delivery dates were not loaded.
    """
    if as_of is not None:
        return pd.Timestamp(as_of)
    if "last_delivery_date" in df.columns:
        return pd.to_datetime(df["last_delivery_date"]).max()
    return pd.to_datetime(df["end_date"]).max()


def flight_progress(df, as_of=None):
    """
    How far into its flight each placement is, as of a date.

    Delivery is recorded one row per day from start_date up to but not
    including end_date, so a flight is (end - start) days long and by the close
    of as_of, (as_of - start) + 1 of those days have run. Capped at the full
    flight so a finished placement reads as 100% elapsed, and floored at zero
    so one that has not started yet reads as 0.
    """
    ref = as_of_date(df, as_of)
    start = pd.to_datetime(df["start_date"])
    end   = pd.to_datetime(df["end_date"])

    out = pd.DataFrame(index=df.index)
    out["flight_days"]  = (end - start).dt.days.clip(lower=1)
    out["elapsed_days"] = (((ref - start).dt.days + 1)
                           .clip(lower=0)
                           .clip(upper=out["flight_days"]))
    out["in_flight"] = out["elapsed_days"] < out["flight_days"]
    return out


def delivery_vs_contract(df, as_of=None):
    """
    Delivered against contracted impressions TO DATE, per placement.

    The contracted figure covers the whole flight, so comparing a live
    placement against it is meaningless: three weeks into a twelve-week flight
    a perfectly healthy site reads as -75%. Contracted impressions are
    therefore prorated to the days elapsed at as_of:

        contracted_to_date = contracted_impressions x elapsed_days / flight_days

    which is capped at the full contracted amount, so a completed flight is
    measured against the whole thing exactly as before.

    ASSUMPTION: contracted delivery is flat across the flight. Contracted
    impressions are generated as daily_traffic x visibility x days, so straight
    line proration is the same model read backwards. A real booking with
    weekday/weekend or seasonal weighting would need a delivery curve here.

    variance_pct < 0 means the placement is behind what the advertiser paid for
    at this point in the flight.
    """
    out = df.copy()
    prog = flight_progress(df, as_of)
    out["as_of"]        = as_of_date(df, as_of).date().isoformat()
    out["flight_days"]  = prog["flight_days"]
    out["elapsed_days"] = prog["elapsed_days"]
    out["in_flight"]    = prog["in_flight"]

    to_date = out["contracted_impressions"] * prog["elapsed_days"] / prog["flight_days"]
    # A placement that has not started yet is contracted for nothing so far.
    # Leave its variance missing rather than dividing by zero; missing never
    # trips the flag line.
    out["contracted_to_date"] = to_date
    out["variance_abs"] = out["verified_impressions"] - to_date
    out["variance_pct"] = out["variance_abs"] / to_date.where(to_date > 0) * 100
    return out[["placement_id", "campaign_id", "site_id", "city", "format",
                "as_of", "flight_days", "elapsed_days", "in_flight",
                "contracted_impressions", "contracted_to_date",
                "verified_impressions", "variance_abs", "variance_pct"]]


def spend_to_date(df, as_of=None):
    """
    Media spend billed so far, per placement.

    negotiated_rate is a four-week figure. A placement runs a 4-12 week flight,
    so the rate is prorated to the days that have actually run:

        spend = negotiated_rate x elapsed_days / 28

    Spend and impressions then share a time base. Without it CPM is understated
    by up to 3x on long completed bookings, and overstated on anything still in
    the air.
    """
    out = df.copy()
    prog = flight_progress(df, as_of)
    out["elapsed_days"] = prog["elapsed_days"]
    out["spend"] = out["negotiated_rate"] * prog["elapsed_days"] / RATE_PERIOD_DAYS
    return out[["placement_id", "negotiated_rate", "elapsed_days", "spend"]]


def cpm(df):
    """
    Cost per thousand impressions.

    Uses VERIFIED impressions, not contracted — the advertiser's real cost per
    thousand is what was actually delivered, not what was promised.
    """
    out = df.copy()
    # verified_impressions can be 0 for a placement that never ran. Swap the 0
    # for NA so CPM comes out missing rather than infinite, and stays out of any
    # average taken over the column.
    out["cpm"] = (out["spend"] / out["verified_impressions"].replace(0, pd.NA)) * 1000
    return out[["placement_id", "campaign_id", "format", "spend",
                "verified_impressions", "cpm"]]


def rate_efficiency(df):
    """How far below rate card the negotiated rate landed."""
    out = df.copy()
    # Both figures are four-week period rates (list price vs what was agreed),
    # so this discount is a like-for-like comparison and does not depend on how
    # long the placement then ran for, or how far into the flight it is.
    out["discount_pct"] = (1 - out["negotiated_rate"] / out["rate_card_monthly"]) * 100
    return out[["placement_id", "campaign_id", "site_id",
                "rate_card_monthly", "negotiated_rate", "discount_pct"]]


def daily_grp(impressions, population, days):
    """
    Daily gross rating points — the OOH "showing level".

    In out-of-home a GRP is always a DAILY rate. A "#50 showing" is inventory
    delivering daily impressions equal to 50% of the market population; it is
    how buyers size a market-level weight of advertising. Quoting the flight
    total instead just restates total impressions in a different unit and makes
    a twelve-week buy look three times heavier than a four-week one at the same
    weight, which is the opposite of what the number is for.

        daily GRP = (impressions / days) / population x 100

    Verified, not contracted, impressions — same choice as cpm(): rate the
    campaign on what actually ran. Across markets this is summed as impressions
    over combined population, which is the population-weighted average of the
    per-market showing levels; averaging the percentages directly would
    over-weight small markets.
    """
    if population <= 0 or days <= 0:
        return 0.0
    return (impressions / days) / population * 100


def reach_frequency(impressions, population, exposure_prob=0.35):
    """
    Estimate unique reach and average frequency from gross impressions.

    ASSUMPTION. Gross impressions count exposures, not people. We model reach
    with a standard saturation curve:

        reach = population * (1 - (1 - p) ** opportunities_per_person)

    where p is the per-opportunity probability that an exposure lands with a
    distinct person. p = 0.35 is a planning convention, not a measured value.
    Frequency then falls out as gross impressions / reach.

    Treat both outputs as estimates. That is true of all OOH reach figures.
    """
    if population <= 0 or impressions <= 0:
        return {"reach": 0.0, "reach_pct": 0.0, "frequency": 0.0}
    opportunities = impressions / population
    reach = population * (1 - (1 - exposure_prob) ** opportunities)
    return {
        "reach": reach,
        "reach_pct": (reach / population) * 100,
        "frequency": impressions / reach if reach else 0.0,
    }


def delivery_variance_ranked(df, threshold_pct=-5.0, as_of=None):
    """
    Under-performing placements, worst first, measured to date.

    This is the flagship output. Agencies normally catch under-delivery by hand
    at end of campaign, during reconciliation. Because the comparison is against
    contracted-to-date rather than the full flight, a placement still in the air
    is judged on the days that have actually run — which is what makes ranking
    it mid-flight, rather than after the money is spent, mean anything.

    threshold_pct is -5% because normal daily delivery noise sits inside +/-5%;
    below that the gap is large enough to be worth a reconciliation conversation.
    It is a hard cliff: -5.1% flags and -4.9% does not.
    """
    v = delivery_vs_contract(df, as_of)
    return v[v["variance_pct"] < threshold_pct].sort_values("variance_pct")
