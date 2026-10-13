# Taproot

**Credit rooted in how Nigerian SMEs really do business.**

Taproot is voice bookkeeping on WhatsApp that ends in a credit-ready record. Traders log sales by voice in Yoruba, Hausa, Igbo, Pidgin or English; every entry is read back and confirmed before it's saved; they get daily and weekly profit as voice notes. When they ask for a loan, Taproot summarises what their record supports and, with a separate consent, hands a one-page summary to a Zenith loan officer.

For Zenith, Taproot is a **customer acquisition and underwriting-data channel**: it reaches traders the bank can't reach today, builds a verified activity record, and gives loan officers structured decision support. **Taproot never approves or declines a loan; the credit decision is Zenith's.**

Built for **Zenith Bank Zecathon 6.0, Track 3: Smart SME Financing and Growth Platform.**

> A taproot is the deep root that reaches water in the dry season: the part you can't see that keeps the plant alive. Banks only see the surface (collateral, paperwork, statements). Taproot reaches down to the proof that's already there.

## Why

*(Illustrative story; Hauwa is a simulated persona, not a real customer.)* Hauwa trades grain in Zaria market. Right after harvest, prices are lowest and she could double her stock, but she has no cash. The bank wants statements she has never kept and forms in a language she doesn't read. She isn't a bad borrower; her business just has no record. Taproot gives it one.

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

### The trader flow (the demo)

1. First message → language and onboarding consent (store chats and phone number).
2. Set up goods: "Add 10 bags of rice, cost 45,000, sell 52,000".
3. Log a sale by voice: "I sold 3 bags of rice at 4,500 each" → read back in the trader's language → one-tap **Yes** before anything is saved. This stops a misheard ₦4,500 being stored as ₦45,000.
4. Daily and weekly profit voice notes.
5. **Ask for a loan** (menu row or just "I want a loan"): a voice summary of what the record supports, then a **separate loan-sharing consent** that names Zenith Bank and the purpose, can be withdrawn any time ("stop sharing"), and is stored with timestamp, language, channel and wording version (`credit_consents` table).
6. The Zenith loan officer receives the one-page summary (`GET /credit/officer/{wa_id}`, only with an active consent).

### How the summary is made

1. **Features** (`build_features`): months of records, average revenue and profit, margin, consistency, growth, restocking, àjọ discipline, bills, existing debt. Consistency is **season-aware for farmers**: a quiet dry season isn't treated as a red flag.
2. **Data trust** (`app/credit/trust.py`): self-reported books can be gamed, so Taproot checks how many days were logged and how steadily (60 steady days beat one big week), spikes, sales entered in bulk after the fact, margins outside a sane range, and **logged sales vs Zenith account inflows** where the trader has an account. The result is a trust level (high, medium or low) plus flags for the officer.
3. **Score** (`score`): a transparent scorecard covering logging habit, consistency, margin, trend, tenure, àjọ and bills, and existing debt. Every point comes with a reason an officer can read and a trader can hear. Bands are referral guidance, not decisions.
4. **Match** (`match`): the product that fits, mapped to the Zenith product it would be referred to. Repayments across all lenders stay within 30% of average monthly profit. The officer sees an **indicative loan-size band**, discounted when data trust is lower.
5. **Officer summary** (`officer_summary`): applicant, consent record, KYC status (BVN/NIN linked at application), record stats, trust flags, reasons, suggested product and band.
6. **Voice summary** (`voice_summary`): what the trader hears, with no promises; it states that Zenith makes the final decision.

**Fairness and inclusion:** gender, religion, ethnicity, state and age are never scoring inputs. Women dominate informal trade and the same flow serves them; `women_led` is self-declared, used only to point to Zenith's women's offer (Z-Woman) and to report outcomes for women separately. A test checks that it never changes the score.

**Compliance:** designed for the Nigeria Data Protection Act 2023 (purpose-specific, revocable, recorded consent) and CBN consumer-protection expectations. KYC (BVN/NIN) is done through Zenith's own process at application. The officer endpoint must sit behind the bank's staff authentication before any real deployment.

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
| `GET /credit/personas/{key}/officer` | The one-page loan officer summary (simulated persona) |
| `GET /credit/officer/{wa_id}` | Live officer summary; requires an active loan-sharing consent (full app only) |
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

- [x] WhatsApp "Ask for a loan" → record summary → separate loan-sharing consent → officer summary
- [x] Data-trust checks, including cross-checking against account inflows
- [ ] Read Zenith account inflows for consenting customers (currently passed in)
- [ ] BVN/NIN linking at application through Zenith's KYC
- [ ] Interview 5–10 traders about how they track money today; add their quotes to the pitch
- [ ] Consented data connectors: open banking statements, POS history, mobile money
- [ ] GenAI receipt and sales-book photo reading into ledger entries
- [ ] Àjọ group onboarding (group admin confirms members' contributions)
- [ ] Buyer and off-taker matching (growth agent)
- [ ] Recalibrate scorecard weights on pilot repayment outcomes; add a gradient-boosted challenger model with SHAP explanations

Rates and limits in `app/credit/matching.py` are illustrative placeholders; the Zenith product mapping (Small Business Loan, Z-Woman) must be confirmed against Zenith's current terms. **All demo data is simulated and labelled as simulated everywhere it appears.**

## Credits

Built on the AjaTrade voice engine. Language understanding, translation and speech recognition run on **N-ATLAS**, Nigeria's open multilingual model (NCAIR / Awarri).
