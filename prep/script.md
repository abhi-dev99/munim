# Munim.ai — Judge Walkthrough Script
### (~4 minutes, point-wise)

---

## HOOK (30 sec)

> "Every team here probably built a GST tool. So let me tell you upfront what we did differently — and why it actually matters for the 14.6 million businesses that will never use a web portal."

- India has 14.6M GST-registered businesses
- ₹14,000+ crore in ITC goes unclaimed every year — not because the law is unclear, but because **the tools exist only for people who already have accountants**
- Our answer: **a GST compliance engine that lives inside WhatsApp**. Zero app install. Zero learning curve. Works for someone with a Class 5 education.

---

## WHAT WE BUILT (45 sec)

**One line:** Photo of an invoice on WhatsApp → full ITC verdict in under 10 seconds.

**What that actually means:**
- Trader forwards any invoice (printed, handwritten, supplier-forwarded) → our bot reads it
- Returns: ✅ ITC eligible / ⚠️ at risk / 🚫 blocked — with rupee amount and reason
- CA sees the same data live on a web dashboard — zero extra work for the CA
- Supported in Hindi, English, Marathi, Gujarati — **including voice notes**

---

## WHY WE'RE DIFFERENT FROM THE OTHER TEAMS (90 sec)

*This is the section that wins.*

**1. We didn't build a chatbot. We built a 7-node stateful agent.**
- Most teams: single Gemini prompt → verdict. Hallucination-prone.
- We use LangGraph — a directed acyclic graph. Each node does one job and can fail independently without crashing the whole pipeline.
- Nodes: Extract → Validate GSTIN → Validate HSN → Reconcile GSTR-2B → Compute ITC → Score Fraud → Generate Diagnosis

**2. ITC decisions are deterministic code, not LLM output.**
- The AI reads the invoice. The law decides the ITC.
- Section 17(5) blocked categories (cars, club memberships, restaurants) are hardcoded rules — not a prompt asking Gemini to "guess" if ITC applies
- Same invoice always gives same result. Auditable. Legally defensible.

**3. We reconcile against GSTR-2B with 3-pass fuzzy matching.**
- Pass 1: Exact GSTIN + invoice number match
- Pass 2: Levenshtein distance ≤ 2 on invoice number (catches typos like INV-2255 vs INV-2256)
- Pass 3: Amount within 2% + date within 30 days (catches formatting differences)
- Most teams do exact match only — that misses 30%+ of real-world matches

**4. HSN validation against 21,934 official codes + semantic fallback.**
- If the invoice has no HSN code, we embed the item description and run pgvector similarity search to suggest the right code
- "Labour charges optics repair" → SAC 995432 even if supplier left the column blank

**5. Privacy-first architecture — not an afterthought.**
- Before any cloud LLM call: GSTIN → SHA-256 hash, business names → PARTY_1, amounts → bucket label (SMALL/MEDIUM/HIGH), phone → [REDACTED]
- Gemini never sees raw PII. Every anonymization is written to an audit log.
- Local LLM first (Ollama) → cloud LLM fallback. Data can stay on-device.

**6. Voice notes. In Hindi. From a ₹8,000 Android phone.**
- Gemini multimodal transcription handles WhatsApp OGG/Opus audio
- Supports Hindi, Hinglish, Marathi, Gujarati — including mid-sentence code-switching
- No other GST tool in India does this.

**7. Dual-sided platform.**
- Trader side: WhatsApp. No onboarding except saying "Hi".
- CA side: real-time dashboard — live invoice feed, ITC buckets, supplier health scores, action queue sorted by ₹ impact
- CA has 0 additional work. Their dashboard self-populates as traders send invoices.

---

## DEMO FLOW (45 sec — do this live)

1. Send a forwarded invoice image to the WhatsApp number
2. Bot acknowledges → processes → returns ITC verdict with amount and reason in Hindi
3. Switch to dashboard → show the invoice appearing in real-time
4. Show Action Queue → sorted by rupee impact, with one-click resolve
5. Show Supplier Health → flags suppliers with filing inconsistencies

---

## IMS ANGLE (20 sec)

> "GSTN launched IMS — Invoice Management System — in October 2024. Every trader now has to explicitly Accept or Reject each supplier invoice on the GST portal, or risk auto-accepting fraud. We solve exactly this problem. Our AT_RISK flag = 'mark pending in IMS'. Our CONFIRMED flag = 'safe to accept'. We're IMS-native."

---

## CLOSE (20 sec)

- Distribution channel: WhatsApp (500M users in India) — not a new app they have to download
- Technical moat: deterministic rules engine + LangGraph + fuzzy reconciliation + semantic HSN + privacy layer — this took real engineering
- Business model: ₹499/month per trader, ₹2,999/month per CA (up to 50 clients)

> "Every rupee of ITC a small business recovers through Munim.ai is money that was legally theirs — they just didn't have the tools to claim it. We built those tools."

---

## HARD QUESTIONS — PREP

**Q: How is this different from ClearTax?**
> ClearTax needs a finance team, a web portal, and CSV uploads. Our target user has never used a spreadsheet. Different distribution, different user entirely.

**Q: What if Gemini hallucinates an ITC verdict?**
> Gemini only reads the invoice — extraction. The ITC decision is deterministic Python code that implements Section 16 and 17(5) verbatim. No hallucination possible in the decision layer.

**Q: Data privacy?**
> GSTIN, business names, phone numbers never reach any cloud LLM in raw form. Every field is anonymized before the API call. We have a per-request audit log proving it.

**Q: Is this actually live?**
> Yes. Real Meta Cloud API WhatsApp number. Real Supabase database. Real invoices processed. You can send a message right now.
