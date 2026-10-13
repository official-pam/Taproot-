from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.credit.demo import PERSONAS, bisi, hauwa, musa, ngozi
from app.credit.features import AltData, build_features
from app.credit.service import assess, voice_summary


def test_steady_trader_scores_well():
    a = assess(*ngozi())
    assert a.score.band == "A"
    assert a.offers[0].product.code == "STOCK"


def test_farmer_not_punished_for_dry_season():
    a = assess(*hauwa())
    assert a.score.band in ("A", "B")
    assert a.offers[0].product.seasonal
    assert "after harvest" in voice_summary(a, "Hauwa")


def test_thin_file_with_strong_ajo_gets_group_loan_not_big_loan():
    a = assess(*bisi())
    assert a.score.thin_file and a.score.band == "D"
    assert a.offers[0].product.code == "GROUP"


def test_struggling_business_gets_builder_and_tips():
    a = assess(*musa())
    assert a.score.band == "E"
    assert a.offers[0].amount == 0
    assert a.score.tips


def test_loan_never_exceeds_affordability():
    for _, _, make in PERSONAS.values():
        entries, alt = make()
        a = assess(entries, alt)
        for o in a.offers:
            if o.amount and not o.product.seasonal:
                assert o.repayment + alt.existing_monthly_debt <= a.features.avg_monthly_profit * Decimal("0.30") + 1


def test_gender_does_not_change_score():
    entries, alt = ngozi()
    s1 = assess(entries, alt).score.score
    alt.women_led = False
    assert assess(entries, alt).score.score == s1


def test_empty_records():
    f = build_features([], AltData())
    assert f.months_of_records == 0
    assert assess([]).score.band == "E"


def test_api():
    from demo_main import app
    c = TestClient(app)
    assert len(c.get("/credit/personas").json()) == 5
    assert c.get("/credit/personas/hauwa").json()["name"] == "Hauwa"
    p = c.get("/credit/portfolio").json()
    assert p["total"] == 300 and p["pre_qualified"] > 0
    r = c.post("/credit/assess", json={
        "business_type": "trader",
        "entries": [{"kind": "sale", "day": str(date(2026, m, 5)), "amount": 200000, "profit": 50000} for m in range(1, 10)],
        "bills_on_time": 9, "bills_total": 9,
    }).json()
    assert r["band"] in "ABC" and r["offers"][0]["amount"] > 0
    assert "Taproot" in c.get("/dashboard").text
