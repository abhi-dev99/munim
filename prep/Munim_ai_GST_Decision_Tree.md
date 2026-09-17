# Munim.ai — End-to-End GST Compliance Decision Tree

**Scope:** Every major path an invoice (and the trader's broader GST position) can take inside Munim.ai, from the moment a photo lands on WhatsApp to the final GSTR-3B compliance outcome.

**Structure:** `ROOT → Stage → Case → Trigger/Action → System Reaction → Consequence/Risk → Solution`

**How to read the trees below:** Each Stage represents one decision point in the pipeline. Each Case under it is a mutually exclusive branch (e.g. "valid" vs "invalid"). Where a case is the healthy/expected path, it is marked 🟢. Where it needs monitoring but isn't yet a problem, it is marked 🟡. Where it represents real financial or compliance risk, it is marked 🔴.

---

## ROOT — Munim.ai GST Workflow

```
ROOT
 ├─ Stage 0: Input Stage (four data feeds)
 ├─ Stage 1: Invoice Intake
 ├─ Stage 2: GSTIN Validation
 ├─ Stage 3: HSN Validation
 ├─ Stage 4: GSTR-2B Reconciliation
 ├─ Stage 5: Supplier Filing Status
 ├─ Stage 6: Fraud Scoring (runs in parallel from Stage 1 onward)
 ├─ Stage 7: ITC Rules Engine (Section 16 / Section 17(5))
 ├─ Stage 8: GSTR-3B Filing & Reconciliation
 └─ Stage 9: Final Compliance Outcome
```

---

## Stage 0: Input Stage

Four independent data feeds enter the system. The state of each one determines which downstream branches are even reachable.

| Input | What it is | Feeds into |
|---|---|---|
| **Invoice uploaded** | Trader sends a photo/PDF via WhatsApp, or uploads via the Trader PWA (`/api/v1/webhook`, `/api/v1/webhook/upload-invoice`) | Stage 1 (Invoice Intake) |
| **GSTR-2B uploaded** | The official supplier-filing summary from the GST portal, uploaded/synced via `/api/v1/gstr2b/*` | Stage 4 (GSTR-2B Reconciliation) |
| **GSTR-3B filed (or not)** | The trader's own monthly summary return | Stage 8 (GSTR-3B Filing & Reconciliation) |
| **Supplier filing status** | Whether each supplier has filed their GSTR-1, checked daily at 09:00 IST | Stage 5 (Supplier Filing Status) |

---

## Stage 1: Invoice Intake

**Input:** Invoice uploaded (photo/PDF via WhatsApp or PWA)
**System component:** Gemini 2.5 Flash multimodal extraction

### Case 1A — Invoice valid 🟢
| | |
|---|---|
| **Trigger / Action** | Trader uploads a readable invoice — crumpled, handwritten, or digital are all handled equally. |
| **System Reaction** | Gemini 2.5 Flash extracts structured fields (supplier name, GSTIN, invoice number/date, HSN codes, taxable value, CGST/SGST/IGST, total) with high confidence. |
| **Consequence / Risk** | None — data is clean enough to proceed. |
| **Solution / Recommended Action** | Auto-advance to Stage 2 (GSTIN Validation). No trader action required. |

### Case 1B — Invoice invalid / unreadable 🔴
| | |
|---|---|
| **Trigger / Action** | Photo is blurry, cropped, badly lit, handwriting is illegible, or the document is missing mandatory fields (GSTIN, invoice number, tax breakup). |
| **System Reaction** | Extraction confidence falls below the acceptance threshold; one or more required fields return empty or low-confidence. |
| **Consequence / Risk** | Invoice cannot enter reconciliation. Associated ITC stays unclaimed and invisible to the trader's working-capital picture until resolved — a silent drag on cash flow if it goes unnoticed. |
| **Solution / Recommended Action** | WhatsApp bot immediately asks the trader to re-upload a clearer photo or confirm/correct the extracted fields manually. If the same invoice fails twice, it is escalated to the CA dashboard action queue for manual entry. |

---

## Stage 2: GSTIN Validation

**System component:** deepvue.tech GSTIN registry integration

### Case 2A — GSTIN valid 🟢
| | |
|---|---|
| **Trigger / Action** | Extracted supplier GSTIN is checked against the live registry. |
| **System Reaction** | Registry confirms the GSTIN is active, registered, and the legal name matches. |
| **Consequence / Risk** | None — a foundational Section 16 condition (supplier must be a registered person) is satisfied. |
| **Solution / Recommended Action** | Auto-advance to Stage 3 (HSN Validation). |

### Case 2B — GSTIN invalid, cancelled, or suspended 🔴
| | |
|---|---|
| **Trigger / Action** | GSTIN does not exist, is cancelled, suspended, or the registered name doesn't match the invoice. |
| **System Reaction** | deepvue.tech returns a failure or "inactive" status; invoice is flagged at the GSTIN-validation gate. |
| **Consequence / Risk** | ITC on this invoice is at serious risk of being fully ineligible. Possible exposure to a bogus or shell vendor — a known GST fraud pattern (circular trading / fake ITC chains). |
| **Solution / Recommended Action** | Flag as high risk in the CA dashboard action queue. Notify the trader to verify supplier status before making payment. Exclude the invoice from any ITC claim until the GSTIN issue is resolved or explained. |

---

## Stage 3: HSN Validation

**System component:** PostgreSQL vector search (Supabase) against an HSN reference set

### Case 3A — HSN correct 🟢
| | |
|---|---|
| **Trigger / Action** | Declared HSN/SAC code is checked against the item description and applied tax rate. |
| **System Reaction** | Vector search confirms the code is a valid match for the description and the rate applied is consistent with that HSN. |
| **Consequence / Risk** | None — correct tax treatment, nothing to rework. |
| **Solution / Recommended Action** | Auto-advance to Stage 4 (GSTR-2B Reconciliation). |

### Case 3B — HSN mismatch 🟡
| | |
|---|---|
| **Trigger / Action** | Declared HSN doesn't match the item description, or implies a tax rate different from what was actually charged. |
| **System Reaction** | Vector search flags a classification discrepancy and surfaces the likely-correct HSN/rate. |
| **Consequence / Risk** | Possible wrong tax rate on the invoice, downstream ITC reversal risk, and increased audit/scrutiny exposure if it recurs across many invoices from the same supplier. |
| **Solution / Recommended Action** | Hold the associated ITC as "at-risk" pending correction. Prompt the trader to request a corrected invoice or credit note from the supplier. Log the mismatch against supplier health. |

---

## Stage 4: GSTR-2B Reconciliation

**System component:** Three-pass fuzzy matching engine
**Precondition:** depends on Input 0 — "GSTR-2B uploaded"

### Case 4A — GSTR-2B not yet uploaded 🟡
| | |
|---|---|
| **Trigger / Action** | Trader or CA has not uploaded/synced the current period's GSTR-2B. |
| **System Reaction** | Three-pass matching cannot run for any invoice in the period; affected invoices sit in a "pending reconciliation" queue. |
| **Consequence / Risk** | ITC eligibility for the whole period stays unknown. If left too long, it compresses the time available to fix any mismatches before the GSTR-3B deadline. |
| **Solution / Recommended Action** | Automated reminder before the 14th of the month to upload GSTR-2B; auto-pull from the GST portal if that integration is enabled. |

### Case 4B — Invoice present in GSTR-2B (matched) 🟢
| | |
|---|---|
| **Trigger / Action** | The invoice is located in the trader's GSTR-2B via fuzzy matching (pass 1: exact match, pass 2: near-match on amount/date/GSTIN, pass 3: broader fuzzy match on residual fields). |
| **System Reaction** | A confirmed match means the supplier has actually reported this invoice to the government — independent confirmation of legitimacy. |
| **Consequence / Risk** | None at this stage — this is the precondition for ITC eligibility under Section 16(2)(aa). |
| **Solution / Recommended Action** | Proceed to Stage 5 (Supplier Filing Status) and Stage 7 (ITC Rules Engine). |

### Case 4C — Invoice missing in GSTR-2B (no match) 🔴
| | |
|---|---|
| **Trigger / Action** | No match is found across all three fuzzy-matching passes. |
| **System Reaction** | Invoice is marked "unreported by supplier" in the trader's GSTR-2B. |
| **Consequence / Risk** | Under Section 16(2)(aa), ITC cannot legally be claimed until the invoice reflects in GSTR-2B. Capital stays blocked. If the trader claims it anyway in GSTR-3B, it becomes an **overclaim** — exposed to reversal with interest under Rule 36(4)/Section 50(3). |
| **Solution / Recommended Action** | Hold ITC as "blocked/pending" in the dashboard. Auto-notify the trader to follow up with the supplier for filing. Increment the supplier's risk score; if this is a recurring pattern with the same supplier, escalate visibly on the CA dashboard. |

---

## Stage 5: Supplier Filing Status

**System component:** Daily supplier health check, 09:00 IST

### Case 5A — Supplier filed GSTR-1 on time 🟢
| | |
|---|---|
| **Trigger / Action** | Supplier files GSTR-1 by the 11th of the month, ahead of the daily health check. |
| **System Reaction** | Health check confirms filing; supplier health score holds steady or improves. |
| **Consequence / Risk** | None — invoices from this supplier flow into GSTR-2B as expected. |
| **Solution / Recommended Action** | No action needed; supplier remains in the "healthy" tier on the CA dashboard. |

### Case 5B — Supplier did not file GSTR-1 🔴
| | |
|---|---|
| **Trigger / Action** | The 11th-of-month GSTR-1 deadline passes with no filing from the supplier. |
| **System Reaction** | Daily health check flags the non-filing; supplier risk score drops. |
| **Consequence / Risk** | All invoices linked to this supplier will not appear in GSTR-2B, so their ITC is blocked. If a trader has multiple non-filing suppliers, blocked capital compounds across the portfolio. |
| **Solution / Recommended Action** | Automated deadline alerts on the 5th, 10th, and 18th quantify the exact rupee ITC at risk. Recommend the trader follow up directly with the supplier, or consider sourcing from more reliable suppliers going forward. Supplier is visibly flagged red in the CA dashboard's supplier-health view. |

---

## Stage 6: Fraud Scoring

**System component:** Six-signal multivariate fraud model (runs in parallel, starting at intake)
**Signals:** Benford's Law digit-distribution analysis, velocity checks, geographic mismatch detection, temporal consistency validation, amount pattern analysis, supplier risk scoring

### Case 6A — No fraud signals triggered 🟢
| | |
|---|---|
| **Trigger / Action** | Invoice is scored across all six signals as it moves through the pipeline. |
| **System Reaction** | All six signal scores remain below the alert threshold. |
| **Consequence / Risk** | None. |
| **Solution / Recommended Action** | Continue normal processing — no manual review needed. |

### Case 6B — Fraud signal(s) triggered 🔴
| | |
|---|---|
| **Trigger / Action** | One or more signals fire — e.g. digit distribution deviates from Benford's Law expectations, an unusual burst of invoices from one supplier (velocity), supplier location doesn't match invoice geography, invoice timing is inconsistent with the supplier's normal pattern, or the amount follows a suspicious round-number/structuring pattern. |
| **System Reaction** | Composite fraud score crosses the alert threshold; invoice is auto-quarantined. |
| **Consequence / Risk** | Risk of claiming ITC against a fake, inflated, or otherwise manipulated invoice — direct financial exposure plus legal and reputational risk under GST anti-evasion provisions. |
| **Solution / Recommended Action** | Quarantine the invoice and block its ITC claim pending manual CA review. Notify the trader. Raise the linked supplier's risk score; if severe or repeated, this becomes a candidate for formal reporting. |

---

## Stage 7: ITC Rules Engine (Section 16 & Section 17(5))

**System component:** Deterministic rules engine — pure logic implementation, not probabilistic
**Precondition:** Invoice valid, GSTIN valid, present in GSTR-2B, no active fraud flag

### Case 7A — Eligible ITC 🟢
| | |
|---|---|
| **Trigger / Action** | Invoice satisfies every Section 16 condition (genuine invoice, GSTIN active, goods/services received, present in GSTR-2B) and does not fall under any Section 17(5) block. |
| **System Reaction** | Engine computes the exact eligible ITC amount deterministically — no estimation. |
| **Consequence / Risk** | None — this is "good" capital ready to be claimed. |
| **Solution / Recommended Action** | Auto-populate this amount in the GSTR-3B claim recommendation; surface it in the CA dashboard's ITC summary and 6-month ITC timeline. |

### Case 7B — Blocked ITC 🔴
| | |
|---|---|
| **Trigger / Action** | Spend falls under a Section 17(5) exclusion — common examples: motor vehicles (with limited exceptions), food and beverages, outdoor catering, club/fitness memberships, life/health insurance (unless mandated), works contract services for immovable property, goods/services for personal consumption. |
| **System Reaction** | Engine identifies and flags the exact 17(5) clause triggered. |
| **Consequence / Risk** | ITC on this line is **permanently** ineligible — claiming it anyway risks a demand notice, interest, and penalty on audit. |
| **Solution / Recommended Action** | Auto-exclude from the ITC claim. Show the trader/CA the specific clause and reason. Recommend booking the GST component as a business expense instead of a credit. |

### Case 7C — At-risk ITC 🟡
| | |
|---|---|
| **Trigger / Action** | ITC is conditionally eligible but a condition is still open — e.g. payment to the supplier is pending beyond 180 days from invoice date, the supplier's filing consistency is shaky, the HSN is under dispute/review, or the goods/services have partial business/personal use. |
| **System Reaction** | Engine marks the credit as conditional rather than confirmed, and starts tracking the relevant condition (e.g. a 180-day payment countdown). |
| **Consequence / Risk** | If the condition isn't resolved in time (e.g. payment not made within 180 days), the ITC must be reversed with interest under Rule 37 — a cash-flow surprise if not tracked proactively. |
| **Solution / Recommended Action** | Track the condition with a visible countdown/timer on the dashboard. Alert the trader well before the reversal deadline. Recommend timely payment, or proportionate voluntary reversal if the condition will not be met. |

---

## Stage 8: GSTR-3B Filing & Reconciliation

**Precondition:** depends on Input 0 — "GSTR-3B filed"

### Case 8A — GSTR-3B not yet filed 🟡
| | |
|---|---|
| **Trigger / Action** | The monthly return remains unfiled as the 20th deadline approaches. |
| **System Reaction** | Deadline alerts automatically trigger on the 5th, 10th, and 18th of the month. |
| **Consequence / Risk** | Late filing means a late fee plus interest on any tax liability, and it delays the trader's actual ITC claim. |
| **Solution / Recommended Action** | Dashboard quantifies the exact rupee ITC that's ready to be claimed this period, to motivate timely filing; nudges trader/CA with the specific deadline. |

### Case 8B — Claim matches eligible ITC (correct claim) 🟢
| | |
|---|---|
| **Trigger / Action** | The ITC amount actually claimed in GSTR-3B equals the Rules-Engine-computed eligible figure. |
| **System Reaction** | Reconciliation engine confirms a clean match between claimed and eligible amounts. |
| **Consequence / Risk** | None — fully compliant filing. |
| **Solution / Recommended Action** | Mark the period as "reconciled" in the CA dashboard and archive. |

### Case 8C — Overclaimed ITC 🔴
| | |
|---|---|
| **Trigger / Action** | The amount claimed in GSTR-3B exceeds the Rules-Engine eligible figure — commonly because blocked ITC, missing-in-2B invoices, or at-risk ITC past its condition window were included anyway. |
| **System Reaction** | System detects the mismatch by comparing GSTR-3B claim data against the GSTR-2B/Rules-Engine output, and isolates which specific invoices caused the gap. |
| **Consequence / Risk** | Liability to reverse the excess with interest under Section 50(3), possible penalty, and elevated risk of scrutiny or a demand notice (DRC-01). |
| **Solution / Recommended Action** | Immediate alert to the CA. Recommend voluntary reversal via DRC-03 in the next return cycle (cheaper than waiting for a notice). Surface the exact root-cause invoices so the same mistake isn't repeated. |

### Case 8D — Underclaimed ITC 🟡
| | |
|---|---|
| **Trigger / Action** | The amount claimed in GSTR-3B is less than the Rules-Engine eligible figure — eligible credit sitting unused. |
| **System Reaction** | System detects the gap between eligible and claimed ITC. |
| **Consequence / Risk** | The trader overpays tax in cash unnecessarily and effectively gives up working capital — a quiet but real cost, especially for thin-margin MSMEs. |
| **Solution / Recommended Action** | Alert with the exact unclaimed rupee amount. Recommend claiming it in the current period if still open, or in a subsequent period, subject to the Section 16(4) time limit (30th November of the following financial year, or the relevant annual return date, whichever is earlier). Surface as "blocked capital" on the dashboard until claimed. |

---

## Stage 9: Final Compliance Outcome

### Case 9A — Fully compliant 🟢
| | |
|---|---|
| **Trigger / Action** | Clean reconciliation across every stage: all invoices valid, GSTINs active, HSNs correct, all in GSTR-2B, suppliers healthy, no fraud signals, no over/underclaim. |
| **System Reaction** | CA dashboard shows a green compliance status for the period. |
| **Consequence / Risk** | None — ITC fully secured, no exposure. |
| **Solution / Recommended Action** | No action required; periodic monitoring continues automatically. |

### Case 9B — Partially compliant 🟡
| | |
|---|---|
| **Trigger / Action** | Some invoices carry at-risk or blocked ITC, HSN mismatches, or pending GSTR-2B/3B items remain open. |
| **System Reaction** | Dashboard shows an amber status with a populated action-item queue, sorted by rupee impact. |
| **Consequence / Risk** | Some capital remains blocked or conditional, but no active violation yet. |
| **Solution / Recommended Action** | CA/trader works through the action queue item by item, prioritizing by amount at risk and deadline proximity. |

### Case 9C — Non-compliant / high risk 🔴
| | |
|---|---|
| **Trigger / Action** | Fraud confirmed on one or more invoices, ITC has been overclaimed in a filed GSTR-3B, or missing-in-2B invoices remain unresolved past the claim window. |
| **System Reaction** | Dashboard shows a red status with urgent flags. |
| **Consequence / Risk** | Potential demand notice, interest, penalty, or — in severe fraud cases — legal exposure. |
| **Solution / Recommended Action** | Urgent CA review. File corrections (e.g. DRC-03 voluntary reversal) promptly to limit interest accrual. Tighten vetting of the suppliers involved going forward. |

---

## Sample end-to-end paths

To make the tree concrete, three representative full journeys through the system:

**Path 1 — The clean invoice (happy path)**
`Invoice uploaded → 1A valid → 2A GSTIN valid → 3A HSN correct → 4B present in GSTR-2B → 5A supplier filed → 6A no fraud → 7A eligible ITC → 8B claim matches → 9A fully compliant`

**Path 2 — The unreliable supplier (blocked capital path)**
`Invoice uploaded → 1A valid → 2A GSTIN valid → 3A HSN correct → 4C missing in GSTR-2B → 5B supplier did not file → 6A no fraud → 7 ITC held as blocked/pending → 8A return not yet filed (ITC excluded from claim) → 9B partially compliant`

**Path 3 — The risky filing (overclaim path)**
`Invoice uploaded → 1A valid → 2B GSTIN cancelled → 6B fraud signal triggered (supplier risk) → 7B blocked ITC (flagged, should be excluded) → trader claims it anyway in GSTR-3B → 8C overclaimed ITC detected → 9C non-compliant / high risk → CA alerted for DRC-03 reversal`

---

## Quick-reference: case → status legend

| Status | Meaning | Typical action |
|---|---|---|
| 🟢 Clear | Condition fully satisfied, no follow-up needed | Auto-proceed |
| 🟡 At risk / pending | Conditionally fine, but needs tracking or a nudge | Monitor, remind, or hold |
| 🔴 Blocked / risk | Real financial, legal, or compliance exposure | Alert, exclude, or escalate to CA |

---

*Generated from the Munim.ai platform overview. This tree reflects the documented architecture (Gemini 2.5 Flash extraction → deepvue.tech GSTIN check → Supabase HSN vector search → three-pass GSTR-2B fuzzy match → six-signal fraud scoring → deterministic Section 16/17(5) ITC engine → GSTR-3B reconciliation) and should be validated against current GST Act provisions before being used as a compliance reference, since tax law and deadline rules can change.*
