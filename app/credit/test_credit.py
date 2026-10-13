"""Tests for the Taproot credit engine (pure, no database)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.credit.demo import PERSONAS, portfolio
from app.credit.features import AltData, build_features
from app.credit.matching import AFFORDABILITY
from app.credit.scoring import MAX_SCORE, MIN_SCORE
from app.credit.service import assess, voice_summary
from demo_main import app


def run(key):
    return assess(*PERSONAS[key][2]())


def test_personas_land_in_expected_bands():
    assert run("ngozi").score.band == "A"
    assert run("hauwa").score.band in ("A", "B")
    assert run("tunde").score.band in ("A", "B")
    assert run("bisi").score.band == "D"
    assert run("musa").score.band == "E"


def test_farmer_gets_seasonal_loan_first():
    assert run("hauwa").offers[0].product.code == "SEASON"


def test_thin_file_with_strong_ajo_gets_group_loan_not_big_loan():
    a = run("bisi")
    assert a.score.thin_file
    assert a.offers[0].product.code == "GROUP"


def test_risky_business_only_gets_credit_builder():
    a = run("musa")
    assert [o.product.code for o in a.offers] == ["BUILDER"]
    assert a.score.concerns


def test_monthly_repayment_is_affordable():
    for key in ("ngozi", "tunde"):
        a = run(key)
        for o in a.offers:
            if not o.product.seasonal and o.amount:
                assert o.repayment <= a.features.avg_monthly_profit * AFFORDABILITY + 1


def test_existing_debt_reduces_offer():
    entries, alt = PERSONAS["ngozi"][2]()
    base = assess(entries, alt).offers[0].amount
    alt.existing_monthly_debt = Decimal("20000")
    assert assess(entries, alt).offers[0].amount < base


def test_gender_never_changes_the_score():
    entries, alt = PERSONAS["hauwa"][2]()
    alt.women_led = True
    a = assess(entries, alt).score.score
    alt.women_led = False
    assert assess(entries, alt).score.score == a


def test_farm_dry_season_not_punished_like_a_trader():
    entries, alt = PERSONAS["hauwa"][2]()
    farm = build_features(entries, alt).consistency
    alt.business_type = "trader"
    assert farm > build_features(entries, alt).consistency


def test_empty_records_are_safe():
    a = assess([], AltData())
    assert MIN_SCORE <= a.score.score <= MAX_SCORE and a.score.thin_file
    assert voice_summary(a)


def test_portfolio_scores_stay_in_range():
    for sme in portfolio(40):
        s = assess(sme["entries"], sme["alt"]).score.score
        assert MIN_SCORE <= s <= MAX_SCORE


def test_api_and_dashboard():
    c = TestClient(app)
    assert c.get("/credit/personas").status_code == 200
    d = c.get("/credit/personas/hauwa").json()
    assert d["voice_summary"] and d["offers"]
    p = c.get("/credit/portfolio").json()
    assert p["total"] == 300 and sum(p["bands"].values()) == 300
    assert "Taproot" in c.get("/dashboard").text
    body = {"business_type": "trader", "entries": [
        {"kind": "sale", "day": f"2026-{m:02d}-10", "amount": 200000, "profit": 50000} for m in range(1, 10)]}
    r = c.post("/credit/assess", json=body).json()
    assert r["band"] in "ABCDE" and r["offers"]
