"""One call from records to a loan officer's summary.

``assess`` is what the WhatsApp flow, the API and the bank dashboard all use:
records → features → data-trust checks → score → matched products → an
indicative loan-size band. Taproot never approves or declines a loan; the
output is decision support for the bank's loan officer.

``voice_summary`` is the short reply read back to the trader as a voice note
(translated by the existing N-ATLAS pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.credit.features import AltData, Features, build_features
from app.credit.matching import Offer, indicative_band, match, women_led_note
from app.credit.scoring import Score, score
from app.credit.trust import Trust, check
from app.trade.ledger import Entry

SIMULATED_NOTE = "Simulated data for demonstration. Not a real customer."


def _band_text(band: tuple[int, int] | None) -> str:
    return f"₦{band[0]:,} – ₦{band[1]:,}" if band else "No loan yet"


@dataclass
class Assessment:
    features: Features
    trust: Trust
    score: Score
    offers: list[Offer]
    band: tuple[int, int] | None
    alt: AltData
    simulated: bool = False

    def to_dict(self) -> dict:
        f, s = self.features, self.score
        best = self.offers[0]
        return {
            "simulated": self.simulated,
            "score": s.score,
            "band": s.band,
            "band_meaning": s.band_meaning,
            "thin_file": s.thin_file,
            "indicative_loan_band": None if self.band is None else {"min": self.band[0], "max": self.band[1]},
            "indicative_loan_band_text": _band_text(self.band),
            "strengths": [{"factor": r.factor, "points": r.points, "text": r.text} for r in s.strengths],
            "concerns": [{"factor": r.factor, "points": r.points, "text": r.text} for r in s.concerns],
            "tips": s.tips,
            "trust": self.trust.to_dict(),
            "business": {
                "type": f.business_type,
                "months_of_records": f.months_of_records,
                "months_in_business": f.months_in_business,
                "avg_monthly_revenue": float(f.avg_monthly_revenue),
                "avg_monthly_profit": float(f.avg_monthly_profit),
                "margin": f.margin,
                "consistency": f.consistency,
                "growth": f.growth,
                "monthly_revenue": [float(v) for v in f.monthly_revenue],
            },
            "offers": [
                {
                    "code": o.product.code,
                    "name": o.product.name,
                    "zenith_product": o.product.zenith_product,
                    "description": o.product.description,
                    "computed_amount": float(o.amount),
                    "repayment": float(o.repayment),
                    "repayment_schedule": "once after harvest" if o.product.seasonal
                    else f"monthly for {o.product.months} months",
                    "why": o.why,
                }
                for o in self.offers
            ],
            "best_product": best.product.name,
            "women_led_note": women_led_note(self.alt.women_led),
        }


def assess(entries: list[Entry], alt: AltData | None = None, *, account_inflows: Decimal | None = None,
           simulated: bool = False) -> Assessment:
    alt = alt or AltData()
    f = build_features(entries, alt)
    t = check(entries, account_inflows)
    s = score(f, t)
    offers = match(f, s, alt.existing_monthly_debt)
    band = indicative_band(offers[0].amount, t.level) if offers[0].amount > 0 else None
    return Assessment(f, t, s, offers, band, alt, simulated)


def officer_summary(a: Assessment, *, name: str | None = None, ref: str | None = None,
                    consent: dict | None = None, kyc: dict | None = None) -> dict:
    """What the Zenith loan officer receives after the trader consents to share.

    One page: who, what the record shows, how far to trust it, why the summary
    says what it says, and the product to consider. No approve/decline.
    """
    d = a.to_dict()
    f, t = a.features, a.trust
    return {
        "reference": ref,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "simulated": a.simulated,
        "notice": SIMULATED_NOTE if a.simulated else None,
        "decision_support_only": "Taproot does not approve or decline loans. The credit decision is Zenith's.",
        "applicant": {
            "name": name,
            "business_type": f.business_type,
            "months_in_business": f.months_in_business,
            "kyc": kyc or {"bvn": "to be linked at application", "nin": "to be linked at application"},
        },
        "consent": consent or {"status": "not yet given"},
        "record": {
            "days_logged": t.logged_days,
            "logging_rate": d["trust"]["logging_rate"],
            "longest_streak_days": t.longest_streak,
            "avg_daily_revenue": float(t.avg_daily_revenue),
            "daily_revenue_variability": d["trust"]["daily_revenue_cv"],
            "avg_monthly_revenue": float(f.avg_monthly_revenue),
            "avg_monthly_profit": float(f.avg_monthly_profit),
            "gross_margin": f.margin,
            "trend_3m": f.growth,
        },
        "data_trust": {"level": t.level, "flags": d["trust"]["flags"]},
        "summary": {
            "score": a.score.score,
            "band": a.score.band,
            "meaning": a.score.band_meaning,
            "why": [r["text"] for r in d["strengths"][:4]],
            "watch": [r["text"] for r in d["concerns"][:4]],
        },
        "suggested_product": {
            "taproot": d["offers"][0]["name"],
            "zenith_product": d["offers"][0]["zenith_product"],
            "indicative_loan_band": d["indicative_loan_band_text"],
            "sizing_rule": d["offers"][0]["why"],
        },
        "also": d["women_led_note"],
    }


def voice_summary(a: Assessment, name: str | None = None) -> str:
    """Short, plain English for a voice note. Numbers in naira, no jargon, no promises."""
    hello = f"{name}, " if name else ""
    s = a.score
    if a.band is None and not s.thin_file and s.band in ("A", "B", "C"):
        return (f"{hello}your sales book looks good. But your loan repayments now already take as much as "
                "your profit can safely carry. Finish paying those first, then ask me again.")
    if s.thin_file or a.band is None:
        lines = [f"{hello}thank you for keeping your sales book. We need a little more time to know your business."]
        if s.tips:
            lines.append(s.tips[0])
        else:
            lines.append(a.offers[0].why)
        return " ".join(lines)
    lines = [f"{hello}your sales book is ready for Zenith Bank."]
    if s.strengths:
        lines.append("What stands out: " + "; ".join(r.text.lower() for r in s.strengths[:2]) + ".")
    lines.append(f"Your record supports a {a.offers[0].product.name.lower()} of about "
                 f"₦{a.band[0]:,} to ₦{a.band[1]:,}. A Zenith loan officer makes the final decision.")
    lines.append("Do you want to share your record with Zenith Bank?")
    return " ".join(lines)
