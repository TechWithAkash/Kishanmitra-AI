"""The last-resort price ESTIMATE: sensible, repeatable, seasonal, and never a fake market report."""

from datetime import date

import pytest

from kisanmitra import mandi


def test_the_estimate_is_a_range_that_makes_sense():
    e = mandi.estimate("Onion", "Maharashtra", date(2026, 10, 6))
    assert 0 < e["low"] < e["typical"] < e["high"]
    assert e["for_date"] == "2026-10-06"


def test_the_same_question_on_the_same_day_always_gets_the_same_answer():
    assert mandi.estimate("Tomato", "Maharashtra", date(2026, 10, 6)) == mandi.estimate("Tomato", "Maharashtra", date(2026, 10, 6))


def test_prices_follow_the_seasons():
    # tomatoes are dear in the monsoon and cheap in winter; onions peak in autumn and are cheap in spring
    assert mandi.estimate("Tomato", "Maharashtra", date(2026, 7, 15))["typical"] > mandi.estimate("Tomato", "Maharashtra", date(2026, 1, 15))["typical"] * 1.5
    assert mandi.estimate("Onion", "Maharashtra", date(2026, 10, 15))["typical"] > mandi.estimate("Onion", "Maharashtra", date(2026, 4, 15))["typical"] * 1.3


def test_states_differ_a_little():
    kerala = mandi.estimate("Potato", "Kerala", date(2026, 10, 6))["typical"]
    mp = mandi.estimate("Potato", "Madhya Pradesh", date(2026, 10, 6))["typical"]
    assert kerala > mp


@pytest.mark.parametrize("crop, low_limit, high_limit", [
    ("Wheat", 2000, 3200), ("Soyabean", 3500, 6000), ("Cotton", 5500, 9000), ("Paddy(Dhan)(Common)", 1800, 3000),
    ("Onion", 600, 4500), ("Tomato", 500, 6000), ("Potato", 800, 3500), ("Green Chilli", 1500, 7000),
])
def test_every_estimate_is_in_a_believable_rupee_range(crop, low_limit, high_limit):
    for month in range(1, 13):
        e = mandi.estimate(crop, "Maharashtra", date(2026, month, 10))
        assert low_limit <= e["low"] <= e["typical"] <= e["high"] <= high_limit, (crop, month, e)


def test_perishables_swing_more_than_grains():
    def width(crop):
        e = mandi.estimate(crop, "Maharashtra", date(2026, 10, 6))
        return (e["high"] - e["low"]) / e["typical"]
    assert width("Tomato") > width("Onion") > width("Wheat")


def test_an_unknown_crop_gets_no_estimate_rather_than_a_guess():
    assert mandi.estimate("Dragon fruit", "Maharashtra") is None


def test_real_data_always_wins_over_the_estimate(monkeypatch):
    rows = [{"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon", "commodity": "Onion", "arrival_date": "05/10/2026",
             "modal_price": "1900", "min_price": "1500", "max_price": "2200"}]
    monkeypatch.setattr(mandi, "_fetch_live", lambda commodity, state: rows)
    r = mandi.get_prices("Onion", "Nashik", "Maharashtra")
    assert r.source == "live" and r.estimate is None and r.records[0]["market"] == "Lasalgaon"
