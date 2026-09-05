# Munim.ai

**AI-Powered GST Compliance & ITC Intelligence for Indian MSMEs**

![Status](https://img.shields.io/badge/Status-Active-success)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20Supabase%20%7C%20Gemini-orange)
![License](https://img.shields.io/badge/License-MIT-green)
[![1st Runner-Up](https://img.shields.io/badge/KLEOS%204.0-1st%20Runner--Up-gold)](https://www.linkedin.com/posts/kleos4-raitacm-nationallevelhackathon-ugcPost-7475041562972880896-UpfR/)

> *Built for India's 64 million MSMEs. Every rupee of ITC matters.*

---

## What Is Munim.ai?

India's GST system is broken for small businesses. Chartered Accountants chase clients for crumpled paper invoices every month. Traders lose thousands in Input Tax Credit because their vendors forgot to file GSTR-1. Nobody finds out until it's too late to do anything about it.

**Munim.ai is a WhatsApp-first compliance co-pilot** that sits between invoice receipt and CA reconciliation. It extracts, validates, cross-checks, and flags — automatically — so the CA walks into month-end with a clean action queue instead of a pile of paper.

---

## Core USPs

### 1. WhatsApp-First — Zero App Download for Traders
Traders interact entirely via WhatsApp. Snap a photo of a bill, send it. That's it. No portals, no forms, no onboarding friction. The bot handles language detection (Hindi, English, Marathi, Gujarati) and responds in the same language. Onboarding a new trader takes under 2 minutes via guided conversational flow.

### 2. Multimodal AI Extraction (Gemini 2.5 Flash)
Invoices come in every format — crumpled thermal receipts, handwritten bills, scanned PDFs, blurry photos. Gemini Vision OCR extracts structured JSON from all of them: supplier name, GSTIN, invoice number, date, line items, HSN codes, tax breakdowns. Accuracy is validated on extraction; low-confidence extractions are flagged for human review.

### 3. Deterministic ITC Rules Engine (No LLM)
A pure rule-based engine implementing **GST Act Sections 16 and 17(5)**. Zero hallucination risk. It classifies every invoice into one of:
- `CONFIRMED` — ITC fully eligible
- `FIXABLE_BLOCKED` — Recoverable issue (e.g., HSN mismatch, wrong tax rate)
- `AT_RISK` — Vendor hasn't filed GSTR-1; ITC in danger
- `INELIGIBLE` — Hard-blocked under Section 17(5) (e.g., gym memberships, restaurant bills, personal vehicle expenses)
- `FRAUD_FLAGGED` — Composite fraud score ≥ 70

Blocked categories covered: motor vehicles, aircraft, beauty/health services, accommodation, outdoor catering, club memberships, real estate services, personal consumption items.

### 4. Six-Signal Fraud Scoring Engine
Every invoice is scored 0–100 using six independent, statistically-grounded signals:

| Signal | What It Detects |
|---|---|
| **GSTIN Age** | New GSTIN (<180 days) issuing high-value invoices |
| **Benford's Law** | Unnatural leading-digit distribution in invoice amounts (χ² test) |
| **Sequential Invoice Numbers** | Consecutive serial numbers from same supplier — a common fake invoice pattern |
| **Business Type Mismatch** | Supplier's GSTIN registration category contradicts what they're billing for |
| **Geographic Mismatch** | Supplier state ≠ buyer state without IGST being charged |
| **Velocity Anomaly** | Invoice amount >5× the supplier's historical average |

Score ≥ 70 → `FRAUD_FLAGGED` (manual CA review required). Score 40–69 → soft flag.

### 5. GSTR-2B Three-Pass Fuzzy Reconciliation
Reconciles trader invoices against the GSTR-2B JSON uploaded from the GST portal using a three-pass matching algorithm:
- **Pass 1 — Exact Match:** GSTIN + invoice number + date must all match precisely
- **Pass 2 — Fuzzy Match:** Levenshtein distance on invoice number (handles formatting differences like `INV-001` vs `INV001`), with ±2% amount tolerance and ±15-day date window
- **Pass 3 — Amount + Date:** Falls back to amount and date proximity if invoice number is ambiguous

Unmatched invoices are surfaced immediately in the Action Queue with vendor contact options.

### 6. Prioritized Action Queue
The CA dashboard surfaces a prioritized list of issues across all clients: fraud flags first, then ITC-at-risk, then fixable blocks. Each action item includes the exact reason, recommended fix, affected tax amount, and one-click vendor communication (WhatsApp or email warning sent directly from the platform).

### 7. Supplier Health Monitoring
Continuous scoring of each supplier's compliance history — GSTR-1 filing consistency, historical fraud flags, average response time to warnings. CAs can see which suppliers are chronically non-compliant and manage risk proactively across their entire portfolio.

### 8. Email Invoice Ingestion (Cloudmailin)
Every trader gets a dedicated Munim email address (e.g., `abc123@cloudmailin.net`) to share with vendors. Vendors can email invoices directly — PDFs are automatically parsed by the same Gemini pipeline and added to the trader's records. Closes the gap for suppliers who don't use WhatsApp.

### 9. Auto-Generated Compliance Reports (PDF)
One-click PDF report generation per trader per period, covering ITC summary, blocked amounts, at-risk credits, reconciliation status, and supplier health. Built for CA handoff and tax filing support.

### 10. GST Simulation (Interactive Demo)
A fully functional, data-driven GST portal simulation (replicating the real GST portal UI) with the IMS (Invoice Management System) and GSTR-3B auto-draft populated from actual backend data. The simulation is context-aware — it loads data for whichever trader or client is currently selected on the dashboard.

### 11. Real-Time Compliance Timeline
A visual calendar-style compliance tracker showing upcoming deadlines: GSTR-1 due dates, GSTR-2B upload windows, GSTR-3B filing deadlines. Traders and CAs get proactive WhatsApp reminders before each deadline.

### 12. Multi-Tenant CA Dashboard
A single CA can manage multiple trader clients from one dashboard. Client switching is instantaneous. All invoice records, action queues, supplier health data, and reports are isolated per trader. The dashboard is built as a PWA — works on mobile without installation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.12), LangGraph, Uvicorn |
| **Frontend** | Next.js 14 (App Router, Turbopack), Tailwind CSS |
| **Database** | Supabase (PostgreSQL + Row Level Security) |
| **AI / LLM** | Google Gemini 2.5 Flash (Vision + Text) |
| **Messaging** | Meta WhatsApp Cloud API |
| **Email Ingestion** | Cloudmailin (webhook-based) |
| **Session / Cache** | Redis (Upstash managed / local Docker) |
| **GSTIN Validation** | deepvue.tech API |
| **Fuzzy Matching** | python-Levenshtein |
| **PDF Generation** | WeasyPrint |
| **Deployment** | Railway (backend), Vercel (frontend) |

---

## Architecture

```
Trader (WhatsApp / Email)
         │
         ▼
Meta Cloud API / Cloudmailin Webhook
         │
         ▼
FastAPI Backend (Railway)
         │
    LangGraph Pipeline
    ├── 1. Gemini Vision OCR → InvoiceJSON
    ├── 2. GSTIN Validator (deepvue.tech)
    ├── 3. HSN Validator (pgvector + Supabase)
    ├── 4. ITC Rules Engine (GST Act §16 / §17(5))
    ├── 5. Fraud Scorer (6 signals, 0–100)
    └── 6. GSTR-2B Reconciler (3-pass fuzzy match)
         │
         ▼
Supabase PostgreSQL
         │
         ├── CA Dashboard (Next.js / Vercel)
         │     ├── Action Queue
         │     ├── Supplier Health
         │     ├── ITC Timeline
         │     ├── Reports Panel
         │     └── GST Simulation
         │
         └── Redis (Upstash)
               └── Session state / conversation context / caching
```

---

## Project Structure

```
munim-ai/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── webhook.py        # WhatsApp + onboarding bot
│   │   │   ├── dashboard.py      # CA dashboard data endpoints
│   │   │   ├── gstr2b.py         # GSTR-2B upload & reconciliation
│   │   │   ├── reports.py        # PDF report generation
│   │   │   ├── communications.py # WhatsApp/email vendor warnings
│   │   │   ├── email_webhook.py  # Cloudmailin email ingestion
│   │   │   └── auth.py           # JWT-based authentication
│   │   ├── domain/           # Core business logic (no LLM)
│   │   │   ├── itc_engine.py     # GST §16 / §17(5) rules engine
│   │   │   ├── fraud.py          # 6-signal fraud scorer
│   │   │   ├── reconciler.py     # 3-pass GSTR-2B reconciler
│   │   │   ├── hsn.py            # HSN code validator
│   │   │   └── supplier_monitor.py # Supplier health scoring
│   │   ├── models/           # Pydantic data models
│   │   └── services/         # Supabase client, WhatsApp API, Gemini
│   ├── schema.sql            # Full database schema
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/        # CA main dashboard
│   │   ├── trader/           # Trader PWA
│   │   └── components/       # Shared UI components
│   └── public/demo/          # GST simulation (standalone HTML/JS)
│
└── demo/                     # Symlinked demo for direct serving
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/webhook` | GET/POST | Meta WhatsApp webhook (verification + message handling) |
| `/api/v1/webhook/upload-invoice` | POST | Direct invoice upload from Trader PWA |
| `/api/v1/email-webhook` | POST | Cloudmailin inbound email → invoice pipeline |
| `/api/v1/dashboard/summary/{trader_id}` | GET | ITC summary card data |
| `/api/v1/dashboard/actions/{trader_id}` | GET | Prioritized action queue |
| `/api/v1/dashboard/actions/{id}/resolve` | PATCH | Mark action item resolved |
| `/api/v1/dashboard/suppliers/{trader_id}` | GET | Supplier health list |
| `/api/v1/dashboard/invoices/{trader_id}` | GET | Invoice records with filters |
| `/api/v1/dashboard/itc-timeline/{trader_id}` | GET | 6-month ITC chart data |
| `/api/v1/dashboard/reports/generate/{trader_id}` | POST | Generate and store PDF report |
| `/api/v1/gstr2b/upload-file/{trader_id}` | POST | Upload GSTR-2B JSON from GST portal |
| `/api/v1/gstr2b/reconcile/{trader_id}` | POST | Trigger reconciliation run |
| `/api/v1/gstr2b/records/{trader_id}` | GET | Fetch GSTR-2B records |

---

## Getting Started (Local)

### Prerequisites
- Python 3.12+
- Node.js 18+
- A Supabase project
- Google Gemini API key
- Meta WhatsApp Business API credentials (for bot testing)
- Redis (Docker or Upstash)

### 1. Database Setup
```bash
# Run the schema against your Supabase project
# (Supabase dashboard → SQL Editor → paste schema.sql)
```

### 2. Backend
```bash
cd backend
cp .env.example .env
# Fill in: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
#          REDIS_URL, META_ACCESS_TOKEN, META_PHONE_NUMBER_ID,
#          CLOUDMAILIN_SECRET, DEEPVUE_API_KEY

pip install -r requirements.txt
uvicorn app.main:app --reload
# OR with Docker:
docker-compose up -d
```

### 3. Frontend
```bash
cd frontend
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
```

- CA Dashboard: `http://localhost:3000/dashboard`
- Trader PWA: `http://localhost:3000/trader`
- GST Simulation: `http://localhost:3000/demo` (or open `frontend/public/demo/index.html`)

---

## Production Deployment

### Backend → Railway
1. New Project → Deploy from GitHub → select repo → Root Directory: `backend/`
2. Add Redis service from Railway marketplace
3. Set all env vars in Railway → Variables
4. Railway auto-deploys on every push to `main`

### Frontend → Vercel
1. New Project → Import repo → Root Directory: `frontend/`
2. Add env var: `NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app`
3. Deploy

### WhatsApp Webhook
In Meta Developer Console → WhatsApp → Configuration:
- Webhook URL: `https://your-railway-app.up.railway.app/api/v1/webhook`
- Verify Token: `munim_verify_2026`
- Subscribe to: `messages`

---

## Recognition

**1st Runner-Up — KLEOS 4.0, National Level Hackathon**
Ramrao Adik Institute of Technology (RAIT ACM), 2026
2000+ registrations · Top 40 teams on-site · 8 teams on the same problem statement

Judged on business viability, GST compliance depth, technical architecture, and cybersecurity considerations.

---

*Munim.ai — Because ITC lost is money lost.*
