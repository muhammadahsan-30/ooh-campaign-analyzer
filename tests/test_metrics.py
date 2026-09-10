"""
Tests use small hand-built inputs so the arithmetic can be checked by eye.
Run with: pytest -q
"""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import metrics as m


def test_delivery_vs_contract_computes_shortfall():
    df = pd.DataFrame([{
        "placement_id": 1, "campaign_id": 1, "site_id": 1, "city": "Toronto",
        "format": "bulletin", "contracted_impressions": 1000,
        "verified_impressions": 900,
    }])
    out = m.delivery_vs_contract(df).iloc[0]
    assert out["variance_abs"] == -100          # 900 - 1000
    assert out["variance_pct"] == -10.0         # -100 / 1000 * 100


def test_cpm_is_spend_per_thousand():
    df = pd.DataFrame([{"placement_id": 1, "campaign_id": 1, "format": "bulletin",
                        "spend": 50_000, "verified_impressions": 100_000}])
    # 50,000 / 100,000 * 1000 = 500
    assert m.cpm(df).iloc[0]["cpm"] == 500.0


def test_rate_efficiency_reads_as_discount():
    df = pd.DataFrame([{"placement_id": 1, "campaign_id": 1, "site_id": 1,
                        "rate_card_monthly": 1_000_000, "negotiated_rate": 750_000}])
    assert m.rate_efficiency(df).iloc[0]["discount_pct"] == 25.0


def test_grp_is_impressions_over_population():
    df = pd.DataFrame([{"verified_impressions": 500_000}])
    # 500,000 / 1,000,000 * 100 = 50
    assert m.grp(df, 1_000_000).iloc[0]["grp"] == 50.0


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
    df = pd.DataFrame([
        {"placement_id": 1, "campaign_id": 1, "site_id": 1, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 990},
        {"placement_id": 2, "campaign_id": 1, "site_id": 2, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 600},
        {"placement_id": 3, "campaign_id": 1, "site_id": 3, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 800},
    ])
    out = m.delivery_variance_ranked(df)
    assert list(out["placement_id"]) == [2, 3]   # -40% then -20%; -1% is above threshold


def test_variance_ranking_threshold_is_adjustable():
    df = pd.DataFrame([
        {"placement_id": 1, "campaign_id": 1, "site_id": 1, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 990},
        {"placement_id": 2, "campaign_id": 1, "site_id": 2, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 600},
        {"placement_id": 3, "campaign_id": 1, "site_id": 3, "city": "Toronto",
         "format": "bulletin", "contracted_impressions": 1000, "verified_impressions": 800},
    ])
    # At a -30% line only placement 2 (-40%) is bad enough to show.
    out = m.delivery_variance_ranked(df, threshold_pct=-30)
    assert list(out["placement_id"]) == [2]
