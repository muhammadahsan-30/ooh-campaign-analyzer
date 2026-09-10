"""
Metric calculations for the OOH Campaign Performance Analyzer.

Every function takes a pandas DataFrame and returns a DataFrame. Each one does
one thing. Where a metric rests on an assumption, the assumption is stated in a
comment here and in docs/assumptions.md.
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


def delivery_vs_contract(df):
    """
    Delivered against contracted impressions, per placement.

    variance_pct < 0 means the placement under-delivered against what the
    advertiser paid for.
    """
    out = df.copy()
    out["variance_abs"] = out["verified_impressions"] - out["contracted_impressions"]
    out["variance_pct"] = (out["variance_abs"] / out["contracted_impressions"]) * 100
    return out[["placement_id", "campaign_id", "site_id", "city", "format",
                "contracted_impressions", "verified_impressions",
                "variance_abs", "variance_pct"]]


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
    # Both figures are monthly (list price vs what was agreed), so this discount
    # is a like-for-like comparison and does not depend on how long the placement
    # then ran for.
    out["discount_pct"] = (1 - out["negotiated_rate"] / out["rate_card_monthly"]) * 100
    return out[["placement_id", "campaign_id", "site_id",
                "rate_card_monthly", "negotiated_rate", "discount_pct"]]


def grp(df, population):
    """
    Gross rating points: impressions as a percentage of the target population.
    100 GRP means impressions equal to the whole population — not 100% of
    people reached, since one person can be counted many times.
    """
    out = df.copy()
    # Verified, not contracted, impressions — same choice as cpm(): rate the
    # campaign on what actually ran.
    out["grp"] = (out["verified_impressions"] / population) * 100
    return out


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


def delivery_variance_ranked(df, threshold_pct=-5.0):
    """
    Under-performing placements, worst first.

    This is the flagship output. Agencies normally catch under-delivery by hand
    at end of campaign, during reconciliation. Ranking it continuously is the
    reason this tool exists.

    threshold_pct is -5% because normal daily delivery noise sits inside +/-5%;
    below that the gap is large enough to be worth a reconciliation conversation.
    """
    v = delivery_vs_contract(df)
    return v[v["variance_pct"] < threshold_pct].sort_values("variance_pct")
