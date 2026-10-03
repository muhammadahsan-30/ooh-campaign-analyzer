"""
Tests use small hand-built inputs so the arithmetic can be checked by eye.
Run with: pytest -q
"""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import metrics as m


def placement(pid=1, contracted=1000, verified=900,
              start="2026-01-01", end="2026-01-11"):
    """A one-placement frame. Default flight is 10 days, 1 Jan to 11 Jan."""
    return {"placement_id": pid, "campaign_id": 1, "site_id": pid, "city": "Toronto",
            "format": "bulletin", "start_date": start, "end_date": end,
            "contracted_impressions": contracted, "verified_impressions": verified}


def test_delivery_vs_contract_computes_shortfall():
    # as_of is the last day of the flight, so the whole 1000 is contracted by now.
    df = pd.DataFrame([placement(contracted=1000, verified=900)])
    out = m.delivery_vs_contract(df, as_of="2026-01-11").iloc[0]
    assert out["contracted_to_date"] == 1000
    assert out["variance_abs"] == -100          # 900 - 1000
    assert out["variance_pct"] == -10.0         # -100 / 1000 * 100
    assert out["in_flight"] == False


def test_cpm_is_spend_per_thousand():
    df = pd.DataFrame([{"placement_id": 1, "campaign_id": 1, "format": "bulletin",
                        "spend": 50_000, "verified_impressions": 100_000}])
    # 50,000 / 100,000 * 1000 = 500
    assert m.cpm(df).iloc[0]["cpm"] == 500.0


def test_rate_efficiency_reads_as_discount():
    df = pd.DataFrame([{"placement_id": 1, "campaign_id": 1, "site_id": 1,
                        "rate_card_monthly": 1_000_000, "negotiated_rate": 750_000}])
    assert m.rate_efficiency(df).iloc[0]["discount_pct"] == 25.0


def test_daily_grp_is_a_daily_showing_level():
    # 10m impressions over 20 days is 500k a day against a 1m population:
    # a #50 showing. The FLIGHT total (1000 GRPs) is a different number and
    # is not what a showing level means.
    assert m.daily_grp(10_000_000, 1_000_000, 20) == 50.0


def test_daily_grp_does_not_reward_a_longer_flight():
    # Same weight per day, twice the flight: the showing level is unchanged.
    assert m.daily_grp(10_000_000, 1_000_000, 20) == m.daily_grp(20_000_000, 1_000_000, 40)


def test_daily_grp_is_zero_when_nothing_has_run():
    assert m.daily_grp(1_000_000, 1_000_000, 0) == 0.0


def test_reach_never_exceeds_population_and_frequency_at_least_one():
    r = m.reach_frequency(impressions=25_000_000, population=6_400_000)
    assert 0 < r["reach"] <= 6_400_000
    assert r["reach_pct"] <= 100
    assert r["frequency"] >= 1.0


def test_reach_frequency_exact_saturation_curve():
    # p = 0.5, and impressions == population so opportunities-per-person = 1.
    # reach = 1000 * (1 - (1 - 0.5) ** 1) = 1000 * 0.5 = 500
    r = m.reach_frequency(impressions=1000, population=1000, exposure_prob=0.5)
    assert r["reach"] == 500.0
    assert r["reach_pct"] == 50.0
    assert r["frequency"] == 2.0          # 1000 impressions / 500 people


def test_reach_frequency_zero_impressions_is_all_zero():
    r = m.reach_frequency(impressions=0, population=1000)
    assert r == {"reach": 0.0, "reach_pct": 0.0, "frequency": 0.0}


def test_cpm_is_missing_when_nothing_was_delivered():
    df = pd.DataFrame([{"placement_id": 1, "campaign_id": 1, "format": "bulletin",
                        "spend": 50_000, "verified_impressions": 0}])
    # 50,000 / 0 would be infinite; the metric returns NA instead.
    assert pd.isna(m.cpm(df).iloc[0]["cpm"])


def test_variance_ranking_returns_worst_first():
    df = pd.DataFrame([placement(1, verified=990),
                       placement(2, verified=600),
                       placement(3, verified=800)])
    out = m.delivery_variance_ranked(df, as_of="2026-01-11")
    assert list(out["placement_id"]) == [2, 3]   # -40% then -20%; -1% is above threshold


def test_variance_ranking_threshold_is_adjustable():
    df = pd.DataFrame([placement(1, verified=990),
                       placement(2, verified=600),
                       placement(3, verified=800)])
    # At a -30% line only placement 2 (-40%) is bad enough to show.
    out = m.delivery_variance_ranked(df, threshold_pct=-30, as_of="2026-01-11")
    assert list(out["placement_id"]) == [2]


# --- mid-flight: the reason contracted impressions are prorated ---------------

# A twelve-week flight: 5 Jan to 30 Mar is 84 days, contracted 840,000
# impressions, so 10,000 a day. Three weeks in, 21 days have run.
TWELVE_WEEK = {"start": "2026-01-05", "end": "2026-03-30", "contracted": 840_000}
THREE_WEEKS_IN = "2026-01-25"        # 21st day of the flight, inclusive


def test_healthy_placement_three_weeks_into_twelve_does_not_flag():
    # 208,000 delivered against 210,000 contracted to date: -1.0%, healthy.
    # Against the FULL 840,000 it would read as -75.2% and flag, which is the
    # bug this proration exists to fix.
    df = pd.DataFrame([placement(verified=208_000,
                                 contracted=TWELVE_WEEK["contracted"],
                                 start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"])])
    row = m.delivery_vs_contract(df, as_of=THREE_WEEKS_IN).iloc[0]
    assert row["elapsed_days"] == 21
    assert row["flight_days"] == 84
    assert row["contracted_to_date"] == 210_000
    assert round(row["variance_pct"], 1) == -1.0
    assert row["in_flight"] == True
    assert m.delivery_variance_ranked(df, as_of=THREE_WEEKS_IN).empty


def test_genuinely_bad_placement_still_flags_mid_flight():
    # 150,000 against 210,000 contracted to date is -28.6%: a real problem,
    # caught three weeks in rather than nine weeks later.
    df = pd.DataFrame([placement(verified=150_000,
                                 contracted=TWELVE_WEEK["contracted"],
                                 start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"])])
    out = m.delivery_variance_ranked(df, as_of=THREE_WEEKS_IN)
    assert list(out["placement_id"]) == [1]
    assert round(out.iloc[0]["variance_pct"], 1) == -28.6


def test_as_of_after_the_flight_measures_against_the_whole_contract():
    # Proration caps at 100%: a finished flight is judged on the full figure.
    df = pd.DataFrame([placement(verified=800_000,
                                 contracted=TWELVE_WEEK["contracted"],
                                 start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"])])
    row = m.delivery_vs_contract(df, as_of="2026-06-01").iloc[0]
    assert row["contracted_to_date"] == 840_000
    assert row["elapsed_days"] == 84
    assert row["in_flight"] == False


def test_as_of_defaults_to_the_latest_delivery_date_in_the_data():
    df = pd.DataFrame([dict(placement(verified=208_000,
                                      contracted=TWELVE_WEEK["contracted"],
                                      start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"]),
                            last_delivery_date=THREE_WEEKS_IN)])
    row = m.delivery_vs_contract(df).iloc[0]
    assert row["as_of"] == THREE_WEEKS_IN
    assert row["contracted_to_date"] == 210_000


def test_placement_that_has_not_started_has_no_variance():
    df = pd.DataFrame([placement(verified=0,
                                 contracted=TWELVE_WEEK["contracted"],
                                 start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"])])
    row = m.delivery_vs_contract(df, as_of="2025-12-01").iloc[0]
    assert row["elapsed_days"] == 0
    assert row["contracted_to_date"] == 0
    assert pd.isna(row["variance_pct"])          # not 0%, and not a flag
    assert m.delivery_variance_ranked(df, as_of="2025-12-01").empty


# --- spend --------------------------------------------------------------------

def test_spend_prorates_the_four_week_rate_to_the_days_that_ran():
    # A 28-day rate of CAD 2,800 is CAD 100 a day. 21 days in: CAD 2,100.
    df = pd.DataFrame([dict(placement(contracted=TWELVE_WEEK["contracted"],
                                      start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"]),
                            negotiated_rate=2_800)])
    assert m.spend_to_date(df, as_of=THREE_WEEKS_IN).iloc[0]["spend"] == 2_100.0


def test_spend_over_a_full_flight_is_the_rate_times_periods():
    # 84 days is exactly three four-week periods, so 3 x CAD 2,800.
    df = pd.DataFrame([dict(placement(contracted=TWELVE_WEEK["contracted"],
                                      start=TWELVE_WEEK["start"], end=TWELVE_WEEK["end"]),
                            negotiated_rate=2_800)])
    assert m.spend_to_date(df, as_of="2026-06-01").iloc[0]["spend"] == 8_400.0


# --- in-flight fault detection -------------------------------------------------
# Every series below is planned at 100 impressions a day, so a day's delivery IS
# its index in percent and the arithmetic can be checked by eye.

PLANNED = 100


def test_daily_index_is_delivery_against_that_days_plan():
    assert m.daily_delivery_index([100, 50, 0], PLANNED) == [1.0, 0.5, 0.0]


def test_daily_index_of_a_placement_planned_for_nothing_is_empty():
    assert m.daily_delivery_index([100, 50], 0) == []


def test_a_healthy_placement_has_no_fault_and_no_alert():
    t = m.detection_timeline([100] * 20, PLANNED, flight_days=20)
    assert t["observed_onset_day"] is None
    assert t["alert_day"] is None
    assert t["recovered"] is False


def test_one_bad_day_is_not_a_fault():
    # A digital screen dark for an afternoon. Three consecutive days are needed.
    series = [100] * 5 + [0] + [100] * 5
    assert m.fault_onset_day(m.daily_delivery_index(series, PLANNED)) is None


def test_two_bad_days_are_still_not_a_fault():
    series = [100] * 5 + [50, 50] + [100] * 5
    assert m.fault_onset_day(m.daily_delivery_index(series, PLANNED)) is None


def test_three_bad_days_are_a_fault_and_onset_is_the_first_of_them():
    series = [100] * 5 + [50, 50, 50] + [100] * 5
    assert m.fault_onset_day(m.daily_delivery_index(series, PLANNED)) == 5


def test_alert_crosses_when_cumulative_delivery_falls_below_the_line():
    # Three full days then three dark ones: by day 3 cumulative is 300 against
    # 400 expected, which is -25% and well past the -5% line.
    assert m.alert_crossing_day([100, 100, 100, 0, 0, 0], PLANNED) == 3


def test_alert_does_not_cross_on_normal_variation():
    # Every day within 4% of plan never puts cumulative delivery past -5%.
    assert m.alert_crossing_day([96, 104, 97, 103, 98] * 4, PLANNED) is None


def test_fault_then_repair_is_recorded_as_recovered():
    # Healthy 5 days, broken 5, repaired for the remaining 10.
    t = m.detection_timeline([100] * 5 + [50] * 5 + [100] * 10, PLANNED, flight_days=20)
    assert t["observed_onset_day"] == 5
    assert t["recovery_day"] == 10
    assert t["recovered"] is True
    assert t["pre_fault_index"] == 1.0
    assert t["fault_index"] == 0.5


def test_detection_delay_is_measured_against_reconciliation():
    # The whole claim in one test. Fault starts on day 10 of a 20-day flight.
    # Cumulative delivery crosses -5% on day 11 -- one day later. End-of-campaign
    # reconciliation would not have found it for another 10 days.
    t = m.detection_timeline([100] * 10 + [50] * 10, PLANNED, flight_days=20)
    assert t["observed_onset_day"] == 10
    assert t["alert_day"] == 11
    assert t["detection_delay_days"] == 1
    assert t["reconciliation_delay_days"] == 10
    # 20-day flight, flagged at the close of day 11: 8 days left to act in.
    assert t["days_remaining_at_detection"] == 8


def test_a_late_fault_can_be_real_without_crossing_the_alert_line():
    # Broken for the last three days of a 40-day flight: a genuine fault, but
    # cumulative delivery is only 1.1% behind, so it is not an alert. Real
    # problems that are too small to flag have to stay too small to flag.
    t = m.detection_timeline([100] * 37 + [50] * 3, PLANNED, flight_days=40)
    assert t["observed_onset_day"] == 37
    assert t["alert_day"] is None
    assert t["detection_delay_days"] is None


def test_a_fault_from_day_one_has_no_pre_fault_period():
    t = m.detection_timeline([50] * 20, PLANNED, flight_days=20)
    assert t["observed_onset_day"] == 0
    assert t["pre_fault_index"] is None
    assert t["fault_index"] == 0.5


# --- shortfall decomposition, pacing and exposure ------------------------------

def test_gross_shortfall_is_not_reduced_by_over_delivery_elsewhere():
    # Two placements, each contracted 1000 to date. One delivers 600 (400 short),
    # the other 1200 (200 over). Net is -200, which reads as -10% and looks mild.
    # Gross is 400: that is the shortfall an advertiser actually experienced, and
    # 50% of it is masked by the other site running hot.
    df = pd.DataFrame([{"contracted_to_date": 1000, "verified_impressions": 600},
                       {"contracted_to_date": 1000, "verified_impressions": 1200}])
    d = m.shortfall_decomposition(df)
    assert d["gross_shortfall"] == 400
    assert d["over_delivery_offset"] == 200
    assert d["net_shortfall"] == 200
    assert d["masking_pct"] == 50.0
    assert d["placements_behind"] == 1
    assert d["variance_pct"] == -10.0


def test_a_fully_healthy_book_has_no_shortfall_and_no_masking():
    df = pd.DataFrame([{"contracted_to_date": 1000, "verified_impressions": 1000}])
    d = m.shortfall_decomposition(df)
    assert d["gross_shortfall"] == 0
    assert d["masking_pct"] == 0.0
    assert d["placements_behind"] == 0


def test_recovery_pace_is_what_finishing_whole_would_take():
    # 10-day flight, 1000 contracted, so 100 a day planned. Five days in, only
    # 300 delivered against 500 expected. 700 is still owed over 5 remaining
    # days = 140 a day, which is 1.4x the planned 100.
    df = pd.DataFrame([placement(contracted=1000, verified=300)])
    row = m.pacing(df, as_of="2026-01-05").iloc[0]
    assert row["elapsed_days"] == 5
    assert row["remaining_days"] == 5
    assert row["planned_daily"] == 100
    assert row["remaining_contracted"] == 700
    assert row["required_daily"] == 140
    assert row["recovery_pace"] == 1.4
    assert row["delivery_index"] == 0.6


def test_a_placement_on_plan_needs_exactly_its_planned_daily_delivery():
    # Delivered exactly to plan: recovery pace is 1.0, i.e. carry on as booked.
    df = pd.DataFrame([placement(contracted=1000, verified=500)])
    row = m.pacing(df, as_of="2026-01-05").iloc[0]
    assert row["delivery_index"] == 1.0
    assert row["recovery_pace"] == 1.0


def test_a_closed_flight_has_no_recovery_pace():
    # Nothing left to recover in; the number would be a division by zero.
    df = pd.DataFrame([placement(contracted=1000, verified=900)])
    row = m.pacing(df, as_of="2026-01-11").iloc[0]
    assert row["remaining_days"] == 0
    assert pd.isna(row["required_daily"])
    assert pd.isna(row["recovery_pace"])


def test_billed_shortfall_is_priced_at_the_contracted_rate():
    # Five days into a 10-day flight: 500 contracted to date, 300 delivered,
    # 200 short. Spend to date is CAD 50, so contracted CPM is
    # 50 / 500 * 1000 = CAD 100 per thousand, and 200 short is worth CAD 20.
    df = pd.DataFrame([dict(placement(contracted=1000, verified=300), spend=50.0)])
    row = m.exposure(df, as_of="2026-01-05").iloc[0]
    assert row["shortfall"] == 200
    assert row["contracted_cpm"] == 100.0
    assert row["billed_shortfall"] == 20.0


def test_preventable_exposure_prices_the_rest_of_the_flight():
    # Same placement. It is running at 0.6 of plan, so it loses 40 impressions
    # a day against a planned 100. Five days remain, so 200 more impressions
    # are at stake, worth another CAD 20 at the same contracted CPM.
    df = pd.DataFrame([dict(placement(contracted=1000, verified=300), spend=50.0)])
    row = m.exposure(df, as_of="2026-01-05").iloc[0]
    assert row["daily_bleed"] == 40.0
    assert row["preventable_exposure"] == 20.0


def test_a_closed_flight_has_nothing_left_to_prevent():
    df = pd.DataFrame([dict(placement(contracted=1000, verified=900), spend=100.0)])
    row = m.exposure(df, as_of="2026-01-11").iloc[0]
    assert row["billed_shortfall"] == 10.0     # 100 short at CAD 100 per thousand
    assert row["preventable_exposure"] == 0.0


def test_exposure_prices_the_rest_of_the_flight_on_the_current_rate():
    # A placement that ran healthy then broke. Cumulative delivery is 450 of 500
    # expected -- only 10% behind -- but it is currently running at 50% of plan.
    # Pricing the remaining 5 days on the cumulative 0.9 would understate the
    # bleed fivefold: 10 a day instead of 50.
    df = pd.DataFrame([dict(placement(contracted=1000, verified=450), spend=50.0)])
    cumulative = m.exposure(df, as_of="2026-01-05").iloc[0]
    current = m.exposure(df, as_of="2026-01-05", current_index=[0.5]).iloc[0]
    assert round(cumulative["daily_bleed"], 6) == 10.0
    assert round(current["daily_bleed"], 6) == 50.0
    # 50 a day x 5 remaining days = 250 impressions at CAD 100 per thousand.
    assert round(current["preventable_exposure"], 6) == 25.0


def test_exposure_falls_back_to_the_cumulative_rate_when_none_is_given():
    df = pd.DataFrame([dict(placement(contracted=1000, verified=450), spend=50.0)])
    assert (m.exposure(df, as_of="2026-01-05", current_index=[None]).iloc[0]["daily_bleed"]
            == m.exposure(df, as_of="2026-01-05").iloc[0]["daily_bleed"])
