# Munim.ai

**WhatsApp-first GST compliance co-pilot for Indian MSMEs**

![Status](https://img.shields.io/badge/Status-Active-success)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20Supabase%20%7C%20Gemini-orange)
![License](https://img.shields.io/badge/License-Proprietary-red)

Traders forward invoices via WhatsApp. Munim extracts, validates, fraud-checks, and reconciles them automatically. CAs get a clean dashboard instead of a pile of paper.

---

## What It Does

- **WhatsApp Invoice Ingestion** — Photo, PDF, or email. No app download. 4 languages (Hindi, English, Marathi, Gujarati)
- **Gemini Vision OCR** — Extracts structured data from handwritten bills, thermal receipts, and scanned PDFs
- **ITC Rules Engine** — Deterministic GST Act §16/§17(5) classification. No LLM in this path. Zero hallucination risk
- **6-Signal Fraud Scorer** — Benford's Law, velocity anomaly, sequential invoices, geo-mismatch, GSTIN age, business mismatch → composite 0–100 score
- **GSTR-2B Reconciliation** — 3-pass fuzzy matching (exact → Levenshtein → amount+date) against GST portal JSON upload
- **Action Queue** — Prioritized issues per client with one-click WhatsApp/email vendor warnings
- **Supplier Health** — Tracks vendor GSTR-1 filing consistency across months
- **Email Ingestion** — Dedicated Cloudmailin address per trader for vendor invoice forwarding
- **PDF Reports** — One-click compliance report generation per trader per period
- **GST Simulation** — Interactive IMS + GSTR-3B auto-draft demo populated from live backend data

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, LangGraph, Python 3.12 |
| Frontend | Next.js 14, Tailwind CSS |
| Database | Supabase (PostgreSQL + RLS) |
| AI | Google Gemini 2.5 Flash |
| Messaging | Meta WhatsApp Cloud API |
| Email | Cloudmailin |
| Cache | Redis (Upstash) |
| Deploy | Railway (backend) + Vercel (frontend) |

---

## Architecture

```
Trader (WhatsApp / Email)
    → Meta API / Cloudmailin Webhook
    → FastAPI + LangGraph Pipeline
        ├── Gemini Vision OCR
        ├── GSTIN Validator
        ├── ITC Rules Engine  (no LLM)
        ├── Fraud Scorer      (no LLM)
        └── GSTR-2B Reconciler (no LLM)
    → Supabase DB
    → Next.js CA Dashboard (Vercel)
    → Redis (session + conversation state)
```

---

## Setup

### Backend
```bash
cd backend
cp .env.example .env   # fill in keys
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

- Dashboard: `http://localhost:3000/dashboard`
- Trader PWA: `http://localhost:3000/trader`

### Database
Run `backend/schema.sql` against your Supabase project.

---

## Key API Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/v1/webhook` | WhatsApp message handler |
| `POST /api/v1/email-webhook` | Cloudmailin inbound email |
| `GET /api/v1/dashboard/actions/{trader_id}` | Prioritized action queue |
| `GET /api/v1/dashboard/suppliers/{trader_id}` | Supplier health |
| `POST /api/v1/gstr2b/upload-file/{trader_id}` | GSTR-2B JSON upload |
| `POST /api/v1/gstr2b/reconcile/{trader_id}` | Trigger reconciliation |
| `POST /api/v1/dashboard/reports/generate/{trader_id}` | PDF report |

---

## Deployment

- **Backend → Railway**: Root dir `backend/`, add Redis service, set env vars
- **Frontend → Vercel**: Root dir `frontend/`, set `NEXT_PUBLIC_API_URL`
- **WhatsApp Webhook**: `https://your-backend/api/v1/webhook`, verify token in `.env`

---

*© 2026 Abhishek Saraf. All rights reserved. See LICENSE.*
