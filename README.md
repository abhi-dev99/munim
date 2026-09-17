# Munim.ai
**The AI-Powered GST Compliance & Intelligence Layer for MSMEs**

![Munim.ai Dashboard](frontend/public/mockup.png) 
*(Note: Example dashboard showcasing the Uber-inspired Minimalist Light UI)*

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
