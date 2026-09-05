# Munim.ai — Complete Technical Specification & Agent Handoff Document
**Version:** 1.0  
**Hackathon:** Kleos 4.0 — D.Y. Patil RAIT, Navi Mumbai  
**Problem Statement:** D4-PS1 — "The CA in Your Pocket That Does Not Exist" (AI/ML Domain)  
**Last Updated:** June 2026  

---

## Table of Contents
1. [Project Vision & Positioning](#1-project-vision--positioning)
2. [Target Market & User Personas](#2-target-market--user-personas)
3. [Use Case Definitions & Workflow Maps](#3-use-case-definitions--workflow-maps)
4. [System Architecture](#4-system-architecture)
5. [Complete Feature Specification](#5-complete-feature-specification)
6. [Tech Stack — Detailed Breakdown](#6-tech-stack--detailed-breakdown)
7. [Service Setup & Free Tier Reference](#7-service-setup--free-tier-reference)
8. [Database Schema](#8-database-schema)
9. [Kafka Topic Definitions](#9-kafka-topic-definitions)
10. [LangGraph Agent Specifications](#10-langgraph-agent-specifications)
11. [n8n Workflow Definitions](#11-n8n-workflow-definitions)
12. [WhatsApp Bot Conversation Flows](#12-whatsapp-bot-conversation-flows)
13. [Web Dashboard Specification](#13-web-dashboard-specification)
14. [Domain Logic Specifications](#14-domain-logic-specifications)
15. [Demo Script](#15-demo-script)
16. [Build Priority & Implementation Order](#16-build-priority--implementation-order)
17. [Environment Variables Template](#17-environment-variables-template)
18. [Open Assumptions & Gaps](#18-open-assumptions--gaps)

---

## 1. Project Vision & Positioning

### What Munim.ai Is
Munim.ai is the **world's first autonomous GST compliance agent designed for India's informal economy traders** — not for chartered accountants, not for enterprises, but for the kirana owner in Lucknow who gets 800 invoices a month on WhatsApp and pays ₹35,000/month to a CA who spends 90% of that time on data entry.

The word *munim* is the traditional Hindi/Urdu term for a business accountant or bookkeeper. We're not building software. We're building the munim that runs 24/7, never sleeps, speaks Hindi, lives on WhatsApp, and finds money the trader didn't know they were losing.

### The Core Insight
Every existing GST reconciliation tool (ClearTax, Vyapar, GSTHero, Suvit) is built **for CAs and finance teams**. Complex interfaces, English-only, ERP-first, desktop-first. The CA is the customer.

Munim.ai inverts this. The **trader is the customer**. The CA is a beneficiary. The system does everything a CA does for data processing — extraction, validation, reconciliation, diagnosis — and hands the CA only the items that genuinely need human judgment. CA's monthly workload per client: 3 weeks → 3 hours. Trader's CA bill: ₹35,000 → ₹8,000.

### What Makes It Not a GPT Wrapper
The LLM (Gemini 2.5 Flash) does exactly two things:
1. **Entity extraction** from messy invoice images (multimodal vision)
2. **Hindi explanation generation** from structured verdict JSON

Everything between ingestion and explanation is deterministic, rule-based domain logic:
- Image preprocessing pipeline (OpenCV)
- GSTR-2B fuzzy matching algorithm (custom)
- ITC computation rules engine (Section 16 & 17(5) GST Act)
- HSN 2.0 validation over 12,167 codes + pgvector semantic matching
- Real-time GSTIN verification with Redis caching
- Multi-variate fraud signal scoring
- Supplier compliance graph with state-change detection

Remove the LLM and swap in any other multimodal model — none of the compliance logic changes. The intelligence is in the domain layer, not the model.

---

## 2. Target Market & User Personas

### Market Size
- **1.4 crore GST-registered MSMEs** in India
- ~60% (84 lakh) are in the "compliance-struggling" bracket: formally registered but regularly missing ITC or filing incorrectly
- Average unclaimed/blocked ITC per MSME per year: ₹50,000 (conservative estimate)
- Total addressable unclaimed ITC: **₹7,000 crore annually**

### Primary Persona: Raju (The Trader)
- Kirana/grocery store owner, textile merchant, hardware supplier, or small manufacturer
- Annual turnover: ₹40 lakh – ₹5 crore
- Invoice volume: 100–2,000/month (mix of WhatsApp images, printed receipts, digital PDFs)
- Pays CA: ₹15,000–₹40,000/month
- Tech comfort: Smartphone-native, WhatsApp-heavy, limited English, no accounting knowledge
- Pain: Has no idea how much ITC he's missing or why he gets GST notices
- Behavior: He will not download an app. He will not learn new software. He lives on WhatsApp.

### Secondary Persona: CA Sharma (The Accountant)
- Small CA firm, 20–100 MSME clients
- Spends 70% of time per client on manual data entry and reconciliation
- Would benefit from a pre-processed "filing brief" that reduces his work to judgment calls only
- Not a direct customer — a beneficiary and potential distribution channel

### What Munim.ai Does For Each
| | Raju (Trader) | CA Sharma |
|---|---|---|
| **Input effort** | Forward invoice to WhatsApp number | Receive Munim Report on 1st |
| **Output received** | Hindi diagnosis + action within 30 sec | CA-ready filing brief, issues flagged |
| **Money impact** | Recovers ₹50K+/year in missed ITC | Serves 5x clients, bills more |
| **Learning curve** | Zero (already on WhatsApp) | Zero (PDF in email/WhatsApp) |

---

## 3. Use Case Definitions & Workflow Maps

### UC-01: Real-Time Invoice Processing (Primary, Event-Triggered)

```
Trigger: Trader sends invoice image/PDF to WhatsApp bot

FLOW:
[Trader] → [WhatsApp] → [Meta Cloud API Webhook]
    → [FastAPI /webhook endpoint]
    → publishes → [Kafka: munim.invoice.received]
    → consumed by → [LangGraph: InvoiceProcessingAgent]
        Node 1: Preprocess image (OpenCV)
        Node 2: OCR (PaddleOCR → Gemini Vision for fallback)
        Node 3: Extract structured JSON (Gemini)
        Node 4: GSTIN validation (Redis cache → GSTIN API)
        Node 5: HSN validation (HSN DB + pgvector semantic match)
        Node 6: GSTR-2B fuzzy matching
        Node 7: ITC computation (Rules Engine)
        Node 8: Fraud signal scoring
        Node 9: Diagnosis generation (Gemini → Hindi)
    → publishes → [Kafka: munim.invoice.processed]
    → consumed by → [NotificationWorker]
        → WhatsApp reply to trader (Hindi)
        → Supabase DB insert
        → Supabase Realtime broadcast → Next.js dashboard live update

Target latency: < 30 seconds end-to-end
```

### UC-02: Continuous Supplier Monitoring (Scheduled, n8n-Triggered)

```
Trigger: n8n cron — every day at 09:00 IST

FLOW:
[n8n: SupplierMonitorWorkflow]
    → Fetches all unique supplier GSTINs from Supabase
    → For each GSTIN:
        → Check Redis cache (hit → use cached state)
        → Cache miss → call GSTIN Verification API → cache result
    → Detect state transitions:
        - Active+Filing → Active+Not Filed  →  ALERT: missed_filing
        - Active → Cancelled               →  ALERT: gstin_cancelled
        - Regular → Composition            →  ALERT: scheme_switch (ITC blocked)
        - Filing streak broken > 2 months  →  ALERT: erratic_filer
        - GSTIN age < 180 days + high value →  ALERT: new_gstin_risk
    → For each alert: publish to [Kafka: munim.supplier.alert]
    → consumed by → [NotificationWorker]
        → WhatsApp alert to all affected traders (Hindi)
        → Update supplier health score in Supabase
        → Invalidate Redis cache entry for changed GSTIN
```

### UC-03: Month-End Compliance Package (Scheduled, n8n-Triggered)

```
Trigger: n8n cron — 1st of every month at 08:00 IST

FLOW:
[n8n: MunimReportWorkflow]
    → Fetches all traders from Supabase
    → For each trader: publishes [Kafka: munim.report.requested]
    → consumed by → [LangGraph: ReportGenerationAgent]
        Node 1: Pull all processed invoices for month from Supabase
        Node 2: Run GSTR-2B reconciliation (month-end full pass)
        Node 3: Compute ITC summary (Eligible, Blocked, At-Risk, Missed)
        Node 4: Run historical leak analysis (6-month delta)
        Node 5: Generate CA-ready filing brief (Gemini)
        Node 6: Render Munim Report PDF (WeasyPrint)
    → publishes → [Kafka: munim.report.ready]
    → consumed by → [NotificationWorker]
        → Send PDF via WhatsApp to trader
        → Send PDF via WhatsApp to trader's registered CA (if set)
        → Store in Supabase Storage
```

### UC-04: Filing Deadline Alert (Scheduled, n8n-Triggered)

```
Trigger: n8n cron — 5th, 10th, and 18th of every month

FLOW:
[n8n: DeadlineAlertWorkflow]
    → Fetches all traders with unresolved ITC issues from Supabase
    → Calculates days to filing deadline (11th for GSTR-1, 20th for GSTR-3B)
    → Generates personalized alert:
        "Filing deadline in X days. You have Y unresolved issues 
         blocking ₹Z in ITC. Fix these before [date] or lose the credit."
    → Sends via WhatsApp (Hindi)
```

---

## 4. System Architecture

### High-Level Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                          │
│                                                                  │
│  WhatsApp → Meta Cloud API → FastAPI Webhook Gateway             │
│                              (/api/v1/webhook)                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ publish
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EVENT BUS (Upstash Kafka)                   │
│                                                                  │
│  Topics:                                                         │
│  munim.invoice.received    munim.invoice.processed               │
│  munim.supplier.alert      munim.report.requested                │
│  munim.report.ready        munim.deadline.alert                  │
└──────┬─────────────────────────────┬────────────────────────────┘
       │ consume                     │ consume
       ▼                             ▼
┌─────────────────┐       ┌──────────────────────────────────────┐
│   LangGraph     │       │         NOTIFICATION WORKER           │
│   Agents        │       │                                       │
│                 │       │  → WhatsApp reply (Meta Cloud API)    │
│  InvoiceAgent   │       │  → Supabase insert                    │
│  ReportAgent    │       │  → Supabase Realtime broadcast        │
└────────┬────────┘       └──────────────────────────────────────┘
         │ read/write
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
│                                                                  │
│  Supabase PostgreSQL    Supabase Realtime    Supabase Storage    │
│  pgvector (HSN index)   (WebSocket)          (invoice images,    │
│                                               Munim Reports)     │
│                                                                  │
│  Upstash Redis                                                   │
│  (GSTIN cache, session state, rate limiting)                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ live push
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js PWA)                        │
│                                                                  │
│  Money Meter   Supplier Health   ITC Timeline   Munim Report     │
│  (live)        Dashboard         (Recharts)      Preview         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│               WORKFLOW ORCHESTRATION (n8n, self-hosted)          │
│                                                                  │
│  SupplierMonitorWorkflow (daily 09:00)                           │
│  DeadlineAlertWorkflow (5th, 10th, 18th)                         │
│  MunimReportWorkflow (1st of month)                              │
│                                                                  │
│  All workflows publish to Kafka → consumed by workers above      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                EXTERNAL APIs (all free/cheap)                    │
│                                                                  │
│  Gemini 2.5 Flash (vision + text + audio)                        │
│  Meta WhatsApp Cloud API (messaging)                             │
│  GSTIN Verification API (Eko/Deepvue — cached aggressively)      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Event bus | Upstash Kafka | Decouples ingestion from processing; shows distributed systems knowledge |
| Agent orchestration | LangGraph | Stateful directed graph; enterprise-grade; not a chain |
| HSN matching | pgvector semantic search | Handles ambiguous descriptions dictionary-lookup can't |
| Scheduling | n8n (self-hosted) | Production-grade workflow orchestration, not cron scripts |
| Caching | Upstash Redis | GSTIN lookups cached permanently, invalidated on state change |
| Real-time | Supabase Realtime | WebSocket live dashboard without custom WebSocket server |
| Frontend generation | Lovable / v0.dev | AI-generated UI shell; human engineering time saved for hard parts |
| Model | Gemini 2.5 Flash | Free tier, multimodal (vision + audio), Hindi-native, 10 RPM free |
| WhatsApp | Meta Cloud API (direct) | Free test mode, no Twilio middleman, no daily limit on user-initiated messages |

---

## 5. Complete Feature Specification

### Layer 1: Ingestion Pipeline

**F-01 — WhatsApp Omni-Ingestion**
- Bot accepts: JPEG/PNG invoice photos, PDF invoices, forwarded WhatsApp images
- Webhook endpoint receives media, downloads from Meta CDN, stores in Supabase Storage
- Publishes `munim.invoice.received` event with media URL + trader ID

**F-02 — Multimodal OCR Pipeline**
- Stage 1: OpenCV preprocessing (deskew, denoise, contrast normalization, threshold)
- Stage 2: PaddleOCR for mixed Hindi-English text extraction
- Stage 3: Gemini 2.5 Flash Vision for semantic entity extraction from OCR text
- Extracts: GSTIN (supplier + buyer), invoice number, date, line items, HSN codes, tax amounts, totals
- Outputs structured `InvoiceJSON` schema

**F-03 — Voice Note Input**
- Trader sends WhatsApp voice note describing an invoice
- Gemini 2.5 Flash processes audio natively (no Whisper needed)
- Transcribed text combined with any attached media for processing
- Hindi voice input fully supported

**F-04 — Conversation State Management**
- Redis stores per-trader conversation state (current invoice in process, awaiting clarification, etc.)
- LangGraph maintains cross-session memory of trader's supplier network and historical patterns
- Bot maintains context: "Remember Ramesh's oil invoice from Tuesday? He filed today. Your ₹2,400 ITC is now confirmed."

---

### Layer 2: Validation Engine

**F-05 — Live GSTIN Validation**
- Every GSTIN on every invoice (supplier + buyer) validated via GSTIN Verification API
- Returns: active status, legal name, taxpayer type, registration date, filing history, e-invoice mandate flag
- Results cached permanently in Redis; cache invalidated only on supplier monitoring state-change detection
- Invalid/cancelled GSTIN → immediate hard alert, invoice flagged as ITC-ineligible

**F-06 — HSN 2.0 Validation Engine**
- Full 12,167-code HSN 2.0 database loaded into Supabase PostgreSQL
- Each HSN code also embedded via Gemini embedding API and stored in pgvector index
- Validation flow:
  1. Extract HSN code from invoice
  2. Exact lookup in HSN DB → valid/invalid
  3. If valid: check tax rate on invoice vs correct rate for code → match/mismatch
  4. If invalid or rate mismatch: run pgvector semantic search on line item description → suggest correct code
  5. Compute ITC delta: (correct rate - applied rate) × invoice amount
- Output: `HSNValidationResult` with status, suggested correct code, ITC impact in ₹

**F-07 — Tax Rate Verification**
- Cross-check GST rate on invoice against official rate for validated HSN code
- Handles: 0%, 5%, 12%, 18%, 28% slabs + cess
- Flags: overpaid tax (supplier error), underpaid tax (compliance risk for buyer)

**F-08 — Duplicate Invoice Detection**
- Hash: SHA-256 of (supplier GSTIN + invoice number + invoice date)
- Check against `invoice_hashes` table in Supabase
- Duplicate detected → alert trader, do not process for ITC
- Handles WhatsApp forwarding loops (same invoice forwarded multiple times)

**F-09 — GSTR-2B Fuzzy Reconciliation Engine**
- Loads trader's GSTR-2B export (CSV/Excel — trader uploads once/month, or dummy for demo)
- Matching algorithm:
  - **Pass 1 (Exact):** GSTIN + invoice number exact match → `MATCHED`
  - **Pass 2 (Fuzzy):** GSTIN exact + invoice number Levenshtein ≤ 2 + amount within ±2% + date within 30 days → `PROBABLE_MATCH` (confidence scored)
  - **Pass 3 (Amount+Date):** GSTIN exact + amount within ±1% + date within 15 days → `POSSIBLE_MATCH` (flagged for review)
  - **Unmatched:** Invoice in trader records not in GSTR-2B → `ITC_AT_RISK`
  - **Orphaned:** Invoice in GSTR-2B not in trader records → `MISSED_ITC` (money left unclaimed)
- All MISSED_ITC items surfaced as immediate action items with ₹ value

---

### Layer 3: Supplier Intelligence Network

**F-10 — Supplier Compliance Graph**
- Directed graph: Trader → [Supplier GSTIN, Supplier GSTIN, ...]
- Built automatically from processed invoice history
- Stored in Supabase (suppliers table + supplier_trader_links junction)
- Daily refresh via n8n SupplierMonitorWorkflow

**F-11 — Supplier Behavioral Flags**
Full taxonomy of flags assigned per supplier GSTIN:

| Flag | Condition | Alert |
|---|---|---|
| `MISSED_FILING` | GSTR-1 or GSTR-3B not filed in current month | ITC from this supplier at risk for current month |
| `HABITUAL_LATE` | Consistently files 5+ days after deadline (last 3 months) | Expect ITC in next month's GSTR-2B, not current |
| `ERRATIC_FILER` | Filing consistency score < 70% over 6 months | High reliability risk; ITC unpredictable |
| `ITC_GHOST` | Invoices never appear in trader's GSTR-2B for 3+ months | Possible fake invoice / circular trading ring |
| `GSTIN_CANCELLED` | GSTIN registration cancelled | All future invoices from this supplier invalid for ITC |
| `SCHEME_SWITCH` | Switched from Regular Taxpayer to Composition Dealer | ITC from this supplier is permanently blocked |
| `EINVOICE_NON_COMPLIANT` | Turnover > ₹5Cr but not generating IRN | Invoice may be invalid; ITC claim risky |
| `CANCELLATION_RISK` | 2+ consecutive missed filings + prior quality rating drop | Pre-emptive warning before GSTIN goes dark |
| `NEW_GSTIN_RISK` | GSTIN age < 180 days + invoice value > ₹50,000 | Elevated fraud probability; extra scrutiny |
| `SECTOR_RISK` | Business category in high-fraud sectors (iron/steel scrap, textiles, chemicals, construction) | Baseline fraud premium applied |

**F-12 — Supplier Health Score**
- Score 0–100 per supplier, recomputed daily
- Weighted inputs: filing consistency (40%), GSTIN age (15%), flag count (30%), sector risk (15%)
- Leaderboard on dashboard: green/yellow/red status per supplier
- Actionable: "Stop accepting invoices from suppliers with score < 40 until they resolve compliance"

**F-13 — ITC Risk Alerts (Proactive)**
- WhatsApp alert the moment a supplier's state changes adversely
- Message example (Hindi): "Sharma Trading ne pichhle 60 din se GST return nahi bhara. Aapka ₹8,600 ITC khatre mein hai. Unhe payment karne se pehle yeh issue resolve karein."
- Actionable: "Yahan click karein apne CA ko alert bhejne ke liye" (tap to forward Munim Report to CA)

---

### Layer 4: Financial Intelligence

**F-14 — ITC Money Meter (Live Dashboard)**
- Five real-time buckets:
  - **Confirmed ITC:** Supplier filed, records match, safe to claim
  - **Fixable Blocked ITC:** HSN error, rate error — can be corrected before filing
  - **At-Risk ITC:** Supplier hasn't filed — claim exists but could be denied
  - **Missed ITC:** Invoices in GSTR-2B not in trader's books — unclaimed money
  - **Ineligible ITC:** Section 17(5) blocked categories
- All buckets show ₹ amounts, click for drill-down to individual invoices
- Updates live via Supabase Realtime websocket — no refresh needed

**F-15 — Historical ITC Leak Analysis**
- Using 6 months of synthetic/historical data (demo: seeded; production: real history)
- Shows: month-by-month ITC claimed vs ITC eligible
- Highlights: "In the last 6 months, you missed ₹87,400 in recoverable ITC"
- Breakdown by error type: HSN mismatches, supplier non-compliance, unrecorded invoices

**F-16 — ITC Cash Flow Calendar**
- Month-by-month forecast of expected ITC credits
- Shows when ITC will hit the Electronic Credit Ledger (post-filing, typically 20th+)
- Flags: "₹8,600 of next month's expected ITC depends on Sharma Trading filing by the 13th — currently unresolved"

**F-17 — Priority Action Queue**
- All open issues sorted by ₹ impact descending
- Trader sees: "Fix issue #1 (₹14,400) → Fix issue #2 (₹8,600) → Fix issue #3 (₹2,400)"
- Each issue has: what's wrong, which invoice, what to tell CA, deadline

**F-18 — Industry Benchmark Score**
- Anonymized aggregate across all Munim traders in same sector
- "Traders like you recover 71% of eligible ITC on average. You're at 43%."
- Gamified: progress bar toward benchmark, monthly delta

---

### Layer 5: Fraud Detection

**F-19 — Multi-Variate Fraud Scoring**
Six independent signals, weighted into a composite fraud score (0–100):

| Signal | Detection | Method |
|---|---|---|
| GSTIN Age | New GSTINs issuing high-value invoices | Registration date from API → age in days |
| Benford's Law | Non-natural leading digit distribution in amounts | Statistical test on invoice amount dataset |
| Sequential Invoice Numbers | Fake invoices often use sequential numbers across "different" vendors | Group by GSTIN, sort invoice numbers, check gaps |
| Business Type Mismatch | Supplier registered as IT services billing for construction materials | GSTIN business category vs invoice line items (Gemini classification) |
| Geographic Mismatch | Supplier GSTIN state ≠ delivery state with no interstate flag | State code from GSTIN chars 1–2 vs invoice delivery address |
| Velocity Anomaly | Invoice amounts suddenly 10x supplier's historical average | Running average per supplier GSTIN over 6 months |

- Fraud score ≥ 70 → hard flag, manual review required before ITC claim
- Fraud score 40–70 → soft flag, highlighted on dashboard
- Fraud score < 40 → auto-processed

**F-20 — Circular Invoice Pattern Detection**
- Detect if same invoice value appears across multiple different supplier GSTINs within same week
- Flag potential round-tripping or invoice recycling

---

### Layer 6: CA Handoff

**F-21 — Munim Report (Auto-Generated Monthly PDF)**
Generated on 1st of month by LangGraph ReportGenerationAgent. Contains:
- Section 1: Executive Summary (total ITC, confirmed/blocked/at-risk breakdown)
- Section 2: Issues Requiring CA Action (sorted by ₹ impact)
- Section 3: All Processed Invoices (categorized, with validation status)
- Section 4: GSTR-2B Reconciliation Summary
- Section 5: Supplier Health Report (flagged suppliers, recommended actions)
- Section 6: GSTR-3B Pre-fill Data (net ITC to claim, adjustments required)
- Rendered as PDF via WeasyPrint; delivered via WhatsApp to trader + CA

**F-22 — CA Collaboration Portal**
- Separate authenticated view in the Next.js PWA
- CA sees: all their registered trader clients, each trader's open issues, resolved items
- CA can: mark issues as resolved, add notes, export filing data
- Audit trail: every change timestamped and attributed

---

## 6. Tech Stack — Detailed Breakdown

### Backend
| Component | Technology | Purpose |
|---|---|---|
| API Gateway | **FastAPI** (Python 3.11+) | WhatsApp webhook, REST APIs, health endpoints |
| Agent Orchestration | **LangGraph** (Python) | Stateful multi-agent workflows |
| Workflow Automation | **n8n** (self-hosted, Docker) | Scheduled jobs: supplier monitoring, deadline alerts, report triggers |
| Image Preprocessing | **OpenCV** (Python) | Deskew, denoise, threshold before OCR |
| OCR | **PaddleOCR** | Mixed Hindi-English invoice text extraction |

### AI / ML
| Component | Technology | Purpose |
|---|---|---|
| Primary LLM | **Gemini 2.5 Flash** (Google AI API) | Invoice vision extraction, Hindi generation, audio transcription |
| Embeddings | **Gemini Embeddings API** | HSN code semantic vectors for pgvector |
| Semantic Search | **pgvector** (in Supabase) | Nearest-neighbour HSN code matching from line item descriptions |
| Fraud Scoring | **Custom Python** (scikit-learn optional) | Multi-variate signal computation, Benford's law test |

### Messaging
| Component | Technology | Purpose |
|---|---|---|
| WhatsApp Interface | **Meta WhatsApp Cloud API** (direct) | Receive invoices, send Hindi responses, deliver reports |
| Webhook | FastAPI POST /api/v1/webhook | Receives Meta webhook events |

### Event Infrastructure
| Component | Technology | Purpose |
|---|---|---|
| Event Bus | **Upstash Kafka** | Decoupled event streaming between ingestion, processing, notification |
| Cache | **Upstash Redis** | GSTIN lookup cache, conversation state, rate limiting |

### Database
| Component | Technology | Purpose |
|---|---|---|
| Primary DB | **Supabase PostgreSQL** | All relational data (traders, invoices, suppliers, reports) |
| Vector DB | **pgvector** (Supabase extension) | HSN code embeddings for semantic search |
| Real-time | **Supabase Realtime** | WebSocket push for live dashboard updates |
| File Storage | **Supabase Storage** | Invoice images, Munim Report PDFs |

### Frontend
| Component | Technology | Purpose |
|---|---|---|
| Framework | **Next.js 14** (App Router) | PWA — responsive on mobile + desktop |
| UI Generation | **Lovable** or **v0.dev** | Rapid UI shell generation (focus engineering time on hard parts) |
| Charts | **Recharts** | ITC timeline, supplier health visualizations |
| Styling | **Tailwind CSS** | Utility-first, consistent with Lovable output |
| Real-time client | **Supabase JS client** | WebSocket subscription for live Money Meter |

### Report Generation
| Component | Technology | Purpose |
|---|---|---|
| PDF Rendering | **WeasyPrint** (Python) | Munim Report PDF generation from HTML template |

### Infrastructure
| Component | Technology | Purpose |
|---|---|---|
| Local tunnel | **ngrok** | Expose local FastAPI to Meta webhook (hackathon) |
| Deployment | **Railway** (free $5 credit) or local + ngrok | FastAPI + n8n containers |
| Containerisation | **Docker + Docker Compose** | Local development environment |

---

## 7. Service Setup & Free Tier Reference

### Gemini 2.5 Flash (Google AI Studio)
- **Free tier:** 10 RPM, 250,000 TPM, 1,500 RPD
- **Covers:** Invoice vision, audio transcription, Hindi text generation, embeddings
- **Note:** Data used to improve Google models on free tier (acceptable for India demo)
- **Setup:** https://aistudio.google.com → Get API Key → save as `GEMINI_API_KEY`
- **Cost at hackathon scale:** ₹0

### Meta WhatsApp Cloud API
- **Setup path:** developers.facebook.com → Create App → Business → Add WhatsApp product
- **Test mode:** Provides test phone number immediately, no business verification needed
- **Test limits:** 5 pre-registered recipient numbers; unlimited replies to user-initiated messages within 24-hour window
- **Demo strategy:** Judge texts the bot first → unlimited replies, no rate limit applies
- **Cost:** Free in test mode; production service conversations ₹0 for first 1000/month
- **Setup time:** ~45 minutes

### Upstash Kafka
- **Free tier:** Effectively pay-as-you-go; $0.20/100K messages single-zone
- **Hackathon cost:** <500 messages total → < $0.01 → effectively ₹0
- **Setup:** upstash.com → Create Kafka cluster → Get bootstrap URL + credentials
- **Note:** Use single-zone (cheaper); multi-zone unnecessary for hackathon

### Upstash Redis
- **Free tier:** 500,000 commands/month, 256MB data, 10GB bandwidth
- **Hackathon usage:** GSTIN cache hits, session state → well under 500K commands
- **Cost:** ₹0

### Supabase
- **Free tier:** 500MB database, 2GB bandwidth, 50MB file storage, Realtime included
- **Setup:** supabase.com → New Project → save URL + anon key + service role key
- **pgvector:** Enable via SQL: `CREATE EXTENSION IF NOT EXISTS vector;`
- **Cost:** ₹0

### GSTIN Verification API
- **Providers:** Eko Platform, Deepvue, Masters India
- **Pricing:** ~₹0.50–₹0.72 per verification
- **Hackathon strategy:** Cache ALL results in Redis permanently. Pre-seed ~30 supplier GSTINs at startup. Live-verify only genuinely new GSTINs during demo. Mock the rest.
- **Expected cost:** < ₹50 for entire hackathon

### n8n (Self-Hosted)
- **Community Edition:** Completely free, no limits on workflows, executions, or users
- **Deploy:** Docker container alongside FastAPI
- **Cost:** ₹0

### PaddleOCR
- **License:** Apache 2.0, fully open source
- **Runs locally** inside FastAPI container
- **Cost:** ₹0

### WeasyPrint
- **License:** BSD, fully open source
- **Runs locally** inside FastAPI container
- **Cost:** ₹0

### Total Expected Cost for Hackathon
**₹50–₹100 max (GSTIN API calls only, if not mocked)**

---

## 8. Database Schema

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Traders (primary users)
CREATE TABLE traders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_number VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(255),
    gstin VARCHAR(15) UNIQUE,
    business_name VARCHAR(255),
    language_pref VARCHAR(10) DEFAULT 'hi', -- 'hi' or 'en'
    ca_whatsapp_number VARCHAR(15), -- registered CA for Munim Report delivery
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Suppliers (unique per GSTIN, shared across traders)
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gstin VARCHAR(15) UNIQUE NOT NULL,
    legal_name VARCHAR(255),
    trade_name VARCHAR(255),
    taxpayer_type VARCHAR(50), -- Regular, Composition, etc.
    registration_date DATE,
    business_category VARCHAR(255),
    is_einvoice_mandated BOOLEAN DEFAULT FALSE,
    health_score INTEGER DEFAULT 100, -- 0-100, recomputed daily
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supplier-Trader relationships (the compliance graph)
CREATE TABLE supplier_trader_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    first_invoice_date DATE,
    last_invoice_date DATE,
    total_invoice_count INTEGER DEFAULT 0,
    total_itc_claimed DECIMAL(15,2) DEFAULT 0,
    UNIQUE(trader_id, supplier_id)
);

-- Supplier behavioral flags
CREATE TABLE supplier_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL, -- see F-11 taxonomy
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    metadata JSONB, -- additional context per flag type
    is_active BOOLEAN DEFAULT TRUE
);

-- Processed invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id),
    
    -- Raw data
    image_url TEXT, -- Supabase Storage URL
    raw_ocr_text TEXT,
    
    -- Extracted fields
    invoice_number VARCHAR(100),
    invoice_date DATE,
    gstin_supplier VARCHAR(15),
    gstin_buyer VARCHAR(15),
    
    -- Financial
    taxable_amount DECIMAL(15,2),
    cgst_amount DECIMAL(15,2),
    sgst_amount DECIMAL(15,2),
    igst_amount DECIMAL(15,2),
    total_amount DECIMAL(15,2),
    
    -- Validation status
    status VARCHAR(50) DEFAULT 'pending', 
    -- pending | processing | validated | flagged | error
    
    itc_status VARCHAR(50),
    -- CONFIRMED | FIXABLE_BLOCKED | AT_RISK | MISSED | INELIGIBLE | FRAUD_FLAGGED
    
    itc_amount_eligible DECIMAL(15,2),
    itc_amount_blocked DECIMAL(15,2),
    itc_block_reason TEXT,
    
    -- Reconciliation
    gstr2b_match_status VARCHAR(50),
    -- MATCHED | PROBABLE_MATCH | POSSIBLE_MATCH | ITC_AT_RISK | MISSED_ITC | UNRECONCILED
    gstr2b_match_confidence DECIMAL(5,2),
    
    -- Fraud scoring
    fraud_score INTEGER DEFAULT 0, -- 0-100
    fraud_signals JSONB, -- breakdown of which signals fired
    
    -- Hash for duplicate detection
    invoice_hash VARCHAR(64) UNIQUE,
    
    -- Processing metadata
    processed_at TIMESTAMPTZ,
    processing_duration_ms INTEGER,
    langgraph_run_id VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoice line items
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT,
    hsn_code_extracted VARCHAR(10), -- what was on the invoice
    hsn_code_validated VARCHAR(10), -- what it should be (after validation)
    hsn_is_valid BOOLEAN,
    hsn_suggestion VARCHAR(10), -- pgvector semantic match suggestion
    hsn_confidence DECIMAL(5,2), -- similarity score
    quantity DECIMAL(15,3),
    unit VARCHAR(20),
    unit_price DECIMAL(15,2),
    taxable_value DECIMAL(15,2),
    tax_rate_applied DECIMAL(5,2), -- rate on invoice
    tax_rate_correct DECIMAL(5,2), -- correct rate for HSN
    rate_mismatch BOOLEAN DEFAULT FALSE,
    itc_delta DECIMAL(15,2) -- ₹ impact of rate mismatch
);

-- HSN Master (12,167 codes)
CREATE TABLE hsn_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hsn_code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    description_hindi TEXT, -- Hindi translation (where available)
    gst_rate DECIMAL(5,2) NOT NULL,
    category VARCHAR(100),
    section VARCHAR(100),
    -- pgvector embedding of description for semantic search
    embedding vector(768) -- Gemini embedding dimension
);

-- Create HNSW index for fast approximate nearest neighbour search
CREATE INDEX hsn_embedding_idx ON hsn_codes 
USING hnsw (embedding vector_cosine_ops);

-- GSTR-2B Imports (monthly uploads)
CREATE TABLE gstr2b_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    month INTEGER NOT NULL, -- 1-12
    year INTEGER NOT NULL,
    supplier_gstin VARCHAR(15),
    invoice_number VARCHAR(100),
    invoice_date DATE,
    taxable_value DECIMAL(15,2),
    igst DECIMAL(15,2),
    cgst DECIMAL(15,2),
    sgst DECIMAL(15,2),
    itc_eligible BOOLEAN DEFAULT TRUE,
    matched_invoice_id UUID REFERENCES invoices(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trader_id, month, year, supplier_gstin, invoice_number)
);

-- Munim Reports (monthly PDF)
CREATE TABLE munim_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pdf_url TEXT, -- Supabase Storage URL
    
    -- Summary stats
    total_invoices_processed INTEGER,
    total_itc_confirmed DECIMAL(15,2),
    total_itc_blocked DECIMAL(15,2),
    total_itc_at_risk DECIMAL(15,2),
    total_itc_missed DECIMAL(15,2),
    total_itc_ineligible DECIMAL(15,2),
    total_issues_count INTEGER,
    
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_to_trader_at TIMESTAMPTZ,
    delivered_to_ca_at TIMESTAMPTZ,
    
    UNIQUE(trader_id, month, year)
);

-- WhatsApp conversation state (Redis-backed, this table for persistence)
CREATE TABLE conversation_states (
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE PRIMARY KEY,
    state VARCHAR(50) DEFAULT 'idle',
    -- idle | awaiting_invoice | processing | awaiting_clarification
    current_invoice_id UUID REFERENCES invoices(id),
    context JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id),
    event_type VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. Kafka Topic Definitions

| Topic | Producer | Consumer | Schema |
|---|---|---|---|
| `munim.invoice.received` | FastAPI webhook | LangGraph InvoiceAgent | `{trader_id, media_url, media_type, message_id, timestamp}` |
| `munim.invoice.processed` | LangGraph InvoiceAgent | NotificationWorker | `{trader_id, invoice_id, itc_status, itc_amount, diagnosis_hi, diagnosis_en, action_required}` |
| `munim.supplier.alert` | n8n SupplierMonitor | NotificationWorker | `{supplier_id, trader_ids[], flag_type, alert_message_hi, itc_at_risk_amount}` |
| `munim.report.requested` | n8n MunimReport | LangGraph ReportAgent | `{trader_id, month, year}` |
| `munim.report.ready` | LangGraph ReportAgent | NotificationWorker | `{trader_id, report_id, pdf_url, summary}` |
| `munim.deadline.alert` | n8n DeadlineAlert | NotificationWorker | `{trader_id, filing_type, days_remaining, blocked_itc_amount, alert_message_hi}` |

---

## 10. LangGraph Agent Specifications

### Agent 1: InvoiceProcessingAgent

**Graph Definition:**
```python
# Nodes (each is a Python function / async function)
nodes = [
    "preprocess_image",      # OpenCV: deskew, denoise, threshold
    "run_ocr",               # PaddleOCR → raw text
    "extract_entities",      # Gemini Vision → InvoiceJSON
    "validate_gstin",        # GSTIN API (Redis cache → API)
    "validate_hsn",          # HSN DB exact + pgvector fallback
    "reconcile_gstr2b",      # Fuzzy matching algorithm
    "compute_itc",           # Rules engine (Section 16 & 17(5))
    "score_fraud",           # Multi-variate scoring
    "generate_diagnosis",    # Gemini → Hindi + English diagnosis
    "handle_error",          # Error recovery node
]

# Edges (conditional)
edges = {
    "preprocess_image": "run_ocr",
    "run_ocr": "extract_entities",
    "extract_entities": conditional(
        if extraction_failed → "handle_error",
        else → "validate_gstin"
    ),
    "validate_gstin": conditional(
        if gstin_invalid → "generate_diagnosis",  # short-circuit with fraud signal
        else → "validate_hsn"
    ),
    "validate_hsn": "reconcile_gstr2b",
    "reconcile_gstr2b": "compute_itc",
    "compute_itc": "score_fraud",
    "score_fraud": "generate_diagnosis",
    "generate_diagnosis": END,
    "handle_error": END,
}

# State schema
class InvoiceAgentState(TypedDict):
    trader_id: str
    media_url: str
    raw_image: bytes
    preprocessed_image: bytes
    ocr_text: str
    invoice_json: dict
    gstin_validation: dict
    hsn_validations: list
    gstr2b_match: dict
    itc_computation: dict
    fraud_score: int
    fraud_signals: dict
    diagnosis_hi: str
    diagnosis_en: str
    action_items: list
    error: Optional[str]
```

**Key Node: `extract_entities` (Gemini Vision)**
```python
# Prompt template for Gemini
EXTRACTION_PROMPT = """
You are a GST invoice parser for India. Extract ALL fields from this invoice image.
Return ONLY valid JSON matching this exact schema. No prose. No markdown.

Schema:
{
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "gstin_supplier": "15-char GSTIN or null",
  "gstin_buyer": "15-char GSTIN or null",
  "supplier_name": "string",
  "line_items": [
    {
      "description": "string",
      "hsn_code": "string or null",
      "quantity": number,
      "unit": "string",
      "unit_price": number,
      "taxable_value": number,
      "cgst_rate": number,
      "sgst_rate": number,
      "igst_rate": number,
      "cgst_amount": number,
      "sgst_amount": number,
      "igst_amount": number
    }
  ],
  "total_taxable_amount": number,
  "total_tax_amount": number,
  "total_amount": number,
  "confidence": number  // 0.0-1.0 extraction confidence
}
"""
```

**Key Node: `validate_hsn` (pgvector semantic search)**
```python
async def validate_hsn(state: InvoiceAgentState) -> InvoiceAgentState:
    for item in state["invoice_json"]["line_items"]:
        hsn = item.get("hsn_code")
        
        # Exact lookup
        result = await db.fetchrow(
            "SELECT hsn_code, description, gst_rate FROM hsn_codes WHERE hsn_code = $1",
            hsn
        )
        
        if not result:
            # Semantic search: embed description → find nearest HSN
            embedding = await gemini.embed(item["description"])
            result = await db.fetchrow("""
                SELECT hsn_code, description, gst_rate,
                       1 - (embedding <=> $1) as similarity
                FROM hsn_codes
                ORDER BY embedding <=> $1
                LIMIT 1
            """, embedding)
            item["hsn_suggestion"] = result["hsn_code"]
            item["hsn_confidence"] = result["similarity"]
            item["hsn_is_valid"] = False
        else:
            item["hsn_is_valid"] = True
            # Check rate mismatch
            applied_rate = item["cgst_rate"] + item["sgst_rate"] + item["igst_rate"]
            if abs(applied_rate - result["gst_rate"]) > 0.1:
                item["rate_mismatch"] = True
                item["tax_rate_correct"] = result["gst_rate"]
                item["itc_delta"] = (result["gst_rate"] - applied_rate) / 100 * item["taxable_value"]
    
    return state
```

### Agent 2: ReportGenerationAgent

**Graph Definition:**
```
nodes: [
    "fetch_month_data",
    "run_reconciliation",
    "compute_itc_summary",
    "analyze_historical",
    "generate_ca_brief",
    "render_pdf",
    "store_and_notify"
]
```

---

## 11. n8n Workflow Definitions

### Workflow 1: SupplierMonitorWorkflow (Daily 09:00 IST)

```
Nodes:
1. Cron Trigger (daily 09:00 IST)
2. HTTP Request → Supabase REST API → fetch all unique supplier GSTINs
3. Split In Batches (batch size: 20, to respect API rate limits)
4. Function Node → For each GSTIN: check Redis cache
5. HTTP Request → GSTIN Verification API (only cache misses)
6. Function Node → Detect state transitions vs cached state
7. IF Node → state change detected?
   YES:
   8a. HTTP Request → Upstash Kafka → publish munim.supplier.alert
   8b. HTTP Request → Supabase → update supplier record + health score
   8c. HTTP Request → Upstash Redis → invalidate cache entry → set new state
   NO:
   8d. HTTP Request → Upstash Redis → refresh cache TTL
9. Error Handler → log failures to Supabase audit_log
```

### Workflow 2: DeadlineAlertWorkflow (5th, 10th, 18th of month)

```
Nodes:
1. Cron Trigger (5th, 10th, 18th at 10:00 IST)
2. HTTP Request → Supabase → fetch traders with unresolved ITC issues
3. Function Node → Compute days to deadline (11th for GSTR-1, 20th for GSTR-3B)
4. Function Node → Generate personalized Hindi alert message per trader
5. HTTP Request → Upstash Kafka → publish munim.deadline.alert for each trader
```

### Workflow 3: MunimReportWorkflow (1st of month, 08:00 IST)

```
Nodes:
1. Cron Trigger (1st of month 08:00 IST)
2. HTTP Request → Supabase → fetch all active traders
3. Split In Batches (batch size: 10)
4. HTTP Request → Upstash Kafka → publish munim.report.requested per trader
5. Wait 30 seconds
6. Error Handler → check for failed report generations, retry
```

---

## 12. WhatsApp Bot Conversation Flows

### Flow 1: New Invoice Received

```
USER: [sends invoice image]

BOT: "Invoice mil gaya! Processing ho raha hai... ek minute."
     [30-second processing]

CASE A — All Clear:
BOT: "✅ Invoice sahi hai!
     
     📄 Ramesh Trading | ₹10,000
     HSN Code: 1511 ✓ (Cooking Oil — sahi)
     GST Rate: 5% ✓
     ITC: ₹476.19 confirmed
     
     Aapka yeh credit agli filing mein mil jayega."

CASE B — Fixable Issue:
BOT: "⚠️ Ek chhoti problem mili.

     📄 Ramesh Trading | ₹10,000
     ❌ HSN Code galat: 3407 likha hai (Shaving Cream)
        Sahi code: 1511 (Cooking Oil)
     
     💸 Iss galti ki wajah se ₹400 ka ITC BLOCK ho raha hai.
     
     🔧 Kya karein: Apne CA ko bolo — 'Ramesh ka invoice, 
     HSN 3407 ki jagah 1511 karna hai.'
     
     Yeh fix ho sakta hai filing se pehle."

CASE C — Supplier Risk:
BOT: "🚨 Dhyan dein!

     📄 Sharma Trading | ₹50,000
     ⚠️ Sharma Trading ne pichhle 2 mahine se GST 
        return nahi bhara.
     
     💸 Agar aap ITC claim karte hain: ₹2,380 REJECT 
        ho sakta hai agle mahine.
     
     Abhi kya karein: Inhe payment mat karo jab tak 
     yeh compliance issue resolve na ho."

CASE D — Fraud Flag:
BOT: "🚫 Suspicious invoice!

     Score: 78/100 (High Risk)
     ❌ GSTIN sirf 45 din purana
     ❌ ₹50,000 ki invoice — iss supplier ki average 
        sirf ₹5,000 thi
     
     Apne CA se verify karwao pehle. ITC claim mat karo 
     abhi tak."
```

### Flow 2: Registration

```
USER: "Hi" / "Hello" / "Namaste"

BOT: "Namaste! Main Munim hun — aapka GST compliance agent.
     
     Main aapke invoices check karta hun, ITC track karta hun, 
     aur aapke CA ke liye monthly report banata hun.
     
     Shuru karte hain — aapka GST number kya hai?"

USER: [GSTIN]

BOT: "Perfect! [Business Name] — register ho gaye.
     
     Ab bas karo: jab bhi koi invoice aaye — WhatsApp pe 
     yahan bhej do. Main baaki sab handle karunga.
     
     Aaj tak ke invoices bhejne shuru karo!"
```

### Flow 3: Dashboard Check

```
USER: "kitna ITC hai" / "status" / "dashboard"

BOT: "📊 Is mahine ka ITC status:

     ✅ Confirmed ITC: ₹41,200
     ⚠️ Blocked ITC: ₹8,600 (3 issues — fix ho sakte hain)
     🚨 At-Risk ITC: ₹12,400 (2 suppliers ne return nahi bhara)
     💰 Missed ITC: ₹3,200 (2 invoices GSTR-2B mein hain 
        jo aapne enter nahi kiye)
     
     ➡️ Total recovery possible: ₹24,200
     
     Dashboard ke liye: [link to PWA]
     
     Sabse badi problem pehle fix karein — kya chaiye details?"
```

---

## 13. Web Dashboard Specification

### Page 1: Money Meter (Home)

**Live components (Supabase Realtime):**
- Circular gauge: Total ITC eligible this month (center number updates live)
- Four stacked bars: Confirmed / Blocked / At-Risk / Missed (color-coded)
- Alert ribbon: "3 urgent issues — ₹8,600 at stake — file by 20th"
- Quick stats row: Invoices processed | Suppliers monitored | Issues open

**Action panel:**
- Priority Action Queue (sorted by ₹ descending)
- Each item: [What's wrong] [Which invoice] [₹ impact] [What to tell CA] [Deadline]

### Page 2: Supplier Health Dashboard

**Components:**
- Supplier list with health score (0–100) colored red/yellow/green
- Flags visible per supplier (badges: LATE_FILER, ERRATIC, CANCELLED, etc.)
- Click supplier → filing history timeline, all invoices, ITC summary from that supplier
- "Watchlist" — top 5 highest-risk suppliers this month

### Page 3: ITC Timeline

**Components:**
- Recharts AreaChart: 6-month historical ITC claimed vs eligible (gap shows lost money)
- Bar chart: Current month breakdown by invoice source
- Cash Flow Calendar: expected ITC credit dates

### Page 4: Munim Report

**Components:**
- Report preview (embedded PDF viewer)
- Download button
- "Send to CA" button (triggers WhatsApp message to registered CA)
- Historical reports (previous months)

### Page 5: CA Portal (Separate Auth)

**Components:**
- Client list (all registered traders linked to this CA)
- Per client: open issues count, ₹ at stake, last report date
- Issue resolution interface: mark resolved, add note, export
- Filing data export: pre-filled GSTR-3B numbers per client

---

## 14. Domain Logic Specifications

### ITC Rules Engine (Section 16 & 17(5) GST Act)

```python
class ITCRulesEngine:
    """
    Deterministic ITC eligibility computation.
    NO LLM involvement — pure rule-based logic.
    """
    
    # Section 17(5) — Blocked ITC categories
    BLOCKED_HSN_CATEGORIES = [
        "motor_vehicles",        # HSN 8703 (passenger vehicles, capacity ≤ 13 persons)
        "aircraft",              # unless used for specified purposes
        "vessels",
        "food_beverages",        # outdoor catering, beauty treatment
        "health_services",       # insurance, except employee coverage
        "club_membership",
        "travel_accommodation",  # hotel stays for personal use
        "personal_consumption",
    ]
    
    # Section 16(2) conditions — ALL must be met for ITC eligibility
    def check_section_16_conditions(self, invoice, supplier, gstr2b_match):
        conditions = {
            "has_tax_invoice": self._is_valid_tax_invoice(invoice),
            "goods_services_received": True,  # assumed on invoice receipt
            "tax_paid_to_government": supplier.gstin_valid and gstr2b_match.status != "ITC_AT_RISK",
            "gst_return_filed": gstr2b_match.status == "MATCHED",
            "within_time_limit": self._within_time_limit(invoice.invoice_date),
        }
        return conditions
    
    def compute_itc_verdict(self, invoice, line_items, supplier, gstr2b_match):
        # Check Section 17(5) first (hard blocks)
        for item in line_items:
            if self._is_blocked_category(item.hsn_code):
                return ITCVerdict(
                    status="INELIGIBLE",
                    reason="Section 17(5) block",
                    legal_section="17(5)",
                    itc_amount=0
                )
        
        # Check Section 16(2) conditions
        conditions = self.check_section_16_conditions(invoice, supplier, gstr2b_match)
        
        if not conditions["has_tax_invoice"]:
            return ITCVerdict(status="FIXABLE_BLOCKED", reason="Invalid tax invoice", ...)
        
        if not conditions["tax_paid_to_government"]:
            return ITCVerdict(status="AT_RISK", reason="Supplier may not have filed", ...)
        
        if not conditions["gst_return_filed"]:
            return ITCVerdict(status="AT_RISK", reason="Not in GSTR-2B yet", ...)
        
        # Check HSN mismatches (fixable blocks)
        for item in line_items:
            if item.rate_mismatch:
                return ITCVerdict(
                    status="FIXABLE_BLOCKED",
                    reason=f"HSN rate mismatch on line item: {item.description}",
                    itc_blocked=item.itc_delta,
                    fix_action="Correct HSN code before filing"
                )
        
        # All checks passed
        return ITCVerdict(
            status="CONFIRMED",
            itc_amount=invoice.total_tax_amount,
            reason="All Section 16 conditions met"
        )
```

### GSTR-2B Fuzzy Matching Algorithm

```python
class GSTR2BReconciler:
    def match_invoice(self, invoice: Invoice, gstr2b_records: List[GSTR2BRecord]) -> MatchResult:
        
        # Filter to same supplier GSTIN
        candidates = [r for r in gstr2b_records if r.supplier_gstin == invoice.gstin_supplier]
        
        if not candidates:
            return MatchResult(status="ITC_AT_RISK", confidence=0.0)
        
        # Pass 1: Exact match (GSTIN + invoice number)
        exact = next((r for r in candidates if r.invoice_number == invoice.invoice_number), None)
        if exact and self._amount_within_tolerance(exact.total, invoice.total, 0.01):
            return MatchResult(status="MATCHED", confidence=1.0, record=exact)
        
        # Pass 2: Fuzzy invoice number + amount tolerance + date window
        for record in candidates:
            levenshtein = self._levenshtein(record.invoice_number, invoice.invoice_number)
            amount_ok = self._amount_within_tolerance(record.total, invoice.total, 0.02)
            date_ok = abs((record.invoice_date - invoice.invoice_date).days) <= 30
            
            if levenshtein <= 2 and amount_ok and date_ok:
                confidence = 1.0 - (levenshtein * 0.15) - (0.1 if not date_ok else 0)
                return MatchResult(status="PROBABLE_MATCH", confidence=confidence, record=record)
        
        # Pass 3: Amount + date only (invoice number format completely different)
        for record in candidates:
            amount_ok = self._amount_within_tolerance(record.total, invoice.total, 0.01)
            date_ok = abs((record.invoice_date - invoice.invoice_date).days) <= 15
            
            if amount_ok and date_ok:
                return MatchResult(status="POSSIBLE_MATCH", confidence=0.6, record=record)
        
        # No match found
        return MatchResult(status="ITC_AT_RISK", confidence=0.0)
    
    def find_missed_itc(self, trader_id: str, gstr2b_records: List, processed_invoices: List) -> List:
        """Find invoices in GSTR-2B not in trader's records — missed ITC"""
        processed_hashes = {inv.invoice_hash for inv in processed_invoices}
        missed = []
        for record in gstr2b_records:
            record_hash = self._hash(record.supplier_gstin, record.invoice_number, record.invoice_date)
            if record_hash not in processed_hashes:
                missed.append(MissedITCItem(record=record, itc_amount=record.itc_amount))
        return missed
```

---

## 15. Demo Script

### Setup (Before Judges Arrive)
1. Pre-load 6 months of synthetic invoice history for "Raju's Kirana, Lucknow"
2. Pre-seed 15 supplier GSTINs (10 healthy, 3 with flags, 2 at-risk)
3. Pre-compute ITC state: ₹41,200 confirmed, ₹8,600 blocked (3 issues), ₹12,400 at-risk
4. Print 3 prop invoices:
   - Invoice A: HSN error (cooking oil billed as shaving cream) — will trigger fixable blocked
   - Invoice B: Valid invoice from healthy supplier — clean pass
   - Invoice C: Invoice from "Sharma Trading" (pre-seeded with MISSED_FILING flag)
5. Have WhatsApp open on phone with Munim bot chat ready
6. Have dashboard open on laptop — judges can see Money Meter live

### Demo Sequence (~5 minutes)

**[0:00 — 0:30] The Problem**
"Raju owns a kirana store in Lucknow. He gets 800 invoices a month and pays ₹35,000 to his CA. His CA spends 3 weeks per month on data entry. Raju has no idea how much ITC he's missing. The GST portal doesn't tell him. His CA doesn't have time to explain. This is ₹7,000 crore in unclaimed ITC sitting across India's 1.4 crore MSMEs — every year."

**[0:30 — 1:15] Invoice A — Live Demo**
"[Pull out phone] This is Raju. He just got this invoice from Ramesh Trading on WhatsApp." [Show crumpled prop invoice — cooking oil, wrong HSN code]
"He forwards it to Munim." [Forward image to WhatsApp bot on live phone]
[~25 seconds processing]
"[Bot responds in Hindi] — read aloud: 'HSN code galat hai. ₹400 ka ITC block ho raha hai. Apne CA ko batao HSN 3407 ki jagah 1511 karna hai.'"
"In 25 seconds. In Hindi. On WhatsApp. Zero app download."

**[1:15 — 2:00] Dashboard — The Full Picture**
"Meanwhile, on the dashboard —" [switch to laptop]
"[Show Money Meter ticking: Confirmed ₹41,200 | Blocked ₹8,600 | At-Risk ₹12,400]"
"This is Raju's ITC landscape this month. ₹24,200 sitting on the table. Three issues, sorted by rupee impact. Every issue has a specific action. Fix this one first — it unlocks ₹8,600."

**[2:00 — 3:00] The Feature No One Has**
"Now here's the part nobody does."
[Click Supplier Health tab]
"We monitor ALL of Raju's 47 suppliers — every night. Sharma Trading hasn't filed GSTR-1 in 60 days. See this flag — MISSED_FILING."
[Click Sharma Trading]
"Raju was about to pay them ₹80,000 tomorrow. If he does that and claims ITC — ₹2,380 gets denied next month. We sent him a WhatsApp alert 3 days ago."
[Show the alert message on phone]
"Supplier intelligence. Real-time. Proactive. Not reactive."

**[3:00 — 3:45] Invoice C — Fraud Detection**
[Forward Invoice C to bot]
"This invoice from a new supplier, GSTIN 45 days old, ₹50,000 value."
[Bot responds with fraud score 78/100, flags displayed]
"Fraud score 78. Two signals fired: new GSTIN issuing high-value invoice, velocity anomaly — their historical average was ₹5,000. Munim says: verify before claiming ITC."

**[3:45 — 4:30] The Munim Report**
"At the end of each month — automatically — Munim generates this."
[Show Munim Report PDF on screen — clean, one page, CA-ready]
"Raju's CA opens this, reviews it in 30 minutes instead of 3 weeks. Raju's bill drops from ₹35,000 to ₹8,000. The CA now handles 5x the clients. Nobody loses — the CA gets their time back, Raju gets his money back."

**[4:30 — 5:00] The Scale**
"1.4 crore GST-registered MSMEs. ₹50,000 average in recoverable ITC per trader per year. That's ₹7,000 crore sitting unclaimed in India's informal economy. Munim unlocks it — on WhatsApp — in Hindi — for free.
We didn't build GST software. We built the munim India never had."

---

## 16. Build Priority & Implementation Order

### Phase 0 — Infrastructure (Day 0, ~2 hours)
- [ ] Supabase project setup + run schema SQL
- [ ] Enable pgvector extension
- [ ] Upstash Kafka cluster + Redis database
- [ ] Meta WhatsApp Cloud API — developer account + test phone number + webhook URL
- [ ] Gemini API key (Google AI Studio)
- [ ] ngrok tunnel pointed at local FastAPI port 8000
- [ ] Docker Compose file with: FastAPI + n8n + PaddleOCR service

### Phase 1 — Core Pipeline (Day 1, ~6 hours)
**Priority: Get Invoice → WhatsApp response working end-to-end**
- [ ] FastAPI webhook endpoint — receive Meta webhook events
- [ ] Media download from Meta CDN → Supabase Storage
- [ ] Publish to Kafka `munim.invoice.received`
- [ ] LangGraph InvoiceProcessingAgent skeleton (nodes, edges, state)
- [ ] `extract_entities` node — Gemini Vision prompt + JSON parsing
- [ ] `validate_hsn` node — HSN DB lookup (exact only first, pgvector later)
- [ ] `compute_itc` node — basic rules engine (Sections 16 + 17(5))
- [ ] `generate_diagnosis` node — Gemini → Hindi text
- [ ] Notification Worker — consume `munim.invoice.processed` → WhatsApp reply
- [ ] Basic registration flow (onboarding conversation)

### Phase 2 — Intelligence Layer (Day 1-2, ~4 hours)
- [ ] GSTIN Verification API integration + Redis caching
- [ ] GSTR-2B fuzzy matching algorithm
- [ ] Fraud scoring (start with 3-4 signals, add more if time)
- [ ] pgvector HSN semantic search (embed all 12,167 codes — one-time job)
- [ ] Supplier compliance graph (DB structure + basic monitoring)

### Phase 3 — Supplier Monitoring (Day 2, ~3 hours)
- [ ] n8n setup (Docker) + SupplierMonitorWorkflow
- [ ] Supplier state-change detection logic
- [ ] Proactive WhatsApp alerts for supplier flags
- [ ] Supplier Health Score computation

### Phase 4 — Dashboard (Day 2, ~4 hours)
- [ ] Next.js PWA setup (Lovable for shell)
- [ ] Supabase Realtime subscription for Money Meter
- [ ] ITC breakdown display (4 buckets)
- [ ] Supplier Health Dashboard
- [ ] Priority Action Queue

### Phase 5 — Munim Report (Day 3, ~3 hours)
- [ ] LangGraph ReportGenerationAgent
- [ ] WeasyPrint PDF template + rendering
- [ ] n8n MunimReportWorkflow
- [ ] WhatsApp PDF delivery

### Phase 6 — Polish (Day 3, final 2 hours)
- [ ] Demo data seeding script (6 months synthetic history)
- [ ] Error handling + graceful fallbacks
- [ ] Loading states on dashboard
- [ ] Run full demo flow 3x — fix any rough edges

---

## 17. Environment Variables Template

```bash
# === GEMINI ===
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001

# === META WHATSAPP ===
META_WHATSAPP_TOKEN=your_token_here
META_PHONE_NUMBER_ID=your_phone_number_id
META_VERIFY_TOKEN=your_webhook_verify_token  # any string you choose
META_APP_SECRET=your_app_secret

# === UPSTASH KAFKA ===
UPSTASH_KAFKA_BOOTSTRAP=your_broker_url
UPSTASH_KAFKA_USERNAME=your_username
UPSTASH_KAFKA_PASSWORD=your_password

# === UPSTASH REDIS ===
UPSTASH_REDIS_URL=your_redis_url
UPSTASH_REDIS_TOKEN=your_redis_token

# === SUPABASE ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# === GSTIN VERIFICATION API ===
GSTIN_API_KEY=your_key_here
GSTIN_API_BASE_URL=https://api.eko.in/ekoicici/gstin/v1
# OR for Deepvue:
# GSTIN_API_BASE_URL=https://api.deepvue.tech/v1

# === APP CONFIG ===
ENVIRONMENT=development
FASTAPI_PORT=8000
NGROK_URL=https://your-ngrok-id.ngrok-free.app

# === n8n ===
N8N_HOST=localhost
N8N_PORT=5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change_this

# === REDIS CACHE TTL ===
GSTIN_CACHE_TTL_SECONDS=86400  # 24 hours, invalidated on state change
SESSION_TTL_SECONDS=3600       # 1 hour conversation state

# === ITC RULES ===
FUZZY_MATCH_AMOUNT_TOLERANCE=0.02  # 2%
FUZZY_MATCH_DATE_WINDOW_DAYS=30
FRAUD_SCORE_HARD_THRESHOLD=70
FRAUD_SCORE_SOFT_THRESHOLD=40
```

---

## 18. Open Assumptions & Gaps

### Confirmed Assumptions
- **GSTR-2B Source:** Dummy CSV generated by team (per PS Simulation Clause). No GST portal interaction.
- **Demo HSN Data:** Full 12,167-code HSN 2.0 CSV available as government open data.
- **Supplier Data:** ~30 pre-seeded supplier GSTINs for demo. Mix of healthy, flagged, and at-risk.
- **Model:** Gemini 2.5 Flash throughout (vision, text, audio, embeddings). No paid model needed.
- **WhatsApp:** Meta Cloud API test phone number. Judges register their numbers in advance if they want to try.

### Gaps Requiring Team Decision
- **Team size/roles:** Not confirmed. Build phases above assume 2 people (backend + frontend split). If solo, cut Phase 5 (Munim Report) until Phase 4 (dashboard) is solid.
- **Deployment:** Not confirmed. If cloud (Railway), update `NGROK_URL` to Railway domain. If local, ngrok is sufficient.
- **Meta Business Account:** If not already created, budget 1 hour for setup on Day 0.
- **pgvector embedding job:** One-time batch job to embed all 12,167 HSN codes. Uses ~12,000 Gemini embedding API calls. At free tier rate limits (1500 RPD), this takes ~8 days if done daily. **Solution:** Run it locally in a single batch on Day 0 with 10 RPM rate limiting — takes ~20 hours. OR use a pre-computed embedding file (HSN 2.0 descriptions + Gemini embeddings) and bulk-insert into Supabase.

### Nice-to-Have (Add Only If Time Permits)
- Voice note input (Gemini audio) — impressive but not critical for demo
- CA Collaboration Portal (Page 5 of dashboard)
- Historical ITC Leak Analysis with actual chart
- Benchmark Score (needs aggregate data, mock for demo)
- Filing Deadline Alerts (n8n workflow — low effort, add on Day 2)

---

*Document complete. All specifications above are sufficient for an engineer to build Munim.ai from scratch without additional context from this conversation.*
