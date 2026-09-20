# Munim-AI

**WhatsApp-first GST compliance co-pilot for Indian MSMEs**

![Status](https://img.shields.io/badge/Status-Active-success)
![AWS](https://img.shields.io/badge/Built%20for-AWS%20First%20Commit%20Hackathon-FF9900?logo=amazonaws&logoColor=white)
![AWS Services](https://img.shields.io/badge/AWS-Step%20Functions%20%7C%20Lambda%20%7C%20Textract%20%7C%20Bedrock%20%7C%20DynamoDB-FF9900?logo=amazonaws&logoColor=white)
![Stack](https://img.shields.io/badge/This%20Build-Lambda%20%2B%20DynamoDB%20%2B%20Textract%20%2B%20Bedrock-232F3E?logo=amazonaws&logoColor=FF9900)
![License](https://img.shields.io/badge/License-Proprietary-red)

> Traders forward invoices via WhatsApp. Munim extracts, validates, fraud-checks, and reconciles them automatically. CAs get a clean action-driven dashboard instead of a pile of paper.

---

## What Munim-AI Does

A CA managing GST compliance for MSME clients today reconciles once a month, in a
deadline rush, after the window to fix a supplier's mistake has already closed. Munim
flips that: every invoice is checked **the moment it arrives** — extracted from a
WhatsApp photo, validated against GST Act rules, fraud-scored, and reconciled against
GSTR-2B — so the CA (and the trader) knows about a blocked credit or a fraudulent
supplier weeks before the filing deadline, not on it.

- **No app to install.** Traders send invoices as WhatsApp photos; onboarding takes under 2 minutes.
- **Deterministic compliance logic.** GST Act §16/§17(5) eligibility, HSN validation, and GSTR-2B reconciliation are pure rule-based code — the LLM only does OCR and plain-language explanation, never the compliance decision itself.
- **Fraud detection nobody runs by hand.** A 6-signal scorer (Benford's Law, sequential invoicing, velocity anomalies, and more) flags fake-invoice patterns a CA charging ₹1,000/month has no time to check manually.
- **One CA, unlimited clients.** A single multi-tenant dashboard ranks every client's open issues by money at risk, so the CA always works the highest-value problem first.
- **It automates the paperwork, not the judgment call.** Representation before tax authorities and legal interpretation stay with the CA — that boundary is deliberate, not a limitation.
- **Built for scale, not a niche.** India has an estimated 6.3+ crore MSMEs and only ~1.4 crore GST-registered businesses with any real CA relationship today — the rest are priced out of compliance help entirely. A WhatsApp-first product, not an app they have to download, is the realistic way to reach the crores of Indian shopkeepers and small manufacturers this actually affects.

The rest of this README covers the feature list, tech stack, and architecture in
detail — jump to any section:

- [**Built on AWS**](#built-on-aws) — the service breakdown for this submission
- [Core USPs](#core-usps)
- [Product Walkthrough](#product-walkthrough) — real screenshots of the live app
- [Tech Stack](#tech-stack)
- [Architecture](#architecture) · [AWS Architecture](#aws-architecture)
- [Data Protection (DPDP Act, 2023)](#data-protection-dpdp-act-2023)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Live Deployment](#live-deployment) — the actual running URLs

---

## Built on AWS

This submission is a real, live AWS build — not a slide, and not just the
invoice pipeline. Two separate AWS Lambda surfaces are live: the **invoice
pipeline** (Step Functions orchestrating 8 Lambdas through OCR, deterministic
compliance scoring, and a Bedrock-generated explanation) and, new this
build, the **entire CA dashboard** — Money Meter, Action Queue, My Practice,
Supplier Trust, GSTR-2B reconciliation, PDF reports — running on a 9th
Lambda against 13 DynamoDB tables, the same FastAPI code the product always
ran, ported off Postgres onto DynamoDB rather than rewritten.

**Try it live:** https://eym73fepx3.ap-south-1.awsapprunner.com (AWS App
Runner). Log in with the public demo — phone **`1234567890`**, OTP
**`123456`** (also shown on the login page itself) — to see the full CA
dashboard running entirely on AWS, backed by real reconciled invoice data.
[**/aws-pipeline**](https://eym73fepx3.ap-south-1.awsapprunner.com/aws-pipeline)
separately reads real invoice verdicts straight off the pipeline's own
DynamoDB table, no login needed — live data, not a fixture, from either
surface.

![AWS Architecture](docs/assets/aws_architecture.png)

| AWS Service | Role in this build |
|---|---|
| **Step Functions** | Orchestrates the 4-stage invoice pipeline (extract → compute verdict → explain → finalize) |
| **Lambda** | 9 functions: ingest, extract, compute_verdict, explain, finalize, meta_webhook, voice_handler, bedrock_healthcheck, plus `munim-dashboard-api` — the entire CA dashboard (FastAPI + Mangum), covering auth, dashboard, GSTR-2B, reports, communications, and My Practice |
| **Amazon Textract** | `AnalyzeExpense` — OCR extraction from the invoice image, zero LLM involved |
| **Amazon Bedrock** | Amazon Nova Micro (cross-region inference) turns the already-computed verdict into one plain-language sentence — it never decides the verdict itself |
| **Amazon DynamoDB** | 13 tables total: the invoice pipeline's own (`munim-invoices`, `munim-traders`, `munim-hsn-codes`, `munim-system-status`) plus 9 more standing up the dashboard (`munim-dashboard-traders`, `munim-dashboard-invoices`, `munim-suppliers`, `munim-supplier-trader-links`, `munim-supplier-flags`, `munim-gstr2b-records`, `munim-reports`, `munim-preferences`, `munim-invoice-line-items`) |
| **API Gateway** | REST API (`POST /invoices`) + HTTP API (the live read endpoint behind `/aws-pipeline`) |
| **Lambda Function URL** | Public HTTPS endpoint for `munim-dashboard-api`, CORS-scoped to the App Runner frontend origin |
| **Amazon S3** | Invoice image storage (pipeline entry point) and generated PDF compliance reports (private, served via presigned URL — not a public bucket) |
| **AWS KMS** | One customer-managed key encrypts S3, every DynamoDB table, and CloudTrail's log bucket |
| **Amazon Cognito** | Provisioned for WhatsApp-OTP custom auth — not yet wired to a live auth path, stated honestly rather than overclaimed |
| **EventBridge Scheduler** | Statutory GSTR deadline alerts on the 5th/10th/18th, matching the FastAPI backend's own cadence |
| **SQS + DLQ** | Retry handling and dead-letter capture on the pipeline |
| **SNS** | WhatsApp inbound event relay from the WABA |
| **CloudWatch** | `munim-invoice-pipeline` dashboard — invocations, errors, Step Functions outcomes, DynamoDB capacity, DLQ backlog |
| **X-Ray** | One trace ID spans an invoice's entire journey, upload through finalize, with per-stage latency |
| **GuardDuty** | Account-wide threat detection |
| **CloudTrail** | Every management-plane action, plus every S3 `GetObject`/`PutObject` on the invoices bucket, including root's own access |
| **App Runner** | Hosts this submission's live frontend |
| **ECR** | Container registry for both the App Runner and `munim-dashboard-api` images |

Full service breakdown, security posture, and known issues:
**[`aws/README.md`](aws/README.md)**.

---

![Money Meter — confirmed ITC, at-risk credit, and potential recovery at a glance](docs/assets/dashboard_screenshot.png)
*Money Meter: the CA's home screen — confirmed ITC, blocked credit, and unclaimed recovery, live.*

---

## Core USPs

![Features](docs/assets/features_diagram.png)

### 1. WhatsApp-First — Zero App Download
- Traders interact entirely via WhatsApp in their language (Hindi, English, Marathi, Gujarati)
- Conversational onboarding in under 2 minutes
- Each trader gets a dedicated Munim email address for vendors who prefer email over WhatsApp

### 2. Multimodal AI Extraction
- Handles crumpled thermal receipts, handwritten bills, scanned PDFs, blurry photos
- Outputs structured JSON: supplier name, GSTIN, invoice number, date, line items, HSN codes, tax breakdown
- Low-confidence extractions are flagged for human review
- The AWS-native pipeline runs this extraction through Amazon Textract, with Amazon Bedrock (Nova Micro) generating the plain-language verdict explanation — full breakdown in [Built on AWS](#built-on-aws) above

### 3. Deterministic ITC Rules Engine — No LLM
- Pure rule-based GST Act §16 + §17(5) implementation
- Classifies every invoice into: `CONFIRMED` / `FIXABLE_BLOCKED` / `AT_RISK` / `INELIGIBLE` / `FRAUD_FLAGGED`
- 12+ blocked categories covered by HSN prefix and keyword matching (motor vehicles, accommodation, outdoor catering, health clubs, personal consumption, real estate, etc.)
- Zero hallucination risk — fully auditable logic

### 4. 6-Signal Fraud Scoring Engine (0–100)

| Signal | What It Detects |
|---|---|
| GSTIN Age | New GSTIN (<180 days) issuing high-value invoices |
| Benford's Law | Unnatural leading-digit distribution (chi-squared test) |
| Sequential Invoice Numbers | Consecutive serials from same supplier — classic fake invoice pattern |
| Business Type Mismatch | GSTIN registration category contradicts invoice line items |
| Geographic Mismatch | Supplier state ≠ buyer state without IGST |
| Velocity Anomaly | Invoice amount >5× the supplier's historical average |

Score ≥ 70 → `FRAUD_FLAGGED`. Score 40–69 → soft flag for CA review.

### 5. GSTR-2B Three-Pass Fuzzy Reconciliation
- **Pass 1 — Exact:** GSTIN + invoice number + date all match
- **Pass 2 — Fuzzy:** Levenshtein distance on invoice number (`INV-001` vs `INV001`), ±2% amount tolerance, ±15-day date window
- **Pass 3 — Amount + Date:** Fallback when invoice number is ambiguous
- Unmatched invoices surface instantly in Action Queue with vendor contact options

### 6. Prioritized Action Queue
- All issues across all clients ranked: fraud flags → ITC-at-risk → fixable blocks
- Each item shows the exact reason, affected tax amount, and recommended fix
- One-click WhatsApp or email vendor warning sent directly from the dashboard

### 7. Supplier Health Monitoring
- Tracks each vendor's GSTR-1 filing consistency across months
- Flags chronically non-compliant suppliers before they become a problem

### 8. Email Invoice Ingestion (Cloudmailin)
- Traders share their dedicated Munim email with vendors
- Vendor emails PDFs → Cloudmailin webhook → same Gemini pipeline → auto-added to records

### 9. Auto-Generated Compliance Reports
- One-click PDF per trader per period
- Covers ITC summary, blocked amounts, at-risk credits, reconciliation status, supplier health

### 10. GST Portal Simulation
- Interactive IMS (Invoice Management System) + GSTR-3B auto-draft
- Populated from live backend data — context-aware per selected trader
- Mirrors the real GST portal UI for demo and training purposes

### 11. Real-Time Compliance Timeline
- Visual deadline calendar: GSTR-1, GSTR-2B upload, GSTR-3B filing dates
- Proactive WhatsApp reminders before each deadline

### 12. Multi-Tenant CA Dashboard
- One CA manages unlimited traders from a single login
- Instant client switching, fully isolated per trader data
- Built as a PWA — works on mobile without installation

### 13. Cross-Tenant Network Intelligence
- Aggregates how a supplier behaves across *every* business Munim monitors, not just one CA's client
- A supplier flagged risky by one CA's client sharpens the signal for every other CA watching the same GSTIN
- Strictly aggregate-only — a business never sees another business's invoices, amounts, or identity, only counts
- Requires a minimum of 3 businesses tracking a supplier before it reports a pattern, to avoid leaking a single client's data through the aggregate

---

## Product Walkthrough

The screenshots below are the live, deployed app — not mockups.

![My Practice — every client the CA manages, ranked by money at risk](docs/assets/screenshot_my_practice.png)
*My Practice — the CA's full client list, each one flagged by reconciliation status and money at risk.*

![Monthly Reports — GSTR-2B records and auto-drafted GSTR-3B readiness](docs/assets/screenshot_monthly_reports.png)
*Monthly Reports — period-by-period GSTR-2B records, one-click PDF export, GSTR-3B readiness score.*

![Action Queue — every open issue across every client, ranked by severity](docs/assets/screenshot_action_queue.png)
*Action Queue — every open issue across every client, ranked Critical → Medium, each with the exact ITC amount at stake.*

![Supplier Trust — filing-consistency health score per vendor](docs/assets/screenshot_supplier_trust.png)
*Supplier Trust — every vendor's GSTR-1 filing health, so a supplier going bad is caught before it blocks ITC.*

![What the Network Sees — cross-tenant supplier intelligence, aggregate only](docs/assets/screenshot_network_intel.png)
*What the Network Sees — Core USP #13 above, live: aggregate-only supplier behavior pooled across every business Munim monitors.*

![Onboard a New Trader — WhatsApp or web QR code, no app install](docs/assets/screenshot_onboard_trader.png)
*Onboarding — a CA adds a new trader with a single QR code, over WhatsApp or the web app.*

![My Profile — CA's practice details and full client roster](docs/assets/screenshot_ca_profile.png)
*My Profile — the CA's practice details and client roster in one place.*

![Login — WhatsApp OTP, no password, no app to install](docs/assets/screenshot_login.png)
*Login — WhatsApp OTP only. No password, no app store.*

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, LangGraph, Python 3.12, Uvicorn |
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS |
| **Database (this submission, live)** | **Amazon DynamoDB** — 13 tables; both the invoice pipeline and the full CA dashboard run on it for this build, same FastAPI code, switched off Postgres via a backend adapter (`DATA_BACKEND`) rather than rewritten |
| **Invoice OCR (this submission)** | **Amazon Textract** `AnalyzeExpense` — zero LLM involved |
| **Verdict explanation (this submission)** | **Amazon Bedrock** (Nova Micro, cross-region) — turns an already-computed verdict into one plain-language sentence, never the decision itself |
| AI / LLM (WhatsApp chat + non-AWS OCR path) | Google Gemini 2.5 Flash — voice/text Q&A on WhatsApp, and OCR only when not running the AWS-native pipeline above |
| Messaging | Meta WhatsApp Cloud API |
| Email Ingestion | Cloudmailin |
| Cache / Sessions | Redis (Upstash) |
| GSTIN Validation | deepvue.tech API |
| Fuzzy Matching | python-Levenshtein |
| PDF Generation | WeasyPrint |
| Deployment (this submission) | **Frontend and entire backend on AWS** — App Runner (frontend), Lambda + DynamoDB (dashboard API), Step Functions + Lambda + Textract + Bedrock (invoice pipeline). See [Live Deployment](#live-deployment) and [`aws/README.md`](aws/README.md) |

---

## Architecture

Generated directly from the real code structure — every box names the actual file behind it.

![Architecture Diagram](docs/assets/architecture_final.png)

```
Trader (WhatsApp / Email)                              Vendor (Email)
         │                                                    │
         ▼                                                    ▼
Meta Cloud API / Cloudmailin Webhook ──────────────────────────
         │
         ▼
FastAPI Backend (this submission: AWS Lambda, behind API Gateway /
                  a Lambda Function URL — see AWS Architecture below)
         │
    LangGraph Pipeline
    ├── 1. Vision OCR → InvoiceJSON      (this submission: Amazon Textract)
    ├── 2. GSTIN Validator (deepvue.tech)
    ├── 3. HSN Validator
    ├── 4. ITC Rules Engine   ← no LLM
    ├── 5. Fraud Scorer       ← no LLM
    └── 6. GSTR-2B Reconciler ← no LLM
         │
         ▼
Database (this submission: Amazon DynamoDB — see Tech Stack above)
    ├── CA Dashboard (Next.js, deployed to AWS App Runner)
    │     ├── Action Queue
    │     ├── Supplier Health
    │     ├── Reports Panel
    │     └── GST Simulation
    └── Redis (session state / conversation context)
```

### AWS Architecture

![AWS Architecture](docs/assets/aws_architecture.png)

The `aws/` directory is a separate, parallel build of this same product's
invoice pipeline — Step Functions, Lambda, Textract, Bedrock, DynamoDB,
API Gateway, Cognito, and more. **See [`aws/README.md`](aws/README.md)**
for the full service breakdown and how each Lambda maps to the pipeline
above.

---

## Data Protection (DPDP Act, 2023)

Munim processes real financial and business data for Indian MSMEs —
invoices, GSTINs, ITC amounts, supplier relationships. That's personal and
business data squarely inside the scope of India's Digital Personal Data
Protection Act, 2023. We're not claiming full legal compliance here — that's
a legal determination, not an engineering one — but naming what's actually
built with DPDP in mind, and what honestly isn't yet, the same way the rest
of this README treats GST-scope gaps: naming the boundary reads as
competence, inventing coverage doesn't.

**In place:**
- **Data residency.** The AWS build runs in `ap-south-1` (Mumbai) — a
  deliberate choice, not the default `us-east-1`, specifically for
  India-resident processing.
- **Encryption at rest, everywhere.** One customer-managed KMS key covers
  every DynamoDB table, S3 bucket, and CloudTrail's log bucket — not a
  per-service default left on autopilot.
- **LLM data minimization.** Before an invoice detail reaches Gemini/Groq
  for non-explanatory tasks (intent classification, summaries), GSTINs are
  hashed, supplier names tokenized, phone numbers redacted, and amounts
  bucketed — never sent raw. One deliberate, disclosed exception: the
  invoice-verdict explanation itself sends the real amount and supplier
  name, because a trader reading "₹MEDIUM blocked" on WhatsApp learns
  nothing — but every such call is now logged in a tenant-scoped, CA-visible
  audit trail either way, so what went out and why is never silent.
- **No AI in the compliance decision.** ITC eligibility, fraud scoring, and
  GSTR-2B reconciliation are pure deterministic code — no model makes or
  influences a decision that affects someone's money, which matters
  directly given DPDP's stance on automated processing affecting a
  person's rights.
- **App-layer tenant isolation.** Every dashboard endpoint checks the
  caller's own phone number against the target trader's registered CA
  before returning anything (`verify_trader_access`) — a CA sees only
  clients who've actually named them.
- **Fail-closed by default.** OTP login has no bypass in production
  (`DEBUG=false` live), tokens are individually revocable, and the WhatsApp
  webhook signature check is written to reject unsigned payloads outside a
  dev environment — see the one open item below for where that last one
  still needs a config change, not a code change, to actually take effect.

**Honest gaps, not yet built:**
- **No explicit consent step.** WhatsApp onboarding today is conversational
  (name, GSTIN, CA number) with no separate "you're agreeing to this"
  checkpoint — the single highest-priority thing missing here.
- **No self-service data rights.** A trader can't yet export or delete
  their own data through the product; today that would need a direct
  request to the team. DPDP's access/correction/erasure rights need a real
  endpoint, not a support inbox.
- **Third-party processors outside India.** Gemini and Groq (both used
  narrowly, see the minimization above) process data outside India for
  that slice of calls. Minimized, not eliminated — a formal Data
  Processing Agreement review with both hasn't been done.

---

## Project Structure

```
munim/
├── aws/                            # This submission's AWS build
│   ├── lambdas/                    # ingest, extract, compute_verdict,
│   │                               # explain, finalize, meta_webhook,
│   │                               # voice_handler, bedrock_healthcheck
│   ├── state-machine.json          # Step Functions definition
│   └── README.md                   # AWS architecture + service breakdown
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── webhook.py          # WhatsApp bot + onboarding
│   │   │   ├── dashboard.py        # CA dashboard endpoints
│   │   │   ├── gstr2b.py           # GSTR-2B upload + reconciliation
│   │   │   ├── reports.py          # PDF generation
│   │   │   ├── communications.py   # Vendor WhatsApp/email warnings
│   │   │   ├── email_webhook.py    # Cloudmailin ingestion
│   │   │   └── auth.py             # JWT auth
│   │   ├── domain/
│   │   │   ├── itc_engine.py       # GST §16/§17(5) rules
│   │   │   ├── fraud.py            # 6-signal fraud scorer
│   │   │   ├── reconciler.py       # 3-pass GSTR-2B reconciler
│   │   │   ├── hsn.py              # HSN validator
│   │   │   ├── supplier_monitor.py # Supplier health scoring
│   │   │   └── network_intel.py    # Cross-tenant supplier intelligence
│   │   ├── models/                 # Pydantic data models
│   │   └── services/               # Supabase, WhatsApp, Gemini clients
│   └── requirements.txt
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/              # CA main dashboard
│   │   ├── trader/                 # Trader PWA
│   │   ├── aws-pipeline/           # Live view onto the AWS pipeline's
│   │   │                           # own DynamoDB data
│   │   └── components/             # Shared UI components
│   └── public/demo/                # GST simulation (standalone HTML/JS)
└── gst-portal-automation/          # GST portal automation scripts (not tracked)
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/webhook` | GET/POST | WhatsApp webhook (verify + message handling) |
| `/api/v1/webhook/upload-invoice` | POST | Direct upload from Trader PWA |
| `/api/v1/email-webhook` | POST | Cloudmailin inbound email → pipeline |
| `/api/v1/dashboard/summary/{trader_id}` | GET | ITC summary card data |
| `/api/v1/dashboard/actions/{trader_id}` | GET | Prioritized action queue |
| `/api/v1/dashboard/actions/{id}/resolve` | PATCH | Mark action resolved |
| `/api/v1/dashboard/suppliers/{trader_id}` | GET | Supplier health list |
| `/api/v1/dashboard/invoices/{trader_id}` | GET | Invoice records + filters |
| `/api/v1/dashboard/itc-timeline/{trader_id}` | GET | 6-month ITC chart data |
| `/api/v1/dashboard/reports/generate/{trader_id}` | POST | Generate PDF report |
| `/api/v1/gstr2b/upload-file/{trader_id}` | POST | Upload GSTR-2B JSON |
| `/api/v1/gstr2b/reconcile/{trader_id}` | POST | Trigger reconciliation run |
| `/api/v1/gstr2b/records/{trader_id}` | GET | Fetch GSTR-2B records |

---

## Live Deployment

This is a deployed, finished submission — not a local dev project.

- **Frontend (AWS App Runner):** https://eym73fepx3.ap-south-1.awsapprunner.com
- **Live AWS pipeline view:** https://eym73fepx3.ap-south-1.awsapprunner.com/aws-pipeline
  — reads real data straight off the Step Functions pipeline's own DynamoDB table.

### AWS Deployment
The `aws/` build deploys straight to AWS — Step Functions, Lambda, API
Gateway, DynamoDB, App Runner. See [`aws/README.md`](aws/README.md) and
the per-component docs in `aws/*.md` (state machine, API Gateway,
EventBridge, App Runner) for the exact `aws`/`docker` CLI commands used
to stand each piece up.

---

![Munim-AI](docs/assets/munim_title_slide.jpg)

---

*See LICENSE.*
