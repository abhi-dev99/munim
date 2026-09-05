# Munim.ai
**The AI-Powered GST Compliance & Intelligence Layer for MSMEs**

Munim.ai is not just another CA replacement. It is the intelligence layer between invoice receipt and CA reconciliation. Designed specifically for Indian MSMEs, Munim acts proactively to ensure you never lose Input Tax Credit (ITC) again due to non-compliant suppliers, HSN mismatches, or timing gaps.

## Features
- **WhatsApp First:** Zero app downloads required. Snap a photo of an invoice and send it to the Munim WhatsApp bot.
- **Multimodal AI Extraction:** Powered by Gemini 2.5 Flash, easily parsing crumpled, handwritten, and digital invoices.
- **Deterministic Rules Engine:** Pure logic implementation of GST Act Sections 16 & 17(5) to calculate exact eligible, blocked, and at-risk ITC.
- **GSTR-2B Reconciliation:** 3-pass fuzzy matching to reconcile incoming invoices against supplier filings.
- **Multi-Variate Fraud Scoring:** Proactive protection using Benford's Law, velocity anomalies, and geographic mismatch checks.
- **Supplier Health Monitoring:** Keep track of your suppliers' filing consistency and receive proactive alerts if they turn risky.

## Tech Stack
- **Backend:** FastAPI, LangGraph, Supabase, Redis (Upstash)
- **Frontend:** Next.js, Tailwind CSS (Glassmorphism design)
- **AI / LLM:** Google Gemini API
- **Messaging:** Meta WhatsApp Cloud API

## Getting Started
1. Clone the repository.
2. Setup the `.env` files in both backend and frontend directories based on the `.env.example` templates.
3. Apply the `schema.sql` to your Supabase instance.
4. Run `docker-compose up` to start the backend and Redis services.
5. In the `frontend` directory, run `npm install` and `npm run dev`.
