"""Taproot credit API: assess a business, officer summary, demo personas, bank portfolio view.

Everything here is decision support for the bank. Demo endpoints use
simulated data and say so in every response.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.credit import consent as loan_consent
from app.credit.demo import PERSONAS, account_inflows, portfolio
from app.credit.features import AltData, Contribution
from app.credit.service import assess, officer_summary, voice_summary
from app.trade.ledger import LAGOS, Entry

router = APIRouter()
DASHBOARD = Path(__file__).resolve().parents[2] / "credit" / "dashboard.html"


class EntryIn(BaseModel):
    kind: str = Field(pattern="^(sale|restock)$")
    day: date
    amount: Decimal
    profit: Decimal = Decimal("0")
    product_name: str = "item"


class AjoIn(BaseModel):
    day: date
    amount: Decimal
    on_time: bool = True


class AssessIn(BaseModel):
    name: str | None = None
    business_type: str = Field("trader", pattern="^(trader|farmer|manufacturer)$")
    months_in_business: int = 0
    entries: list[EntryIn] = []
    ajo_contributions: list[AjoIn] = []
    ajo_expected: int = 0
    bills_on_time: int = 0
    bills_total: int = 0
    inflows: list[tuple[date, Decimal]] = []
    existing_monthly_debt: Decimal = Decimal("0")
    advice_sessions: int = 0
    women_led: bool | None = None
    account_inflows: Decimal | None = None  # money into the trader's Zenith account, same period


def _entry(e: EntryIn) -> Entry:
    when = datetime(e.day.year, e.day.month, e.day.day, 12, tzinfo=LAGOS)
    one = Decimal("1")
    return Entry(kind=e.kind, product_name=e.product_name, qty=one, unit_price=e.amount, unit_cost=e.amount - e.profit,
                 set_price=e.amount, amount=e.amount, profit=e.profit, created_at=when)


@router.post("/credit/assess")
def assess_business(body: AssessIn) -> dict:
    alt = AltData(
        business_type=body.business_type,
        months_in_business=body.months_in_business,
        ajo_contributions=[Contribution(c.day, c.amount, c.on_time) for c in body.ajo_contributions],
        ajo_expected=body.ajo_expected,
        bills_on_time=body.bills_on_time,
        bills_total=body.bills_total,
        inflows=body.inflows,
        existing_monthly_debt=body.existing_monthly_debt,
        advice_sessions=body.advice_sessions,
        women_led=body.women_led,
    )
    a = assess([_entry(e) for e in body.entries], alt, account_inflows=body.account_inflows)
    return {**a.to_dict(), "voice_summary": voice_summary(a, body.name)}


@router.get("/credit/personas")
def list_personas() -> list[dict]:
    out = []
    for key, (name, about, make) in PERSONAS.items():
        a = _persona(key)
        out.append({"key": key, "name": name, "about": about, "score": a.score.score, "band": a.score.band,
                    "trust": a.trust.level, "simulated": True})
    return out


def _persona(key: str):
    if key not in PERSONAS:
        raise HTTPException(404, "Unknown persona")
    entries, alt = PERSONAS[key][2]()
    return assess(entries, alt, account_inflows=account_inflows(key, entries), simulated=True)


@router.get("/credit/personas/{key}")
def persona(key: str) -> dict:
    a = _persona(key)
    name, about, _ = PERSONAS[key]
    return {"name": name, "about": about, **a.to_dict(), "voice_summary": voice_summary(a, name),
            "officer_summary": _demo_officer(key, a)}


def _demo_officer(key: str, a) -> dict:
    name = PERSONAS[key][0]
    return officer_summary(
        a, name=f"{name} (simulated)", ref=f"TAP-DEMO-{key.upper()}",
        consent={"status": "granted (simulated)", "partner": loan_consent.PARTNER,
                 "purpose": loan_consent.PURPOSE, "version": loan_consent.VERSION,
                 "channel": "voice", "language": "as chosen by trader"} if a.band else
                {"status": "not asked: record not ready for a loan, nothing shared"},
    )


@router.get("/credit/personas/{key}/officer")
def persona_officer(key: str) -> dict:
    """The one-page summary a Zenith loan officer receives (simulated persona)."""
    return _demo_officer(key, _persona(key))


@router.get("/credit/officer/{wa_id}")
async def officer_for_trader(wa_id: str) -> dict:
    """Live: officer summary for a real trader, only with an active loan-sharing consent.

    Needs the full app (database). Protect this route behind the bank's
    staff authentication before any real deployment.
    """
    from app.storage import storage

    grant = await storage.credit_consent_active(wa_id, loan_consent.PARTNER)
    if grant is None:
        raise HTTPException(403, "No active consent to share this record")
    entries = await storage.trade_entries(wa_id)
    user = await storage.get_user(wa_id)
    a = assess(entries, AltData(business_type=getattr(user, "role", None) if getattr(user, "role", None) in
                                 ("trader", "manufacturer", "farmer") else "trader"))
    return officer_summary(
        a, name=getattr(user, "preferred_name", None) or getattr(user, "name", None),
        ref=f"TAP-{grant.id:06d}",
        consent={"status": "granted", "partner": grant.partner, "purpose": grant.purpose,
                 "version": grant.version, "language": grant.language, "channel": grant.channel,
                 "granted_at": grant.granted_at.isoformat()},
    )


_PORTFOLIO_CACHE: dict | None = None


@router.get("/credit/portfolio")
def portfolio_view() -> dict:
    """Bank officer view: pre-qualified pipeline across the synthetic portfolio."""
    global _PORTFOLIO_CACHE
    if _PORTFOLIO_CACHE is None:
        rows = []
        for sme in portfolio():
            a = assess(sme["entries"], sme["alt"], account_inflows=sme["account_inflows"], simulated=True)
            best = a.offers[0]
            rows.append({
                "id": sme["id"],
                "state": sme["state"],
                "type": a.features.business_type,
                "women_led": bool(sme["alt"].women_led),
                "score": a.score.score,
                "band": a.score.band,
                "avg_monthly_profit": float(a.features.avg_monthly_profit),
                "offer": best.product.name if best.amount > 0 or a.score.band in ("D", "E")
                else "No new loan: repayments at limit",
                "zenith_product": best.product.zenith_product,
                "band_min": a.band[0] if a.band else 0,
                "band_max": a.band[1] if a.band else 0,
                "trust": a.trust.level,
                "flags": len([x for x in a.trust.flags if x.severity != "info"]),
                "top_reason": (a.score.strengths or a.score.concerns or [None])[0].text
                if (a.score.strengths or a.score.concerns) else "",
                "concern": a.score.concerns[0].text if a.score.concerns else "",
            })
        bands = Counter(r["band"] for r in rows)
        approvable = [r for r in rows if r["band"] in ("A", "B", "C")]
        _PORTFOLIO_CACHE = {
            "total": len(rows),
            "bands": {b: bands.get(b, 0) for b in "ABCDE"},
            "pre_qualified": len(approvable),
            "simulated": True,
            "pipeline_low": sum(r["band_min"] for r in approvable),
            "pipeline_high": sum(r["band_max"] for r in approvable),
            "trust": dict(Counter(r["trust"] for r in rows)),
            "women_led_share": sum(r["women_led"] for r in approvable) / len(approvable) if approvable else 0,
            "by_type": dict(Counter(r["type"] for r in approvable)),
            "by_state": dict(Counter(r["state"] for r in approvable).most_common(8)),
            "rows": sorted(rows, key=lambda r: -r["score"]),
        }
    return _PORTFOLIO_CACHE


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD.read_text(encoding="utf-8")
