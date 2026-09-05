# 🏛️ Munim.ai

**The AI-Powered GST Compliance & Intelligence Layer for Indian MSMEs**

![Status](https://img.shields.io/badge/Status-Active-success)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20Supabase%20%7C%20LangGraph-orange)

![Munim.ai Dashboard](frontend/public/mockup.png) 
*(Note: Dashboard showcasing the Uber-inspired Minimalist Light UI)*

Munim.ai is not just another CA replacement. It is the intelligence layer between invoice receipt and CA reconciliation. Designed specifically for Indian MSMEs, Munim acts proactively to ensure you never lose Input Tax Credit (ITC) again due to non-compliant suppliers, HSN mismatches, or timing gaps.

## The Core Philosophy
Traditional accounting software requires manual data entry and reactive checking. Munim is **Proactive, Deterministic, and Multimodal**. 
- **The Trader Experience:** Entirely via WhatsApp. They take a photo, Munim does the rest.
- **The CA Experience:** A pristine, Uber-style high-contrast PWA dashboard that focuses entirely on action items, blocked capital, and supplier health.

## Key Features
- **WhatsApp First:** Zero app downloads required. Snap a photo of an invoice and send it to the Munim WhatsApp bot.
- **Multimodal AI Extraction:** Powered by Gemini 2.5 Flash, easily parsing crumpled, handwritten, and digital invoices.
- **Deterministic Rules Engine:** Pure logic implementation of GST Act Sections 16 & 17(5) to calculate exact eligible, blocked, and at-risk ITC.
- **GSTR-2B Reconciliation:** 3-pass fuzzy matching to reconcile incoming invoices against supplier filings.
- **Multi-Variate Fraud Scoring:** Proactive protection using Benford's Law, velocity anomalies, and geographic mismatch checks.
- **Supplier Health Monitoring:** Keep track of your suppliers' filing consistency and receive proactive alerts if they turn risky.

## Tech Stack
- **Backend:** FastAPI, LangGraph, Supabase, Redis (Upstash / Local)
- **Frontend:** Next.js (Turbopack), Tailwind CSS (Minimalist Light Mode)
- **AI / LLM:** Google Gemini API (gemini-2.5-flash)
- **Messaging:** Meta WhatsApp Cloud API

## Getting Started

### 1. Database Setup
Ensure you have a Supabase instance running. 
1. Run the `backend/schema.sql` to initialize your tables.
2. (Optional) Run `backend/scripts/seed_data.py` to populate mock traders and invoices.

### 2. Backend Environment
1. Clone the repository and navigate to `/backend`.
2. Copy `.env.example` to `.env` and fill in your Gemini, Supabase, and Redis keys.
3. Start the backend:
```bash
# Using Docker (requires docker daemon)
docker-compose up -d

# OR natively (if Redis is running elsewhere)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend Environment
1. Navigate to `/frontend`.
2. Configure `.env` if necessary (defaults to `http://localhost:8000`).
3. Start the UI:
```bash
npm install
npm run dev
```

Visit `http://localhost:3000` to view the pristine CA dashboard!
Visit `http://localhost:3000/trader` for the mobile Trader PWA.

---

## Production Deployment

### Backend → Railway
1. Push to GitHub (already done)
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub → Select `munim-ai` → Set **Root Directory** to `backend/`
3. Add a Redis service in Railway dashboard
4. Copy Railway's auto-generated Redis URL and set `UPSTASH_REDIS_URL` in your Railway env vars
5. Set all other env vars (Gemini key, Supabase, Meta tokens) in Railway → Variables
6. Railway auto-deploys on every push to `main`

**Your backend URL** will be: `https://your-app.up.railway.app`

### Frontend → Vercel
1. Go to [vercel.com](https://vercel.com) → New Project → Import `munim-ai` → Set **Root Directory** to `frontend/`
2. Add env var: `NEXT_PUBLIC_API_URL=https://your-app.up.railway.app`
3. Deploy — done in 2 minutes

### WhatsApp Webhook Setup
1. In Meta Developer Console → Your App → WhatsApp → Configuration
2. Set Webhook URL: `https://your-app.up.railway.app/api/v1/webhook`
3. Set Verify Token: `munim_verify_2026`
4. Subscribe to: `messages` field

---

## Architecture

```
Trader (WhatsApp) → Meta Cloud API
                          ↓
                    FastAPI Backend (Railway)
                          ↓
                    LangGraph Pipeline
                    ├── Gemini Vision → InvoiceJSON
                    ├── GSTIN Validator (deepvue.tech)
                    ├── HSN Validator (pgvector + Supabase)
                    ├── GSTR-2B Reconciler (3-pass fuzzy)
                    ├── ITC Rules Engine (GST Act 16/17(5))
                    └── Fraud Scorer (6 signals)
                          ↓
                    Supabase DB → CA Dashboard (Next.js/Vercel)
                    Redis (Upstash) → Session state + caching
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/webhook` | GET/POST | Meta WhatsApp webhook |
| `/api/v1/webhook/upload-invoice` | POST | Direct invoice upload (Trader PWA) |
| `/api/v1/dashboard/summary/{trader_id}` | GET | ITC summary |
| `/api/v1/dashboard/actions/{trader_id}` | GET | Prioritized action queue |
| `/api/v1/dashboard/actions/{id}/resolve` | PATCH | Mark issue resolved |
| `/api/v1/dashboard/suppliers/{trader_id}` | GET | Supplier health list |
| `/api/v1/dashboard/itc-timeline/{trader_id}` | GET | 6-month ITC chart data |
| `/api/v1/dashboard/reports/generate/{trader_id}` | POST | Generate PDF report |
| `/api/v1/gstr2b/upload-file/{trader_id}` | POST | Upload GSTR-2B JSON |

---

*Built for India's 64 million MSMEs. Every rupee of ITC matters.*
