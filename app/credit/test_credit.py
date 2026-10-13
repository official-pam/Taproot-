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


def _farm_year():
    from app.credit.demo import _sale
    entries = []
    for year in (2025, 2026):
        for month in (9, 10, 11):  # harvest sales only; nothing for the rest of the year
            for day in range(1, 28, 3):
                entries.append(_sale(date(year, month, day), "maize (bag)", 4, 50000, 30000))
    return entries


def test_farmer_not_punished_for_dry_season():
    entries = _farm_year()
    farmer = assess(entries, AltData(business_type="farmer"))
    trader = assess(entries, AltData(business_type="trader"))
    assert farmer.features.consistency > trader.features.consistency
    assert not any(r.factor == "consistency" for r in farmer.score.concerns)
    assert any(r.factor == "consistency" for r in trader.score.concerns)


def test_grain_trader_story_persona():
    a = assess(*hauwa())
    assert a.score.band in ("A", "B")
    assert "final decision" in voice_summary(a, "Hauwa")


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
    assert r["band"] in "ABC" and r["offers"][0]["computed_amount"] > 0
    assert r["indicative_loan_band"] is not None
    officer = c.get("/credit/personas/hauwa/officer").json()
    assert officer["simulated"] and "does not approve" in officer["decision_support_only"]
    assert officer["suggested_product"]["zenith_product"]
    assert c.get("/credit/personas/musa").json()["simulated"] is True
    assert "Taproot" in c.get("/dashboard").text


def test_inflated_record_is_flagged_by_account_cross_check():
    from app.credit.demo import account_inflows
    entries, alt = musa()
    a = assess(entries, alt, account_inflows=account_inflows("musa", entries))
    assert a.trust.level == "low"
    assert any(f.code == "account_gap" and f.severity == "serious" for f in a.trust.flags)


def test_steady_logging_beats_one_big_week():
    from datetime import timedelta
    from app.credit.demo import _sale
    start = date(2026, 6, 1)
    steady = [_sale(start + timedelta(days=i), "rice", 1, 50000, 40000) for i in range(70)]
    burst = [_sale(start + timedelta(days=i % 7), "rice", 10, 50000, 40000) for i in range(70)]
    s_steady = assess(steady, AltData(), account_inflows=Decimal("3500000"))
    s_burst = assess(burst, AltData(), account_inflows=Decimal("35000000"))
    assert s_steady.trust.logged_days == 70 and s_burst.trust.logged_days == 7
    assert s_steady.score.score > s_burst.score.score


def test_margin_sanity_check():
    from app.credit.demo import _sale
    entries = [_sale(date(2026, 8, d), "soap", 1, 10000, 1000) for d in range(1, 29)]
    a = assess(entries)
    assert any(f.code == "margin_high" for f in a.trust.flags)
