# Taproot 🌱

**Credit rooted in how Nigerian SMEs really do business.**

Taproot is a voice-first AI platform on WhatsApp that turns a small business's everyday records into a fair, explainable credit score. It then matches the business to the right financing. It works in Yoruba, Hausa, Igbo, Pidgin and English, with no app, forms or English needed.

> A taproot is the deep root that reaches water in the dry season. It's the part you can't see that keeps the plant alive. Banks only see the surface: collateral, paperwork and statements. Taproot reaches beneath it.

Built for **Zenith Bank Zecathon 6.0, Track 3: Smart SME Financing and Growth Platform.**

## The problem

Hauwa farms maize outside Zaria. When the rains come, she has about two weeks to plant and fertilize. The bank wanted collateral, statements and forms in English. By the time she gave up, the planting window had closed. She borrowed from a moneylender, bought half the fertilizer she needed and harvested half the maize she could have.

Hauwa isn't a credit risk. She's invisible to the bank. Her proof sits in her sales book, her àjọ contributions and her mobile-money transfers.

## How it works

```
 WhatsApp voice note (5 languages)
        │  N-ATLAS speech recognition + understanding
        ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1 Discovery  │──▶│ 2 Scoring    │──▶│ 3 Matching   │──▶│ 4 Growth     │
 │ sales book,  │   │ explainable  │   │ right product│   │ buyers, tips,│
 │ àjọ, bills,  │   │ 300–850 score│   │ sized to real│   │ advice that  │
 │ mobile money │   │ + reasons    │   │ cash flow    │   │ protects loan│
 └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
        │                                      │
        ▼                                      ▼
 Voice-note reply in the owner's language   Bank dashboard: pre-qualified pipeline
```

1. **Discovery.** Traders already keep their sales book by voice through the bot (`app/trade/`). With consent, Taproot adds àjọ/esusu contributions, bill payments and mobile-money inflows (`app/credit/features.py`).
2. **Scoring.** A transparent points scorecard. Every point has a plain-language reason that can be read out in a voice note. It's **season-aware**, so a farmer's quiet dry-season months aren't treated as instability (`app/credit/scoring.py`).
3. **Matching.** Seasonal input loans (repaid once after harvest), stock finance, equipment finance, working capital, àjọ group loans and a credit builder. Monthly repayments are capped at 30% of average profit (`app/credit/matching.py`).
4. **Growth.** The existing farm and trade advisor keeps the business healthy, which protects repayment.

**Fairness:** gender, ethnicity, religion and age are never scoring inputs. "Women-led" is self-declared and used only to route businesses to support programmes. A test checks that it can't change a score.

## Run the demo (no database or API keys needed)

```bash
pip install -r requirements.txt
uvicorn demo_main:app --port 8001
```

- Bank dashboard: http://localhost:8001/dashboard
- API docs: http://localhost:8001/docs
- Try `GET /credit/personas/hauwa` or `POST /credit/assess`

Demo personas (synthetic): **Hauwa** (maize farmer, Zaria), **Ngozi** (fabric trader, Onitsha), **Tunde** (garri processor, Abeokuta), **Bisi** (tomato seller, Mile 12, new with a thin file but strong àjọ), and **Musa** (struggling phone-accessories trader).

## Run the full WhatsApp bot

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
pytest
```

Environment variables are listed in `SPEC.md` section 1. The N-ATLAS server setup is in `natlas_server/README.md`.

## Repo layout

| Path | What it is |
| --- | --- |
| `app/credit/` | **Taproot credit engine:** features, scorecard, matching, demo data, dashboard, tests |
| `app/api/routes/credit.py` | Credit API and dashboard routes |
| `demo_main.py` | Stand-alone demo server |
| `app/trade/` | Voice sales book for traders (the main data source) |
| `app/services/`, `app/onboarding/`, `app/voice/` | WhatsApp, N-ATLAS voice pipeline, onboarding with consent |
| `app/agri/` | Farm advice calculators |
| `natlas_server/` | GPU server for N-ATLAS and ASR models |
| `docs/TAPROOT.md` | Product notes and hackathon roadmap |

## Built on

Taproot grows out of **AjaTrade**, our live voice-first WhatsApp assistant for farmers and traders. Language understanding and speech recognition run on **N-ATLAS**, Nigeria's open multilingual model (NCAIR / Awarri).
