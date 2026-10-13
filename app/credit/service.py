"""One call from records to decision: features → score → offers.

``assess`` is what the WhatsApp flow, the API and the bank dashboard all use.
``voice_summary`` is the short reply read back to the owner as a voice note
(translated by the existing N-ATLAS pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.credit.features import AltData, Features, build_features
from app.credit.matching import Offer, match
from app.credit.scoring import Score, score
from app.trade.ledger import Entry


@dataclass
class Assessment:
    features: Features
    score: Score
    offers: list[Offer]
    alt: AltData

    def to_dict(self) -> dict:
        f, s = self.features, self.score
        return {
            "score": s.score,
            "band": s.band,
            "band_meaning": s.band_meaning,
            "thin_file": s.thin_file,
            "strengths": [{"factor": r.factor, "points": r.points, "text": r.text} for r in s.strengths],
            "concerns": [{"factor": r.factor, "points": r.points, "text": r.text} for r in s.concerns],
            "tips": s.tips,
            "business": {
                "type": f.business_type,
                "months_of_records": f.months_of_records,
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
                    "description": o.product.description,
                    "amount": float(o.amount),
                    "repayment": float(o.repayment),
                    "repayment_schedule": "once after harvest" if o.product.seasonal
                    else f"monthly for {o.product.months} months",
                    "total_cost": float(o.total_cost),
                    "why": o.why,
                }
                for o in self.offers
            ],
            "support_programmes": ["Women-led SME support"] if self.alt.women_led else [],
        }


def assess(entries: list[Entry], alt: AltData | None = None) -> Assessment:
    alt = alt or AltData()
    f = build_features(entries, alt)
    s = score(f)
    return Assessment(f, s, match(f, s, alt.existing_monthly_debt), alt)


def voice_summary(a: Assessment, name: str | None = None) -> str:
    """Short, plain English for a voice note. Numbers in naira, no jargon."""
    hello = f"{name}, " if name else ""
    s = a.score
    if s.thin_file:
        lines = [f"{hello}we need a little more time to know your business."]
    else:
        lines = [f"{hello}good news. Taproot has looked at your business records."]
    if s.strengths:
        lines.append("What stands out: " + "; ".join(r.text.lower() for r in s.strengths[:2]) + ".")
    best = a.offers[0]
    if best.amount > 0:
        when = "once, after harvest" if best.product.seasonal else f"each month for {best.product.months} months"
        lines.append(f"You can get a {best.product.name.lower()} of up to ₦{best.amount:,.0f}. "
                     f"You would pay back ₦{best.repayment:,.0f} {when}.")
    else:
        lines.append(best.why)
    if s.tips:
        lines.append(s.tips[0])
    lines.append("Reply YES to apply, or ask me anything.")
    return " ".join(lines)
