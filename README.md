<div align="center">
  <h1>🧾 Munim.ai</h1>
  <p><b>WhatsApp-first, AI-driven GST compliance co-pilot for Indian SMEs and CAs</b></p>
</div>

## 📌 Overview

**Munim.ai** is an intelligent GST compliance platform designed to eliminate the manual bottleneck of invoice processing for Chartered Accountants (CAs) and SME traders. 

By leveraging **Gemini 2.5 Flash Vision** alongside a deterministic rule-based engine, Munim.ai allows traders to simply WhatsApp a photo of a bill and have it instantly extracted, verified, fraud-checked, and reconciled against the GSTR-2B auto-draft. No desktop portals, no steep learning curves—just seamless compliance on a platform traders already use.

## 🚀 Key Features

- **WhatsApp-First Ingestion**: Traders send bill photos, PDFs, or forwarded emails to a multilingual WhatsApp bot (Hindi, English, Marathi, Gujarati). 
- **AI Extraction & Classification**: Gemini 2.5 extracts structured JSON (supplier, GSTIN, HSN codes, tax breakdown) without requiring strict formatting.
- **Deterministic ITC Rules Engine**: A rigid, non-LLM Python engine applies GST Act Sections 16 and 17(5) to classify invoices as eligible, blocked, or at-risk.
- **6-Signal Fraud Detection**: Statistically scores invoices (0-100) using Benford's Law, sequential anomaly detection, geographic mismatch, and velocity anomalies. High scores are instantly escalated.
- **Automated GSTR-2B Reconciliation**: A 3-pass fuzzy matching algorithm instantly flags missing vendor filings to prevent Input Tax Credit (ITC) leakage.
- **1-Click CA Dashboard**: Centralized dashboard for CAs to manage 100+ clients, review fraud flags, and send automated WhatsApp/email warnings to non-compliant vendors.

## 🏗 Architecture & Stack

Munim.ai is orchestrated via a stateful **LangGraph** pipeline, ensuring each invoice passes through discrete, verifiable steps (Extraction → Validation → HSN Check → ITC Engine → Fraud Score → Reconciliation).

- **Backend**: FastAPI, LangGraph, Python 3.12
- **Frontend**: Next.js 14 (App Router), Tailwind CSS
- **Database & Auth**: Supabase (PostgreSQL + RLS)
- **AI & Vision**: Google Gemini 2.5 Flash Vision
- **Messaging Integration**: Meta WhatsApp Cloud API
- **Caching & State**: Redis (Upstash)

## ⚙️ How It Works

1. **Upload**: A trader sends an invoice image to the Munim WhatsApp number.
2. **Process**: LangGraph pipeline extracts data, validates the GSTIN via external APIs, and cross-matches HSN codes using pgvector.
3. **Analyze**: The ITC Rules Engine determines eligibility, while the statistical Fraud Scorer looks for anomalies.
4. **Reconcile**: The invoice is fuzzy-matched against portal JSON to ensure the vendor actually filed their returns.
5. **Action**: CAs review a centralized dashboard and trigger 1-click vendor warnings if discrepancies are found.

---
*Built to bridge the gap between complex tax regulations and the everyday realities of Indian SMEs.*
