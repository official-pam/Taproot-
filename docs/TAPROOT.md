# Taproot: product notes and hackathon roadmap

## What is built

- Credit engine (`app/credit/`): features from the sales book and alternative data, explainable 300–850 scorecard with bands A–E, product matching with affordability caps, and a plain-English voice summary.
- API (`/credit/assess`, `/credit/personas`, `/credit/portfolio`) and a bank officer dashboard (`/dashboard`).
- Five synthetic personas plus a 300-business synthetic portfolio. No real customer data.
- Tests in `app/credit/test_credit.py`, covering bands, affordability, the debt effect, the gender-neutrality check, season-awareness and the API.

## Score bands

| Band | Score | Meaning |
| --- | --- | --- |
| A | 720+ | Strong: approve on standard terms |
| B | 640–719 | Good: approve with standard monitoring |
| C | 560–639 | Fair: smaller first loan, limit grows with repayment |
| D | 480–559 | Building: credit builder or àjọ group loan |
| E | below 480 | Not yet: keep recording, Taproot checks again |

A thin file (fewer than 3 months of records) is capped at band D, so strong àjọ history can still unlock a small group loan.

## Hackathon build plan (20–22 October)

1. **WhatsApp flow:** add "Check my loan options" to the trader and farm menus. Call `assess()` on the user's own `trade_entries`, translate `voice_summary()` through the existing N-ATLAS pipeline and send it as a voice note.
2. **Consent screens:** separate consent for each new data source (àjọ, bills, mobile money), in five languages. Nothing is scored without consent.
3. **Àjọ capture:** the group leader confirms contributions by voice ("Bisi paid ₦5,000 today"), so the record has a second witness.
4. **Receipt photos:** GenAI extraction into ledger entries, kept only when the owner confirms (same Yes/No pattern as `app/trade/flow.py`).
5. **Bank side:** the dashboard filters, an application queue, and a "why this score" view for credit officers.
6. **Growth agent:** connect band A–C farmers to off-takers, and send restock timing tips to traders.

## Model roadmap

- The weights in `scoring.py` are a transparent starting point, not a trained model.
- During the pilot, log every assessment and repayment outcome. Then fit a gradient-boosted model on the same features, keep SHAP reason codes, and run fairness checks across self-declared groups and states.
- Recalibrate seasonal sizing per crop and zone using `app/agri/crops.py` and `app/agri/zones.py`.

## Open questions for the bank

- The real product catalogue, rates and limits to replace the placeholders in `matching.py`
- Which identity and KYC details lenders need on the "Record for a loan" statement
- Open banking API access for consented statement data
