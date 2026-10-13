"""Explainable credit scorecard.

A points-based scorecard (300 to 850) rather than a black box, so a credit
officer can see exactly why a business got its score and the owner can be
told, in plain words and in their own language, what would raise it.

Each factor adds or removes points and leaves a reason. Weights are a
starting point to be recalibrated on real repayment outcomes during the
pilot (see docs/TAPROOT.md, "Model roadmap").

Fairness: gender, religion, ethnicity, state of origin and age are never
inputs. ``women_led`` exists on AltData only to route businesses to support
programmes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.credit.features import Features
from app.credit.trust import Trust

BASE = 450
MIN_SCORE, MAX_SCORE = 300, 850

# Score bands: label, minimum score, what it means for the bank
# Bands are decision support for the bank's loan officer, not decisions.
BANDS = [
    ("A", 720, "Strong record: refer to loan officer for standard review"),
    ("B", 640, "Good record: refer to loan officer"),
    ("C", 560, "Fair record: refer for a smaller first loan"),
    ("D", 480, "Building: suggest a group (àjọ) loan or credit builder"),
    ("E", 0, "Not yet: keep logging sales; Taproot will check again"),
]

MIN_MONTHS_FOR_SCORE = 3


@dataclass
class Reason:
    factor: str
    points: int
    text: str  # plain English, short enough to read out in a voice note


@dataclass
class Score:
    score: int
    band: str
    band_meaning: str
    thin_file: bool
    reasons: list[Reason] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)

    @property
    def strengths(self) -> list[Reason]:
        return sorted((r for r in self.reasons if r.points > 0), key=lambda r: -r.points)

    @property
    def concerns(self) -> list[Reason]:
        return sorted((r for r in self.reasons if r.points < 0), key=lambda r: r.points)


def _naira(v: Decimal) -> str:
    return f"₦{v:,.0f}"


def score(f: Features, trust: Trust | None = None) -> Score:
    reasons: list[Reason] = []
    tips: list[str] = []

    def add(factor: str, points: int, text: str) -> None:
        if points:
            reasons.append(Reason(factor, points, text))

    # 1. Length of track record
    m = f.months_of_records
    if m >= 12:
        add("history", 60, f"{m} months of business records")
    elif m >= 6:
        add("history", 35, f"{m} months of business records")
    elif m >= MIN_MONTHS_FOR_SCORE:
        add("history", 10, f"{m} months of records so far")
    else:
        add("history", -40, "Less than 3 months of records")
        tips.append("Record every sale for 3 months and Taproot can score your business.")
    if f.months_in_business >= 36:
        add("tenure", 20, f"In business for about {f.months_in_business // 12} years")

    # 2. Consistency (season-aware for farms)
    c = f.consistency
    label = "season to season" if f.business_type == "farmer" else "month to month"
    if c >= 0.8:
        add("consistency", 70, f"Steady income {label}")
    elif c >= 0.6:
        add("consistency", 35, f"Fairly steady income {label}")
    elif c >= 0.4:
        add("consistency", 0, "")
    else:
        add("consistency", -45, f"Income goes up and down a lot {label}")
        tips.append("Recording every sale, even small ones, shows how steady your business really is.")

    # 3. Profitability
    if f.margin is not None:
        if f.margin >= 0.20:
            add("margin", 55, f"Good profit margin ({f.margin:.0%})")
        elif f.margin >= 0.10:
            add("margin", 30, f"Healthy profit margin ({f.margin:.0%})")
        elif f.margin > 0:
            add("margin", 5, f"Thin profit margin ({f.margin:.0%})")
        else:
            add("margin", -60, "Sales are not making a profit overall")
            tips.append("Check your selling prices: some goods are selling below cost.")
    if f.loss_sale_share > 0.25:
        add("losses", -30, f"{f.loss_sale_share:.0%} of sales were at a loss")

    # 4. Growth
    if f.growth is not None:
        if f.growth >= 0.15:
            add("growth", 40, f"Sales grew {f.growth:.0%} in the last 3 months")
        elif f.growth <= -0.25:
            add("growth", -40, f"Sales fell {abs(f.growth):.0%} in the last 3 months")

    # 5. Reinvestment
    if f.months_of_records >= 3 and f.restock_months / f.months_of_records >= 0.5:
        add("reinvestment", 20, "Restocks regularly: money goes back into the business")

    # 6. àjọ / esusu / cooperative discipline
    if f.ajo_rate is not None:
        on_time = f.ajo_on_time if f.ajo_on_time is not None else 0
        if f.ajo_rate >= 0.9 and on_time >= 0.9:
            add("ajo", 75, "Pays àjọ contributions in full and on time")
        elif f.ajo_rate >= 0.75:
            add("ajo", 35, "Pays most àjọ contributions")
        else:
            add("ajo", -35, "Missed several àjọ contributions")

    # 7. Bills
    if f.bills_rate is not None:
        if f.bills_rate >= 0.9:
            add("bills", 30, "Pays bills and rent on time")
        elif f.bills_rate < 0.6:
            add("bills", -30, "Often late paying bills")

    # 8. Existing debt
    if f.debt_to_profit is not None:
        if f.debt_to_profit > 0.5:
            add("debt", -70, "Existing loan repayments take more than half of monthly profit")
        elif f.debt_to_profit > 0.3:
            add("debt", -25, "Existing loan repayments are already significant")

    # 9. Logging habit and data trust (self-reported records)
    if trust is not None:
        if trust.logged_days >= 60 and trust.logging_rate >= 0.6:
            add("logging", 50, f"Logged sales on {trust.logged_days} days, steadily")
        elif trust.logged_days >= 30 and trust.logging_rate >= 0.4:
            add("logging", 25, f"Logged sales on {trust.logged_days} days")
        elif trust.logged_days < 14:
            add("logging", -20, f"Only {trust.logged_days} days logged so far")
            tips.append("Log your sales every day. A steady habit counts for more than one big week.")
        serious = [x for x in trust.flags if x.severity == "serious"]
        checks = [x for x in trust.flags if x.severity == "check"]
        if serious:
            add("trust", -60, serious[0].text)
        if checks:
            add("trust_checks", -min(45, 15 * len(checks)), checks[0].text)

    # 10. Engagement with growth advice
    if f.advice_sessions >= 5:
        add("engagement", 15, "Actively uses business advice")

    total = BASE + sum(r.points for r in reasons)
    total = max(MIN_SCORE, min(MAX_SCORE, total))
    thin = f.months_of_records < MIN_MONTHS_FOR_SCORE
    if thin:
        # A thin file can still qualify for a credit-builder or group loan
        # (band D) on the strength of àjọ and bills, but nothing larger.
        total = min(total, 559)

    band, meaning = next((b, mean) for b, cut, mean in BANDS if total >= cut)
    return Score(total, band, meaning, thin, reasons, tips)
