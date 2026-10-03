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


# --- in-flight fault detection ------------------------------------------------
# Everything below reads ONLY the daily delivery series. The generator knows
# which placements it broke and when; this layer is never told. That is the
# point: if the analyzer could read the answer it would prove nothing about
# whether delivery problems are detectable from delivery data.
#
# A placement's DAILY DELIVERY INDEX is what it delivered on a day against what
# it was planned to deliver that day:
#
#     daily index = verified that day / (contracted impressions / flight days)
#
# Healthy daily delivery varies; a fault does not look like variance. The two
# thresholds below sit in the gap between those two populations, and the
# three-day run requirement is what stops a single bad day -- a digital screen
# dark for an afternoon -- being called a fault.

IMPAIRED_INDEX  = 0.90   # a day below 90% of plan is impaired
RECOVERED_INDEX = 0.95   # a day at or above 95% of plan is running normally
RUN_DAYS        = 3      # consecutive days needed to call a fault, or a recovery

# A cumulative read needs enough days behind it to mean anything. On day one the
# "cumulative" variance IS that single day, and one noisy day sits as low as
# 0.92 of plan on perfectly healthy delivery -- below the -5% line. Without this
# guard the alert fires on 45 placements that never developed a fault at all,
# and detection delay comes out NEGATIVE on 15 of them, which is nonsense.
#
# Fourteen days is where that disappears completely on this dataset: false
# alarms 45 -> 0, negative delays 15 -> 0, and the number of real faults caught
# rises from 75 to 90 because the statistic stops being polluted. The cost is
# honest and small -- median detection moves from 3 to 4 days, against 31 days
# to reconciliation. This is the "widen the threshold when few days have
# elapsed" limitation the README has always flagged, made concrete.
MIN_ALERT_DAYS  = 14


def daily_delivery_index(verified, planned_daily):
    """Each day's verified impressions as a share of that day's planned delivery."""
    if planned_daily <= 0:
        return []
    return [v / planned_daily for v in verified]


def _first_run(flags, min_len, start=0):
    """
    Index of the first day that begins `min_len` consecutive True values.

    Returns None if no such run exists. Searching from `start` lets the same
    helper find a recovery after an onset without rewriting the scan.
    """
    run = 0
    for i in range(start, len(flags)):
        run = run + 1 if flags[i] else 0
        if run >= min_len:
            return i - min_len + 1
    return None


def fault_onset_day(index_series, min_len=RUN_DAYS):
    """
    The day a fault began, as a 0-based offset into the flight.

    The first day of the first run of `min_len` consecutive impaired days. None
    if the placement never sustained one, which is the healthy case.
    """
    return _first_run([x < IMPAIRED_INDEX for x in index_series], min_len)


def recovery_day(index_series, onset, min_len=RUN_DAYS):
    """
    The day delivery returned to normal after `onset`, or None if it never did.

    Same run rule in the other direction, so a single good day inside a fault
    is not mistaken for a repair.
    """
    if onset is None:
        return None
    day = _first_run([x >= RECOVERED_INDEX for x in index_series], min_len,
                     start=onset + min_len)
    return day


def alert_crossing_day(verified, planned_daily, threshold_pct=-5.0,
                       min_days=MIN_ALERT_DAYS):
    """
    The day this placement would first have been flagged, measured to date.

    Applies the SAME -5% line delivery_variance_ranked() uses, but day by day
    against cumulative delivery rather than once at the as-of date:

        cumulative verified / (planned_daily x days so far) - 1 < threshold

    ...and only once `min_days` of delivery have actually run. See
    MIN_ALERT_DAYS: a cumulative average over one or two days is a single noisy
    day wearing a disguise, and acting on it produces alerts for placements that
    were never broken.

    This is what makes "caught in flight" a measurable claim rather than an
    assertion -- it is the day the dashboard would have shown the problem.
    """
    if planned_daily <= 0:
        return None
    cumulative = 0.0
    for k, v in enumerate(verified):
        cumulative += v
        if k + 1 < min_days:
            continue
        expected = planned_daily * (k + 1)
        if expected > 0 and (cumulative / expected - 1) * 100 < threshold_pct:
            return k
    return None


def _mean(values):
    return sum(values) / len(values) if values else None


def detection_timeline(verified, planned_daily, flight_days, threshold_pct=-5.0):
    """
    One placement's delivery history, as the Attention Centre needs to tell it.

    All day numbers are 0-based offsets into the flight, so day 0 is the
    placement's start_date and day k is start_date + k days.

    `reconciliation_delay_days` is the comparison the whole project rests on:
    the days between a fault starting and the end of the flight, which is when
    end-of-campaign reconciliation would have found it by hand. Set against
    `detection_delay_days`, it is the time the tool actually buys.
    """
    idx = daily_delivery_index(verified, planned_daily)
    onset = fault_onset_day(idx)
    recovered = recovery_day(idx, onset)
    alert = alert_crossing_day(verified, planned_daily, threshold_pct)

    fault_end = recovered if recovered is not None else len(idx)
    return {
        "observed_onset_day": onset,
        "recovery_day": recovered,
        "recovered": recovered is not None,
        "alert_day": alert,
        # How long the tool took to call it, against how long reconciliation would have.
        "detection_delay_days": None if (alert is None or onset is None) else alert - onset,
        "reconciliation_delay_days": None if onset is None else flight_days - onset,
        # Flight still left to act in on the day it was flagged.
        "days_remaining_at_detection": None if alert is None else flight_days - (alert + 1),
        "pre_fault_index": None if not onset else _mean(idx[:onset]),
        "fault_index": None if onset is None else _mean(idx[onset:fault_end]),
    }


# --- shortfall, pacing and exposure -------------------------------------------

def shortfall_decomposition(df):
    """
    Gross shortfall, the over-delivery that hides it, and what is left net.

    A campaign-level variance nets the two against each other, so a campaign
    reading -1% can be carrying a million impressions of real shortfall on some
    placements while others run hot. Over-delivery on one site does not repair a
    dark site on another -- the advertiser still did not get what they bought in
    the place they bought it -- so the gross figure is the operational one and
    the net figure is the accounting one. Both are reported; neither is hidden.

        gross  = sum of shortfalls on placements that are behind
        offset = sum of over-delivery on placements that are ahead
        net    = gross - offset
        masking = offset / gross

    Takes a frame of placements, returns one dict for the whole frame.
    """
    behind = (df["contracted_to_date"] - df["verified_impressions"]).clip(lower=0)
    ahead  = (df["verified_impressions"] - df["contracted_to_date"]).clip(lower=0)
    gross, offset = float(behind.sum()), float(ahead.sum())
    contracted = float(df["contracted_to_date"].sum())
    return {
        "gross_shortfall": gross,
        "over_delivery_offset": offset,
        "net_shortfall": gross - offset,
        "masking_pct": (offset / gross * 100) if gross > 0 else 0.0,
        "placements_behind": int((behind > 0).sum()),
        "variance_pct": ((float(df["verified_impressions"].sum()) - contracted)
                         / contracted * 100) if contracted > 0 else 0.0,
    }


def pacing(df, as_of=None):
    """
    What each placement would now have to do to finish its contract whole.

        planned daily  = contracted impressions / flight days
        required daily = (contracted - verified) / days remaining
        recovery pace  = required daily / planned daily

    A recovery pace of 1.26 means "126% of the daily delivery this placement was
    planned for, every remaining day". That is a statement of what recovery would
    TAKE, not a forecast that it will happen -- and usually it is a number the
    booked face cannot reach, because a healthy face in this model delivers
    0.96-1.05 of plan and has no mechanism to run 26% hot. Above about 1.05 the
    gap closes with added weight or a make-good, not by catching up. The
    interface has to say so rather than implying recovery is available.

    A placement whose flight has closed has no days remaining; its required
    daily and recovery pace are left missing rather than infinite.
    """
    prog = flight_progress(df, as_of)
    out = pd.DataFrame(index=df.index)
    out["placement_id"]  = df["placement_id"]
    out["flight_days"]   = prog["flight_days"]
    out["elapsed_days"]  = prog["elapsed_days"]
    out["remaining_days"] = prog["flight_days"] - prog["elapsed_days"]
    out["planned_daily"] = df["contracted_impressions"] / prog["flight_days"]

    to_date = df["contracted_impressions"] * prog["elapsed_days"] / prog["flight_days"]
    out["delivery_index"] = df["verified_impressions"] / to_date.where(to_date > 0)
    out["remaining_contracted"] = (df["contracted_impressions"]
                                   - df["verified_impressions"]).clip(lower=0)
    remaining = out["remaining_days"].where(out["remaining_days"] > 0)
    out["required_daily"] = out["remaining_contracted"] / remaining
    out["recovery_pace"]  = out["required_daily"] / out["planned_daily"]
    return out


def exposure(df, as_of=None, current_index=None):
    """
    What the shortfall is worth, and how much of it is still preventable.

    `current_index` is the rate the placement is running at NOW, as a share of
    planned daily delivery. It matters because a fault starts on a day: a
    placement that ran healthy for three weeks and has been dark for four days
    has a cumulative delivery index close to 1.0, which says almost nothing
    about how fast it is losing impressions today. Passing the fault-period rate
    instead prices the rest of the flight on what the placement is actually
    doing. Left out, the cumulative index is used, which is right only for a
    placement that has been behind from the start.

    Two different quantities, which must never be added together:

      billed shortfall  - impressions already missed, priced at the placement's
                          CONTRACTED CPM (spend / contracted to date). That is
                          the rate the client agreed to pay per thousand.
                          Delivered CPM would be circular: it is inflated
                          precisely because delivery fell short.

      preventable       - what accrues over the REST of the flight if nothing is
                          fixed. Live placements only; a closed flight has
                          nothing left to prevent.

    ASSUMPTION: preventable exposure assumes today's shortfall rate continues
    for the remaining days. That is a statement about the future, so it is
    modelled, not calculated, and is labelled as such wherever it appears.

    Requires a `spend` column (from spend_to_date).
    """
    prog = flight_progress(df, as_of)
    pace = pacing(df, as_of)
    to_date = df["contracted_impressions"] * prog["elapsed_days"] / prog["flight_days"]

    out = pd.DataFrame(index=df.index)
    out["placement_id"] = df["placement_id"]
    out["shortfall"] = (to_date - df["verified_impressions"]).clip(lower=0)
    # Contracted CPM: what a thousand contracted impressions was billed at.
    out["contracted_cpm"] = df["spend"] / to_date.where(to_date > 0) * 1000
    out["billed_shortfall"] = out["shortfall"] * out["contracted_cpm"] / 1000
    # Impressions lost per further day at the current rate of under-delivery.
    rate = pace["delivery_index"] if current_index is None else pd.Series(
        current_index, index=df.index).fillna(pace["delivery_index"])
    out["current_index"] = rate
    out["daily_bleed"] = (pace["planned_daily"] * (1 - rate)).clip(lower=0)
    preventable = (out["daily_bleed"] * pace["remaining_days"]
                   * out["contracted_cpm"] / 1000)
    out["preventable_exposure"] = preventable.where(prog["in_flight"], 0.0)
    return out
