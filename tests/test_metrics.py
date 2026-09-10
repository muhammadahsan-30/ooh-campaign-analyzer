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
