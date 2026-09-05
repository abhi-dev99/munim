# Munim.ai — Comprehensive Product Plan & Feature Roadmap

> This document is the master reference for all planned interfaces, features, and future possibilities
> for the Munim.ai platform. It covers the WhatsApp bot, mobile app (PWA), CA portal, 
> voice support, and all backend intelligence capabilities.

---

## The Product Stack (All Interfaces)

Munim.ai is not a single app. It is a **multi-surface intelligence platform** with four distinct interfaces, all connected to the same backend and database:

| Surface | Who Uses It | What It Does |
|---------|-------------|-------------|
| **WhatsApp Bot** | Trader (primary) | Invoice upload, voice commands, ITC status, alerts |
| **Trader Mobile App (PWA)** | Trader | Visual dashboard, invoice history, supplier check tool |
| **CA Web Portal** | Chartered Accountant | All client invoices, compliance management, report generation |
| **Admin Dashboard** | Munim Team / Demo | System health, model performance, usage analytics |

---

## INTERFACE 1: WhatsApp Bot (Trader Primary Interface)

### Currently Implemented
- [x] Invoice image processing → Hindi diagnosis
- [x] Trader registration (GSTIN onboarding)
- [x] On-demand ITC status ("status" / "kitna ITC hai?")
- [x] Proactive supplier health alerts (daily job)
- [x] Filing deadline reminders (5th, 10th, 18th)
- [x] Monthly Munim Report PDF delivery

### Voice Support (NEW — Build This)

**The Problem:** Many traders are more comfortable speaking than typing. Rural or semi-literate traders especially find audio more natural.

**What We Build:**

#### Incoming Voice Messages (Trader → Munim)
When a trader sends a WhatsApp voice note, the bot must:
1. Download the audio file from Meta's media API (already implemented for images — same flow)
2. Send the audio bytes to **Gemini 2.0 Flash** (it handles audio natively — no separate STT needed)
3. Extract the intent: `"Munim, Ramesh Trading ki invoice dekho"` → invoice lookup intent
4. Execute the intent and reply in Hindi voice or text

**Supported Voice Commands:**
```
"Munim, aaj kitna ITC hua?" → ITC summary
"Supplier XYZ ka status kya hai?" → Supplier compliance check
"Mujhe report chahiye" → Trigger report generation
"[describe invoice verbally] → Voice invoice entry (for handwritten/no-photo situations)
"Deadline kab hai?" → Next filing deadline
"Status bata" → Full compliance status
```

#### Outgoing Voice Responses (Munim → Trader)
For key alerts, send audio voice notes back (not just text):
1. Use **Gemini TTS** or Google Cloud TTS to generate Hindi audio
2. Send the MP3/OGG via `whatsapp.send_audio()` method
3. Use voice for: fraud alerts, deadline warnings, high-value ITC blocked alerts

**Technical Implementation:**
```python
# webhook.py — add audio message type handler
elif msg_type == "audio":
    audio_url = extract_audio_url(payload)
    audio_bytes = await whatsapp.download_media(audio_url)
    
    # Gemini handles audio natively
    response = await gemini.understand_audio(audio_bytes, prompt=VOICE_INTENT_PROMPT)
    intent = parse_intent(response)
    await execute_intent(intent, trader, phone)
```

#### Invoice via Voice Description
If a trader doesn't have the invoice photo but has the invoice in hand:
- Trader reads out: *"Ramesh Trading, invoice 1234, date 5 June, taxable 10,000, GST 1,800"*
- Munim extracts structured invoice data from speech
- Processes it as a manually-entered invoice (lower fraud score, flagged as "manually entered")
- Stores with `source = "voice_manual"` flag

---

### Additional WhatsApp Features (Planned)

#### 1. Supplier Pre-Check Tool
Before paying a new supplier, trader texts their GSTIN:
```
Trader: "27AABCS1429B1ZB check karo"
Munim: "Radha Traders — GSTIN Active ✅
        Filing history: 8/12 months filed (67%)
        Risk: MEDIUM — check GSTR-2B before paying.
        Last filed: April 2026."
```

#### 2. HSN Code Lookup
```
Trader: "Cotton fabric ka HSN kya hai?"
Munim: "Cotton fabric (woven, <85% cotton):
        HSN: 5208 | GST Rate: 5%
        
        Agar blended fabric hai toh:
        HSN: 5515 | GST Rate: 12%"
```

#### 3. GST Calculator
```
Trader: "50,000 ki item pe 18% GST kitna hoga?"
Munim: "CGST: ₹4,500
        SGST: ₹4,500
        Total GST: ₹9,000
        Invoice Total: ₹59,000"
```

#### 4. 180-Day Payment Reminder
Auto-alert when a supplier payment is approaching the 180-day limit:
```
Munim: "⚠️ Payment Alert!
        Sharma Trading — Invoice INV-2024-0234
        Date: 1 January 2025
        Payment due by: 30 June 2025 (180-day limit)
        ITC at risk: ₹8,400
        
        Ab tak payment nahi hui? Jaldi karo — ITC
        reverse ho jayega!"
```

#### 5. Batch Invoice Status
```
Trader: "Is mahine ke sare invoices"
Munim: [Sends summary table as image or PDF]
       "June 2026 — 23 invoices processed
        ✅ Confirmed: 18 | ⚠️ At Risk: 3 | 🚨 Blocked: 2"
```

---

## INTERFACE 2: Trader Mobile App (Progressive Web App)

### Why PWA Instead of Native App
- **No app store** — works directly in Chrome/Safari on mobile (critical for low-tech traders)
- **Looks native** — can be added to home screen, works offline
- **Faster to build** — we use the same Next.js frontend code
- **No approval wait** — App Store/Play Store approval takes 2–7 days
- **For hackathon:** PWA wins on speed and reach

### How the PWA Works
In Next.js, add `next-pwa` package. The app becomes installable on Android/iOS.
A trader in Nagpur can tap "Add to Home Screen" and get a native-looking app icon.

---

### PWA Screens & Feature Set

#### Screen 1: Dashboard (Home)
The "Money Meter" — The first thing trader sees every morning:
```
┌─────────────────────────────────┐
│ 🟢 Namaskar, Vijay ji!          │
│ June 2026 ITC Status            │
├─────────────────────────────────┤
│ ✅ Confirmed      ₹41,200       │
│ ⚠️  At Risk        ₹8,600       │
│ 🚨 Blocked         ₹3,200       │
│ 💰 Recovery Possible ₹11,800   │
├─────────────────────────────────┤
│ 🔔 3 Action Items               │
│ 📋 View Report                  │
└─────────────────────────────────┘
```

Features:
- Real-time ITC meter (pulls from backend)
- Monthly trend sparkline (last 6 months)
- Notification badge for unread action items
- "Scan Invoice" quick-action button (camera)
- Language toggle: Hindi ⇄ English

#### Screen 2: Invoice Scanner (Camera)
- Opens device camera directly
- Captures invoice photo
- Sends to backend API (same as WhatsApp pipeline, but via HTTP)
- Shows processing spinner with steps: *"Extracting → Verifying GSTIN → Checking HSN → Done!"*
- Displays Hindi/English diagnosis result
- Option to share result to WhatsApp or CA

#### Screen 3: Invoice History
- Full list of all processed invoices
- Filter by: month, status (Confirmed/Blocked/At-Risk), supplier
- Tap any invoice for full detail: line items, HSN validation, fraud score breakdown
- Download as PDF or share to WhatsApp

#### Screen 4: Supplier Directory
- All suppliers the trader has dealt with
- Health score ring indicator for each
- Tap supplier → see all invoices from them + their compliance history
- "Check New Supplier" button → enter GSTIN → get instant compliance report

#### Screen 5: Action Queue
- All pending issues, sorted by ₹ impact
- Each item shows: Supplier, Problem, ₹ at risk, What to do
- "Mark Resolved" button
- "Call Supplier" shortcut (taps to call)
- "Message CA" shortcut (opens WhatsApp to CA)

#### Screen 6: Reports
- List of generated monthly Munim Reports
- View PDF in-app or download
- "Generate Report" button for current month
- Share to CA button

#### Screen 7: Settings & Profile
- GSTIN management
- CA's WhatsApp number (for auto-delivery of reports)
- Language preference (Hindi/English/Hinglish)
- Notification preferences (WhatsApp vs Push)
- 180-day payment alert settings

---

## INTERFACE 3: CA Web Portal (The Invoice Loop)

### The "Loop Mechanism" You Mentioned
Currently, the CA only gets a **monthly PDF report**. The loop you're asking about is:

**Trader uploads invoice → Munim processes it → CA sees it in real-time in their portal**

This means the CA has a live, up-to-date view of every single invoice their client (the trader) has uploaded. No more waiting for month-end. No more back-and-forth on WhatsApp. The CA is always in the loop.

**How it Works (Technical):**
```
Trader sends invoice via WhatsApp / PWA
    ↓
Backend processes → stores in Supabase (invoices table with trader_id)
    ↓
CA Portal queries Supabase in real-time (or via websocket subscription)
    ↓
CA sees invoice appear in their dashboard immediately
    ↓
CA can annotate, flag, add notes, or approve for filing
```

---

### CA Portal Screens & Feature Set

#### Screen 1: Client Overview (Multi-Trader Dashboard)
The CA's command centre. Shows all their client traders at a glance:
```
┌────────────────────────────────────────────────┐
│ YOUR CLIENTS — June 2026                        │
├────────────────────┬─────────┬────────┬────────┤
│ Client             │ Invoices│ ITC    │ Status  │
├────────────────────┼─────────┼────────┼────────┤
│ Vijay Steel Works  │ 23      │₹41,200 │ ⚠️ 3   │
│ Ramesh Kirana      │ 47      │₹12,800 │ ✅ OK  │
│ Priya Textiles     │ 31      │₹89,400 │ 🚨 1   │
│ Sunil Hardware     │ 18      │₹23,100 │ ✅ OK  │
└────────────────────┴─────────┴────────┴────────┘
```

Features:
- Total ITC across all clients
- Clients with outstanding issues highlighted
- Upcoming filing deadlines per client
- Quick-generate Munim Report for any client

#### Screen 2: Live Invoice Feed (The Loop)
Real-time feed of invoices uploaded by clients:
```
[5 min ago] Vijay Steel Works — Tata Steel Trading — ₹1,24,500 — ✅ CONFIRMED
[22 min ago] Priya Textiles — Quick Deals Ltd — ₹42,000 — 🚨 FRAUD FLAGGED
[1 hr ago] Ramesh Kirana — Agro Suppliers — ₹8,200 — ⚠️ AT RISK
```
- Filter by client / status / date range
- CA can add a note to any invoice: "Spoke to supplier, filing in 2 days"
- CA can flag invoice for client: "Aapko yeh fix karna hai"
- CA can mark invoice as "Ready for Filing" (workflow state)

#### Screen 3: Client Detail Page
Drill down into a single client (trader):
- Money Meter (same as trader dashboard)
- Invoice Register table (sortable, filterable, downloadable as CSV/Excel)
- Supplier Health graph
- Action Items queue
- GSTR-2B reconciliation status
- ITC timeline chart (6 months)
- "Generate Munim Report" button
- "Send to Client on WhatsApp" button (triggers WhatsApp delivery)

#### Screen 4: Invoice Detail Page
Click any invoice to see:
- Extracted data: supplier GSTIN, buyer GSTIN, invoice number, date
- Line items table: description, HSN code (extracted + validated), quantity, rate, taxes
- GSTIN validation result: Active/Cancelled/Suspended
- GSTR-2B match: Matched / Not Found / Partial Match (confidence %)
- Fraud signals: individual signal scores, which ones fired
- ITC verdict: Confirmed / Blocked / At-Risk with specific GST section cited
- CA annotation field: add notes for client

#### Screen 5: GSTR-3B Filing Assistant
At month end (14th → 20th), CA views:
- Pre-populated GSTR-3B draft based on confirmed ITC
- Table 4A: ITC Available (auto-calculated)
- Table 4B: ITC Reversed (blocked invoices)
- Table 4C: Net ITC (what can actually be claimed)
- "Export for Filing" button → generates JSON in GSTN-compatible format
- Issues list: what needs to be resolved before filing

#### Screen 6: Supplier Intelligence
- Master directory of all suppliers across all clients
- Which suppliers are shared across multiple clients
- Suppliers with compliance issues (flagged across the entire CA's portfolio)
- History of state changes: "Sharma Trading GSTIN suspended — 3 of your clients are affected"

#### Screen 7: Alerts & Notifications Centre
- All automated alerts sent to clients
- CA can see which alerts were read/acted on
- CA can send custom alerts to specific clients
- Batch deadline reminders: "Send reminder to all clients with pending issues"

---

## INTERFACE 4: Admin Dashboard (Internal / Demo)

For the hackathon presentation, this serves as a live demo panel:
- Total invoices processed (all time / today)
- Agent pipeline performance: average processing time
- Model usage: Gemini tokens consumed
- Error rate: % invoices that failed extraction
- GSTR-2B match rate: % invoices found in GSTR-2B
- Fraud detection stats: invoices flagged / amount protected
- Database health: table row counts, storage used

---

## BACKEND FEATURES (Full Intelligence Layer)

### Currently Operational
- [x] Gemini Vision invoice extraction (text, structured JSON)
- [x] GSTIN verification (API + mock fallback + Redis cache)
- [x] HSN validation (exact match + pgvector semantic search)
- [x] 3-pass GSTR-2B fuzzy reconciliation (exact → Levenshtein ≤2 → amount+date)
- [x] ITC rules engine (Sec 16(2), 16(4), 17(5))
- [x] 5-signal fraud scoring (GSTIN age, Benford's Law, sequential numbers, geographic mismatch, velocity anomaly)
- [x] Hindi diagnosis generation (Gemini)
- [x] Daily supplier health monitoring (APScheduler)
- [x] Monthly PDF report generation (WeasyPrint)
- [x] WhatsApp delivery to trader + CA
- [x] Supabase storage for invoices + reports

### Add: Voice Processing Pipeline
```
Audio message received (WhatsApp)
    ↓
whatsapp.download_media() → audio bytes
    ↓
gemini.understand_audio(bytes, prompt) → structured intent + transcript
    ↓
intent_router(intent) → execute appropriate handler
    ↓
[optional] text_to_speech(reply_text) → audio bytes
    ↓
whatsapp.send_audio(phone, audio_bytes)
```

### Add: E-Invoice / IRN Validation
Government e-invoices have a QR code containing:
- IRN (Invoice Reference Number)
- Supplier GSTIN, buyer GSTIN, invoice date, amount, HSN codes
- A cryptographic signature

We can:
1. Trader photographs the QR code on their invoice
2. We decode it and extract the IRN
3. Call the NIC IRP API to verify the IRN is authentic
4. This is the **strongest fraud detection** possible — if the IRN is fake or doesn't exist, it is a 100% confirmed fraudulent invoice

### Add: Tally / Zoho Export
- Export invoice register as:
  - Tally XML format (most common in India)
  - Excel CSV (Zoho Books compatible)
  - JSON (for any other software)
- CA can import directly into their accounting software

### Add: Multi-Trader Support for a Single CA
Currently, a trader registers individually. A CA should be able to:
- Onboard multiple traders under their CA account
- Have one dashboard showing all of them
- Receive one consolidated WhatsApp report

### Add: Payment Tracker (180-Day Rule)
```sql
-- New table: invoice_payments
CREATE TABLE invoice_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id),
    payment_date DATE,
    payment_amount DECIMAL(15,2),
    is_full_payment BOOLEAN DEFAULT FALSE
);
```
- Trader logs payment against invoice via WhatsApp ("Payment kiya — INV-1234 — 42000")
- System tracks 180-day deadline
- Alerts trader 30 days before expiry: "Warning: 30 days mein payment karo nahi toh ITC jaega"

### Add: Annual ITC Reconciliation (for ITR/GSTR-9)
At year end:
- Summarize entire year's ITC: claimed, blocked, reversed, eligible but unclaimed
- Identify permanently missed ITC (invoices > 2 years old that were never claimed)
- Generate GSTR-9 Annual Return draft

---

## COMPETITIVE DIFFERENTIATORS (What Makes Us Win)

### Vs. ClearTax / GSTHero / Vyapar
| Feature | Munim.ai | ClearTax | Vyapar |
|---------|----------|----------|--------|
| WhatsApp-native | ✅ | ❌ | ❌ |
| Hindi voice support | ✅ | ❌ | ❌ |
| Real-time supplier monitoring | ✅ | ❌ | Partial |
| Benford's Law fraud detection | ✅ | ❌ | ❌ |
| Point-of-decision intelligence | ✅ | ❌ | ❌ |
| Requires smartphone app | ❌ No | ✅ Yes | ✅ Yes |
| Price | Free | ₹5,000/yr | ₹2,500/yr |
| Works for Tier 3 cities | ✅ | ❌ | Partial |

### Features No One Else Has
1. **Proactive supplier graph** — monitors your suppliers' health continuously, not just your invoices
2. **Voice invoice entry** — describe invoice verbally when you can't photograph it
3. **E-Invoice IRN authentication** — cryptographic verification of government-issued invoices
4. **180-day payment tracking** — the only tool that actively prevents this ITC loss
5. **CA real-time loop** — CA sees invoices as they are uploaded, not at month-end
6. **LangGraph inspection** — every AI decision is traceable, auditable, explainable

---

## IMPLEMENTATION PRIORITY (Phased Build)

### Phase 1 — Hackathon MVP (NOW)
**Goal: Win the competition**

| # | Item | Time Estimate |
|---|------|--------------|
| 1 | CA Web Portal (Next.js, dark glassmorphism) | 2–3 days |
| 2 | Trader PWA (add mobile responsive layout) | 1 day |
| 3 | Voice message support in WhatsApp bot | 1 day |
| 4 | Live invoice feed loop on CA portal | 0.5 days |
| 5 | Supplier pre-check via WhatsApp | 0.5 days |

**Total: ~5 days**

### Phase 2 — Post-Hackathon (Production MVP)
| # | Item |
|---|------|
| 6 | E-Invoice IRN validation |
| 7 | 180-day payment tracker |
| 8 | Multi-CA client management |
| 9 | Tally/Zoho export |
| 10 | GSTR-3B filing assistant |

### Phase 3 — Scale (3–6 months post launch)
| # | Item |
|---|------|
| 11 | Annual GSTR-9 reconciliation |
| 12 | Bank statement auto-reconciliation (UPI/NEFT cross-reference) |
| 13 | Predictive ITC forecasting (ML) |
| 14 | Supplier marketplace (find GST-compliant suppliers by category) |
| 15 | Insurance integration (ITC loss insurance?) |

---

## OPEN QUESTIONS / DECISIONS NEEDED

1. **Mobile App:** PWA (my recommendation — faster, no app store) or React Native (more native feel, longer build time)?
2. **CA Portal auth:** How does a CA log in? Options:
   - WhatsApp OTP (consistent with trader flow)
   - Email + password (more traditional, easier to implement)
   - Google OAuth
3. **Voice reply:** Should Munim reply with audio voice notes back to the trader, or just text? (Audio is more impressive but adds complexity)
4. **Multi-language:** Beyond Hindi — do we need Gujarati, Marathi, Tamil for the demo?
5. **CA onboarding:** Does the trader register their CA's number, or does the CA sign up independently?
