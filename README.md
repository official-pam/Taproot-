# Taproot

**Credit rooted in how Nigerian SMEs really do business.**

Taproot is a voice-first AI platform on WhatsApp that turns a small business's everyday records into fair, explainable credit. It reads sales, restocks, àjọ/esusu contributions, bill payments and mobile-money inflows (all shared with consent), then scores the business and matches it to financing it can actually repay. Owners speak in Yoruba, Hausa, Igbo, Pidgin or English and get answers back as voice notes. They don't need an app, forms or English.

Built for **Zenith Bank Zecathon 6.0, Track 3: Smart SME Financing and Growth Platform.**

> A taproot is the deep root that reaches water in the dry season: the part you can't see that keeps the plant alive. Banks only see the surface (collateral, paperwork, statements). Taproot reaches down to the proof that's already there.

## Why

Hauwa farms maize outside Zaria. When the rains come she has about two weeks to plant and fertilize. The bank wanted collateral, statements and English forms. By the time she gave up, the window had closed. She isn't a credit risk; she's invisible to the system. Taproot makes her visible, and gets her the money before the rain does.

## What's in this repo

| Part | Where | Status |
| --- | --- | --- |
| WhatsApp bot, voice notes, onboarding with consent, 5 languages (N-ATLAS) | `app/services`, `app/onboarding`, `app/voice`, `natlas_server/` | Live (inherited from AjaTrade) |
| Sales book: sales, restocks, profit, stock, "record for a loan" PDF | `app/trade/` | Live |
| Farm advice: crop diagnosis, soil, fertilizer, irrigation | `app/agri/`, `app/services/advisor/` | Live |
| **Credit features** from ledger + alternative data | `app/credit/features.py` | New |
| **Explainable scorecard** (300–850, bands A–E, plain-language reasons) | `app/credit/scoring.py` | New |
| **Product matching and loan sizing** by affordability | `app/credit/matching.py` | New |
| **Credit API and bank officer dashboard** | `app/api/routes/credit.py`, `app/credit/dashboard.html` | New |
| Synthetic personas and a 300-SME demo portfolio | `app/credit/demo.py` | New |

### How a decision is made

1. **Features** (`build_features`): months of records, average revenue and profit, margin, consistency, growth, restocking, àjọ discipline, bills, existing debt. Consistency is **season-aware for farmers**: a quiet dry season isn't treated as a red flag.
2. **Score** (`score`): each factor adds or removes points and leaves a reason a credit officer can read and an owner can hear. A thin file (under 3 months) is capped at band D, so it can reach an àjọ group loan or credit builder but nothing bigger.
3. **Match** (`match`): picks the best product for the business type and band. Monthly repayments across all lenders stay within 30% of average monthly profit. Seasonal input loans are repaid once from half of expected harvest profit.
4. **Voice summary** (`voice_summary`): a short reply translated and spoken by the existing N-ATLAS pipeline.

**Fairness:** gender, religion, ethnicity, state and age are never scoring inputs. `women_led` is self-declared and used only to route businesses to support programmes. A test checks that it never changes the score.

## Run the demo (no database or WhatsApp needed)

```bash
pip install -r requirements.txt
uvicorn demo_main:app --reload --port 8001
```

Open http://localhost:8001/dashboard for the bank view, or http://localhost:8001/docs for the API.

| Endpoint | What it does |
| --- | --- |
| `POST /credit/assess` | Score any business from its records and alternative data |
| `GET /credit/personas` | The five demo businesses (Hauwa, Ngozi, Tunde, Bisi, Musa) |
| `GET /credit/personas/{key}` | Full assessment plus the voice note it would receive |
| `GET /credit/portfolio` | Bank pipeline: bands, pre-qualified value, women-led share |
| `GET /dashboard` | Credit officer dashboard |

## Run the full bot

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
pytest
```

Environment variables are listed in `SPEC.md` section 1; the N-ATLAS server setup is in `natlas_server/README.md`. The credit routes are mounted in the full app too.

## Hackathon roadmap

- [ ] WhatsApp flow: "Check my loan" menu row → `assess()` on the user's ledger → voice summary → YES to apply
- [ ] Consented data connectors: open banking statements, POS history, mobile money
- [ ] GenAI receipt and sales-book photo reading into ledger entries
- [ ] Àjọ group onboarding (group admin confirms members' contributions)
- [ ] Buyer and off-taker matching (growth agent)
- [ ] Recalibrate scorecard weights on pilot repayment outcomes; add a gradient-boosted challenger model with SHAP explanations

Product names, rates and limits in `app/credit/matching.py` are illustrative placeholders, to be replaced with the partner bank's real products. All demo data is synthetic.

## Credits

Built on the AjaTrade voice engine. Language understanding, translation and speech recognition run on **N-ATLAS**, Nigeria's open multilingual model (NCAIR / Awarri).
