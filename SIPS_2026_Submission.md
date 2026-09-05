# Munim.ai — SIPS 2026 Submission
**Student Innovation & Product Summit | IIM Bangalore**
**Theme: AI & Intelligent Systems**

---

## 1. Problem Statement

India's GST system puts an enormous compliance burden on small businesses that are least equipped to handle it.

**The core problems:**

**For SME traders:**
Every month, they are required to maintain records of every purchase invoice, verify that their supplier filed the corresponding GSTR-1, reconcile that against the GSTR-2B auto-draft, and claim Input Tax Credit (ITC) before the filing deadline. Most traders have no idea this process exists. They hand paper bills to their CA at month-end and hope for the best.

**For Chartered Accountants:**
A typical CA manages 50–100 SME clients. 80% of their time is spent collecting documents — chasing WhatsApp messages, sorting crumpled photos, re-entering data manually. Actual GST analysis is a small fraction of what they do. They are bottlenecked by data collection, not analysis.

**The financial cost:**
India loses an estimated ₹1–2 lakh crore annually to ITC leakage — credits that businesses were entitled to but failed to claim due to compliance gaps, missed deadlines, supplier non-filing, and data entry errors. For an individual SME, this can mean lakhs of rupees left on the table every year.

**Why existing software fails:**
ClearTax, Tally, BUSY — all require the trader to learn a desktop portal. They require structured data input. They're reactive — they find problems at filing time, not when the invoice arrives. And they're built for accountants in English, not for a shopkeeper in Nashik.

---

## 2. Target Users

**Primary — Chartered Accountant Firms (The Buyer)**
- CA firms managing 20–200 SME clients
- Currently drowning in manual document collection and reconciliation
- Need a centralized view of all client compliance status in real-time
- Pain point: month-end crunch, ITC mismatches found too late to fix
- Willingness to pay: ₹2,000–₹10,000/month for a solution that saves them 40+ hours

**Secondary — SME Traders and Shop Owners (The End-User)**
- Small manufacturers, wholesalers, retailers, opticians, pharmacies, hardware stores
- GST-registered, actively buying from vendors and generating purchase invoices
- Largely non-English, non-tech-savvy
- Already on WhatsApp — no new behaviour to teach
- Tier 2 and Tier 3 cities: Nashik, Pune, Surat, Nagpur, Indore, Jaipur

**Tertiary — Individual Freelancers and Consultants**
- Self-employed GST registrants who deal with service invoices
- Need automated ITC tracking without hiring a full CA

---

## 3. Proposed Solution

Munim.ai is a WhatsApp-first, AI-driven GST compliance co-pilot.

**The trader's experience:**
They send any invoice to a WhatsApp bot — a photo, a PDF, a screenshot. The bot acknowledges it in their language, extracts all the data using AI, runs it through compliance checks, and confirms receipt. That's all they do. No login, no portal, no form.

**The CA's experience:**
They log into a clean dashboard showing all their clients' invoice data, already processed, already classified, already flagged. Instead of spending hours collecting and entering data, they spend 20 minutes reviewing flagged items, clicking to send vendor warnings where needed, and generating a compliance report.

**What happens in between (the intelligence layer):**

1. **AI Extraction** — Gemini 2.5 Flash Vision reads the invoice image/PDF and outputs structured JSON: supplier name, GSTIN, invoice number, date, each line item with HSN code and tax breakdown.

2. **GSTIN Validation** — The supplier's GSTIN is validated against a live API to confirm it's active and that the registration date, business category, and state code are consistent.

3. **ITC Rules Engine** — A deterministic, rule-based engine (no AI) applies GST Act Sections 16 and 17(5) to classify the invoice: fully eligible, partially eligible, blocked, or at-risk.

4. **Fraud Detection** — Six independent statistical signals are combined into a fraud score (0–100). Invoices scoring above 70 are automatically escalated for CA review.

5. **GSTR-2B Reconciliation** — When the CA uploads the monthly GSTR-2B JSON from the GST portal, the reconciler cross-matches all inward invoices using a three-pass algorithm. Unmatched invoices (vendor didn't file) are immediately flagged with vendor contact options.

6. **Automated Vendor Communication** — CAs can send WhatsApp or email warnings to non-compliant vendors directly from the dashboard with a single click.

---

## 4. Prototype Overview

The prototype is fully functional end-to-end. All flows described below are live and testable.

### Flow A: Trader Invoice Submission (WhatsApp)
1. Trader sends a bill photo to the Munim WhatsApp number
2. Bot detects language, acknowledges in same language (Hindi/English/Marathi/Gujarati)
3. Gemini Vision extracts invoice data
4. ITC engine classifies it; fraud scorer runs
5. Bot responds with result: "Your bill from [Supplier] for ₹X has been recorded. ITC of ₹Y is eligible."
6. If blocked: bot explains why in plain language. If fraud flagged: CA is notified.

### Flow B: Trader Onboarding (WhatsApp)
Guided conversational onboarding that collects business name, GSTIN (validated live), and language preference. Takes under 2 minutes. At completion, trader receives their dedicated Munim email address for vendor invoice forwarding.

### Flow C: Email Invoice Ingestion
Vendors can email invoices directly to the trader's dedicated Cloudmailin address. PDFs are automatically parsed through the same Gemini pipeline and added to records without any manual action.

### Flow D: CA Dashboard
- **Action Queue**: Prioritized issues across all clients — fraud flags, ITC-at-risk items, fixable blocks. Each item shows the affected amount and recommended action.
- **Supplier Health**: Visual scoring of each vendor's compliance track record.
- **Invoice Records**: Searchable, filterable log of all processed invoices with status indicators.
- **GSTR-2B Upload**: Drag-and-drop JSON upload that triggers the reconciliation engine.
- **Reports**: One-click PDF compliance report generation.
- **Compliance Timeline**: Visual deadline tracker with upcoming GSTR-1, GSTR-2B, GSTR-3B dates.

### Flow E: GST Portal Simulation
An interactive simulation of the GST portal's IMS (Invoice Management System) populated with the actual trader's real invoice data. Demonstrates how Munim's output maps directly to the government filing interface, and how GSTR-3B values are auto-calculated from accepted/rejected credits.

### Live Demo
- CA Dashboard: `https://munim-ai.vercel.app/dashboard`
- Trader PWA: `https://munim-ai.vercel.app/trader`
- GitHub: `https://github.com/abhi-dev99/munim-ai`

---

## 5. Technical Architecture

### System Overview

```
Trader (WhatsApp / Email)
         │
         ▼
Meta Cloud API / Cloudmailin Webhook
         │
         ▼
FastAPI Backend (Python 3.12)
         │
    LangGraph Agentic Pipeline
    ├── 1. Gemini 2.5 Flash Vision → InvoiceJSON
    ├── 2. GSTIN Validator (deepvue.tech API)
    ├── 3. HSN Validator (pgvector similarity search)
    ├── 4. ITC Rules Engine (GST §16 / §17(5)) — no LLM
    ├── 5. Fraud Scorer (6-signal composite, 0–100) — no LLM
    └── 6. GSTR-2B Reconciler (3-pass fuzzy match) — no LLM
         │
         ▼
Supabase PostgreSQL + Row Level Security
         │
         ├── Next.js Dashboard (Vercel)
         └── Redis (Upstash) — Session & conversation state
```

### Key Technical Components

**LangGraph Pipeline**
The invoice processing flow is orchestrated as a stateful LangGraph graph. Each node is a discrete, testable step. Failures at any node are caught and surfaced with appropriate status rather than silently dropping invoices.

**ITC Rules Engine (itc_engine.py)**
Pure Python rule-based implementation. Section 17(5) blocked categories are matched by HSN prefix (e.g., `8703` for passenger vehicles, `9963` for health/fitness services) and by keyword matching on description. Section 16(2) conditions (invoice received, tax paid, return filed, possession of goods) are checked against available metadata. No LLM is in this path — deterministic by design.

**Fraud Scoring Engine (fraud.py)**
Six signals, each weighted and bounded:
| Signal | Weight | Method |
|---|---|---|
| GSTIN Age | 20 | Registration date vs. invoice date |
| Benford's Law | 15 | Chi-squared test on leading digit distribution |
| Sequential Invoices | 15 | Consecutive number detection |
| Business Mismatch | 15 | Category vs. line item cross-check |
| Geographic Mismatch | 15 | State code from GSTIN prefix |
| Velocity Anomaly | 20 | Z-score against supplier historical average |

**GSTR-2B Reconciler (reconciler.py)**
Three-pass algorithm using Levenshtein distance for invoice number matching, ±2% amount tolerance, and ±30-day date windows. Confidence scores are assigned per match quality (1.0 for exact, 0.7–0.9 for fuzzy, 0.5 for amount+date only). Unmatched invoices → `AT_RISK` status.

**Multilingual WhatsApp Bot (webhook.py)**
Session state maintained in Redis per phone number. Language detected on first message and stored. All bot responses are templated in English, Hindi, Marathi, and Gujarati. Conversation state machine handles: new user → onboarding flow → invoice submission → status queries.

**Database Schema (Supabase)**
Core tables: `traders`, `invoices`, `gstr2b_records`, `action_items`, `supplier_profiles`, `reports`. Row Level Security policies ensure CAs only see their assigned traders. Supabase Auth used for CA login.

### Stack Summary

| Layer | Technology |
|---|---|
| Backend | FastAPI, LangGraph, Python 3.12 |
| Frontend | Next.js 14 (App Router), Tailwind CSS |
| Database | Supabase (PostgreSQL + RLS) |
| AI | Google Gemini 2.5 Flash |
| Messaging | Meta WhatsApp Cloud API |
| Email Ingestion | Cloudmailin |
| Caching | Redis (Upstash) |
| GSTIN Validation | deepvue.tech |
| Fuzzy Matching | python-Levenshtein |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## 6. Expected Impact

**Immediate (for early adopters):**
- A CA managing 50 clients currently spends ~20 hours/month on document collection. Munim reduces this to near-zero — invoices arrive processed, classified, and flagged automatically.
- ITC recovery rate improves because issues are flagged within hours of invoice receipt, not at month-end when it's too late to fix vendor non-filing.
- Fraud detection catches fake invoice schemes before ITC is claimed — protecting businesses from GST department scrutiny and penalties.

**Market Scale:**
- India has 63 million registered MSMEs and ~300,000 practicing CAs
- Average CA manages 30–80 clients
- Even at 1% CA adoption at ₹3,000/month → ₹90 crore ARR opportunity
- ITC leakage in India is estimated at ₹1–2 lakh crore annually — every percentage point recovered is massive value

**Societal:**
- Reduces the compliance burden on Tier 2/3 business owners who currently pay CAs just to do data entry
- Makes GST compliance accessible to first-generation business owners who don't speak financial jargon or English
- Levels the playing field between organized retail (which has full accounting teams) and small traders

**Technology Demonstration:**
- Proves that multimodal AI + deterministic rules can replace manual professional work in regulated domains — without needing the AI to "hallucinate" legal interpretations
- The separation of AI (extraction) from rules-based logic (compliance classification) is a design pattern applicable broadly to legal, tax, and regulatory domains

---

## 7. Team Details

**Team Code0710**
1st Runner-Up — KLEOS 4.0 National Level Hackathon, RAIT ACM (2026)
2000+ registrations · Top 40 on-site · Panel of 6 judges across business, compliance, tech, and cybersecurity

**Abhishek** — Full Stack & AI Integration
Backend architecture, LangGraph pipeline, Gemini Vision integration, WhatsApp bot, GSTR-2B reconciliation engine, fraud scoring system, CA dashboard frontend.

*Institution: [Your College Name]*
*GitHub: https://github.com/abhi-dev99*

> **Note:** Team size may be updated to include additional members. This document reflects the core builder of the prototype.

---

*Submitted under Theme: **AI & Intelligent Systems***
*File name format: `Code0710_AI.pdf`*
