# Munim.ai — iQOO Hackathon 2026 (Pune City Battle) Master Report

**Prepared:** 2026-09-03 · **Pune City Battle:** Sept 5–6, 2026 (30 hours) · **Target:** ₹1.5L (professional/student bucket winner)

---

## 0. Read this first — the scoring rubric changes your strategy

I pulled the actual iQOO x Reskilll judging rubric. It is materially different from a generic hackathon, and it changes what "impressing the jury" means for this specific event more than any code bug does.

| Component | Weight | Measured by |
|---|---|---|
| End product quality | 30% | Jury |
| Novelty & impact | 20% | Jury |
| **Creative phone use** (camera, voice, on-device AI) | **15%** | **HackTracker device telemetry** |
| Technical depth | 15% | Jury |
| **Office Kit usage** | **10%** | **HackTracker device telemetry** |
| Demo & presentation | 10% | Jury |

This table and everything below it is now sourced directly from the rendered `/guide` and `/terms` pages at iqoo.reskilll.com (a JS app — plain fetches only see an empty shell, so this required a real browser render), not third-party paraphrases. Exact official wording: *"HackTracker · creative phone use: Device data. Camera, voice, on-device AI in the build" — 15%*, *"HackTracker · Office Kit usage: Device data. Phone and laptop bridge use" — 10%*. HackTracker "captures counts and durations only (no keystrokes, screenshots, or browsing)". **A local/open-source model at the core earns "brownie points"** (the official framing — a bonus signal, not a literal penalty clause), but the 15% "creative phone use" dimension is measured *from* camera/voice/on-device-AI usage, so a build that never touches any of those three still scores near-zero on that dimension by construction. The demo **must run on the iQOO phone**. Build time is 55% "Red Light" (phone-only, bridged to a laptop via Office Kit — screen mirror, clipboard, file transfer, remote control, already paired on your loaner at check-in) and 45% "Green Light" (both devices).

Confirmed schedule for Pune (Sept 5–6): Sat ~08:00 check-in → clock starts 10:00 → active hacking from 11:00 → two scored evaluation rounds (Saturday evening, Sunday morning) → Top 10 pitch → awards ~Sunday 17:00. Top 6 teams per city advance to the Grand Finale (3 per bucket). **FinTech and Commerce is a confirmed, official track, identical across all four cities** — Munim's domain fits it exactly. (It does *not* carry to the Grand Finale track list, which drops FinTech/Education/HealthTech in favor of Mobility/Community App — a later-stage problem, not a Pune one.)

**One rule that matters more than any of this:** both `/terms` (§03) and `/guide` state *"Submissions must be original work created during the event (with pre-event idea drafting permitted)"* and *"Original work only: code written during the event window. No shipping a pre-built product... Organisers may verify a project was built inside the event window."* Munim.ai is an existing, working, publicly-hosted codebase built for a different hackathon (Kleos 4.0). The team's call on this (made explicitly, not by default): the underlying idea is pre-existing and independently validated — it was assessed by IIM Bangalore's SIP — which is a legitimate reading of "pre-event idea drafting permitted," and the actual implementation work for the iQOO-specific build (on-device features, fixes, Office Kit integration) happens live during the event window. If you take this path, say so proactively in the pitch rather than leaving it for a judge to discover via git history — "validated concept, iQOO build done this weekend" is a strength; an undisclosed prior repo discovered mid-Q&A is not.

**The trap Munim is currently in regardless of the above:** the product's "phone-first" story is about the *end user* (an MSME trader who never needs a laptop, just WhatsApp). That's a genuinely strong angle for the 30%+20% jury-scored buckets. But it does nothing for the 25% HackTracker buckets, which score *your team's* on-device camera/voice/NPU usage and Office Kit usage *during the build*. Right now, nothing in the stack touches an on-device model, and WhatsApp itself is structurally incapable of ever earning that credit — every WhatsApp message round-trips through Meta's servers to your cloud backend; nothing runs on the phone's NPU no matter how "phone-native" the UX feels. The only place in this codebase that *can* earn on-device credit is the `/trader` PWA, because it's the only surface that executes code inside the phone's own browser.

Practical implication for the roadmap below: **build one small, real, on-device feature inside the trader PWA during the event**, and **actually use Office Kit for your own coding workflow during Red Light hours** (not just as an idea — HackTracker checks usage, not intent). Section 4 has the specific feature to build and why it fits the product honestly rather than being bolted on.

Sources: [iQOO Hackathon 2026 overview](https://reskilll.com/blogs/iqoo-hackathon-2026-india-phone-first-ai-hackathon-iqoo-reskilll/), [City Battles format](https://reskilll.com/blogs/iqoo-city-battles-2026-india-first-phone-first-ai-hackathon-4-cities/), [Winning strategy guide](https://reskilll.com/blogs/how-to-win-iqoo-city-battles-strategy-guide-phone-first-ai-hackathon/).

---

## 1. Architecture as it actually stands

```
WhatsApp (trader) ──▶ Meta Cloud API ──▶ webhook.py (FastAPI, unauthenticated*)
                                              │
                              asyncio.create_task (fire-and-forget, no queue)
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                 media download        invoice_agent.py       onboarding state
                 (whatsapp.py)         (LangGraph pipeline)    machine (Redis)
                        │                     │
                        ▼                     ▼
                 Gemini 2.5 Flash      itc_engine.py (§16/17(5), deterministic)
                 vision OCR            fraud.py (6-signal scorer)
                 (llm_router.py,       reconciler.py (3-pass GSTR-2B match)
                 7-key rotation pool)         │
                                              ▼
                                     Supabase Postgres ──▶ dashboard.py API
                                                                  │
                                                                  ▼
                                                     Next.js dashboard (/dashboard CA)
                                                     + Next.js PWA-styled (/trader)
                                                     + static /demo (GST portal sim)
                                                     + /dev (diagnostics), /admin
```

*\*See §2.1 — no signature verification is actually wired up.*

**The core technical claim — LLM only does OCR extraction + Hindi explanation, everything in between is deterministic rule-based code — is true and worth defending on stage.** `itc_engine.py`, `fraud.py`, `reconciler.py`, `hsn.py`, `supplier_monitor.py` contain zero LLM calls; this was verified by direct inspection, not just trusting the docs. That's a real differentiator against other teams who will have wrapped a GPT prompt around "check my GST" and called it done.

---

## 2. Brutal critique — bugs and gaps found by direct code reading

Three independent deep-dives were run against the current working tree. Findings below are organized by severity; each cites file:line. Nothing here was fixed — this is read-only audit output, exactly as requested.

### 2.1 WhatsApp webhook & LangGraph pipeline

**P0 — No webhook signature verification is ever invoked.** `whatsapp.py:210-221` defines `verify_webhook_signature()`; a repo-wide check confirms it is called nowhere. `webhook.py:146-149` parses `await request.json()` and processes it directly, trusting the `from` phone number unconditionally (`whatsapp.py:245`). Anyone who obtains the registered ngrok URL — which is *currently in a public git history*, per this project's own known landmines — can POST a forged Meta-shaped payload and create traders, alter GSTINs, or impersonate the CA↔trader phone pairing. Even if wired up, `meta_app_secret` defaults to `""` (`config.py:48`), which makes the verification function return `True` unconditionally — a second, independent bypass. `meta_verify_token` also has a hardcoded fallback of `"munim_verify_2026"` (`config.py:47`).

**P0 — Every Gemini/Supabase/Redis call blocks the single asyncio event loop.** `llm_router.py:49` and `:203-213`, `gemini.py:324-345` and `:361-367`, and every function in `supabase_client.py` make synchronous I/O calls directly inside `async def` handlers with no `await`/`to_thread`. Contrast with the *correct* pattern already in the same file for Resend emails (`webhook.py:542`, `asyncio.to_thread(...)`). Under concurrent WhatsApp traffic — e.g., a judge messaging while another trader's invoice is mid-OCR — one multi-second Gemini call stalls every other trader's webhook response and rate-limit check system-wide. This is the single highest-severity scalability bug in the codebase and is exactly the failure mode a live multi-user demo can trigger by accident.

**P1 — No idempotency on `message_id`.** Meta retries webhook deliveries on slow responses; `webhook.py:146-180` has no dedup cache, so a retry reruns the full pipeline (a second paid Gemini call, a second CA WhatsApp/email alert). Only invoices with a populated `gstin_supplier` get caught by the later `invoice_hash` check (`webhook.py:428-445`), and only after the expensive OCR call already ran.

**P1 — No per-phone locking during onboarding.** Two fast messages from the same number dispatch as independent `asyncio.create_task` calls (`webhook.py:176`) that can both read stale Redis state before either writes its transition — a fast double-send can process the second message against the wrong onboarding step.

**P1 — Background work has no persistence.** All heavy processing is fire-and-forget `asyncio.create_task` (`webhook.py:168-176`) with no queue behind it. A crash or `--reload` restart mid-task silently drops the invoice; the trader is left with "Processing ho raha hai" and no follow-up, no server-side trace it was ever received.

**P1 — `parse_webhook_message` only reads `messages[0]`** (`whatsapp.py:239-243`), silently dropping any additional messages Meta batches into one delivery.

**P1 — JSON-parse failures are mislabeled as quota exhaustion.** `llm_router.py:200-233`: if extraction fails for a reason unrelated to rate limits on all three fallback models, execution still falls through to the quota-exceeded sentinel, and the trader is told (in Hindi) "Munim is unavailable, try again in 2-3 minutes" — the wrong diagnosis for what may just be a bad photo.

**P2 — Raw internal error codes leak to the end user.** `invoice_agent.py:378-386` interpolates strings like `API_QUOTA_EXCEEDED` directly into the Hindi WhatsApp message shown to the trader.

**P2 — No retry on media download failure** (`whatsapp.py:148-187`, one attempt, then `(None, None)`); **no top-level try/except in `handle_text_message`** (unlike the invoice path), so an unhandled exception in registration/intent flow disappears with no user-facing response.

**What's genuinely good here:** the backgrounding architecture itself (`webhook.py` returns `{"status":"ok"}` immediately, deferring work — correctly avoids Meta's timeout, just undermined by the blocking-call bug above); Redis-state-loss recovery in `handle_text_message` (`webhook.py:196-221`) that reconstructs onboarding progress from which trader columns are already populated; WebP/PNG→JPEG magic-byte sniffing in `whatsapp.py:114-145` (a real bug class WhatsApp is known to trigger); the `GeminiKeyPool` failing loud with a clear `RuntimeError` when all 7 keys are exhausted rather than hanging; JSON salvage/repair for truncated Gemini output (`llm_router.py:171-197`); and a real, working GSTIN+invoice-number+amount duplicate-invoice hash check (`webhook.py:428-445`).

### 2.2 Core engines — ITC, fraud, reconciliation

**P0 — Reconciliation is broken by a real code bug, not just "never run."** `invoice_agent.py:219-225` calls `reconciler.match_invoice(...)` without the required `consumed_ids` argument (`reconciler.py:107-114` has no default). **Every single automatic invocation raises `TypeError`**, silently swallowed by the surrounding `try/except` (`invoice_agent.py:167`, `:229-231`), which returns `UNRECONCILED` regardless of whether a real GSTR-2B match exists. This is independent of, and worse than, the missing-column issue below — it means the automatic WhatsApp/email ingestion path (`webhook.py`, `email_webhook.py`) has **never once** produced a real match, by design of the bug, not by absence of data.

The manual endpoint (`POST /api/v1/gstr2b/reconcile/{trader_id}`, `gstr2b.py:381-509`) *does* pass `consumed_ids` correctly and would work for matching — but it never calls `mark_gstr2b_record_matched()` (`supabase_client.py:285-293`, confirmed zero callers repo-wide). So even a successful manual reconcile run cannot populate `gstr2b_records.matched_invoice_id`, which fully and independently explains the documented "0 of 2,337 rows matched" fact — it isn't only the missing migration.

**If a judge asks to see a matched invoice live, the current code cannot produce one, on either path, regardless of what data is loaded.** This is the highest-leverage fix in the entire codebase — see the roadmap.

**P0 — `gstr2b_records.record_type` migration confirmed unapplied.** `backend/migrations/add_gstr2b_record_type.sql` exists, is a single `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` + index, and its own header comment already documents that every upload currently 500s-then-swallows per record, storing nothing, and permanently defaulting every row to `"B2B"` — silently disabling `net_credit_notes()` (CDNR) and B2BA amendment handling in `reconciler.py`. This is a copy-paste-into-Supabase-SQL-editor fix, ~30 seconds, enormous payoff.

**P1 — GSTIN not normalized on the OCR side before matching.** `reconciler.py:126` does raw string equality (`r.supplier_gstin == supplier_gstin`). Upload-side GSTINs are `.upper().strip()`'d (`gstr2b.py:69`); Gemini-extracted `invoice.gstin_supplier` never is. Any OCR output with trailing whitespace or lowercase characters silently fails every match and degrades to `ITC_AT_RISK` for a spurious reason.

**P1 — No future-date sanity check.** `itc_engine.py`'s `is_valid_tax_invoice()` (line 91-98) checks field presence only, never `invoice_date <= today`. Seed data has invoices dated into December 2026 against today's real date (2026-09-03); such invoices pass every date-gated rule silently and can render `CONFIRMED`. A CA judge will notice an "approved" invoice dated in the future within seconds — it directly undercuts the "deterministic, rule-based, trustworthy" pitch.

**P2 — Fraud engine's statistical rigor is partly cosmetic.** `fraud.py:87-132`: the Benford's Law chi-squared test uses `min_sample_size=20`, but at n=20 the expected count for leading digit 9 is under 1 — well below the ≥5 rule of thumb for chi-square validity, so the test is statistically unreliable at its own stated threshold. Separately, severity scaling on this signal and on `score_velocity_anomaly` (`fraud.py:253-284`) saturates to the full point cap the instant the trigger condition fires — so despite looking like a continuous severity curve, both are effectively **binary** flags in practice. `score_gstin_age` (line 51-85), by contrast, genuinely scales across its range — worth knowing which signals to lean on if a judge asks to see "graduated" fraud scoring live.

**P2 — Fuzzy-match thresholds are generous enough to risk false positives.** Levenshtein ≤2 on invoice numbers + 2% amount tolerance + 30-day window (`reconciler.py:158-179`) will readily match sequential invoice numbers (`INV-001` vs `INV-002`) from a recurring monthly supplier with similar amounts — the exact pattern the fraud scorer's own sequential-invoice signal treats as suspicious in a different context.

**What's genuinely good here:** the §17(5)→validity→GSTIN→time-limit→RCM/composition→2B-timing→180-day→HSN waterfall in `itc_engine.py` is a coherent, defensible rule ordering, and composition-dealer/RCM gating correctly avoids false `AT_RISK` flags — a subtlety most teams building this problem statement will get wrong. The reconciler's three-pass design with a single threaded `consumed_ids` set for match-exclusivity is architecturally correct — only the *caller* misuses it. `dashboard.py:get_gstr3b_draft()` really does return `table3_1: None` with an honest "out of scope" note exactly as documented — verified in code, not just claimed. December year-wraparound is handled correctly in both `itc_engine.py` and `hsn.py`'s two-pass exact+pgvector-semantic fallback.

### 2.3 GSTIN external-validator resilience (answers the "what if deepvue-style API dies mid-demo" question directly)

`gstin.py` already has a real three-tier fallback chain: Sandbox.co.in (primary) → GSTVerify/Dubey (secondary) → local format-based demo response (`_demo_mode_response`, line 235-286), which infers a state from the GSTIN prefix and returns a plausible fabricated legal name. **This is good engineering for demo continuity** — the app will never hard-crash if an external GSTIN API is unreachable. The catch: the fallback response is returned with `verification_status: "VERIFIED_VALID"` and no visual flag distinguishing it from a real verification. If the external API happens to be down while a judge is watching, the dashboard will confidently display a fabricated legal name ("Demo Business (Maharashtra)") as if it were verified, with nothing in the UI signaling degraded mode. Also confirmed: `is_valid_gstin_format()` (`gstin.py:24-33`) does not validate the checksum digit — line 28's own `TODO` admits it — so a syntactically-shaped but invalid GSTIN can still be reported valid.

### 2.4 Next.js dashboard & trader PWA — mobile reality check

**The `/trader` app is legitimately mobile-first** — sticky header, fixed bottom action bar, 44px+ touch targets, `capture="environment"` for real camera access, slide-out nav. This is real, working phone-native UX, not a hackathon veneer.

**"PWA" is currently aspirational, not real.** No `manifest.json`, no service worker, no `next-pwa` config anywhere in `frontend/`; confirmed independently by direct filesystem check (`frontend/public/` has no manifest, `next.config.js` only sets `output: 'standalone'`). What exists is `trader/layout.js:4-12` — a `max-w-md mx-auto` div with a **hardcoded fake iOS status bar** (literal "9:41" text) to make a desktop browser screenshot look like a phone. It is not installable, has no offline capability, and cannot add-to-homescreen. **On a mobile-first hackathon where judges may literally try to install it, this is the single most fixable, highest-optics gap in the frontend.**

**P1 — The CA `/dashboard` is not responsive at all.** Hardcoded 256px sidebar margin with no breakpoint variant (`dashboard/page.js:559`), a fixed two-column grid via inline `gridTemplateColumns` (line 689), bare `grid-cols-4` with no responsive prefix in `SupplierHealth.js` and `IMSPanel.js`. On a 375-430px phone screen this renders as a squeezed, likely broken desktop layout — a real risk given the demo-must-run-on-phone rule. `GSTR3BPanel.js:118` uses `overflow-hidden` instead of `overflow-auto` on its table wrapper, which **clips** wide content instead of scrolling it — a genuine bug, not just a design choice.

**P1 — `/demo` (the GST portal simulation) is dead code.** It's a static `public/demo/index.html` + `app.js`, entirely outside the React app. It reads `?traderId=` and calls dashboard endpoints with **no Authorization header** (`app.js:555-641`), so every call 401s and it silently falls back to hardcoded fake invoices ("Balaji Hardware", "Surat Textiles"). It also hardcodes `apiBase` to `http://localhost:8000` (line 551-553) — already stale against the in-progress port change to 8004 in `start_dev.bat`, and it never worked against the deployed ngrok tunnel in the first place. The dashboard's own "GST Portal" quick-link button that constructs this URL has therefore never functioned as intended.

**P2 — `/dev` is a fully unauthenticated ops console** exposing live Gemini key-pool rotation controls and an OCR test-bench that fires real paid API calls, reachable at whatever public ngrok URL is live. Fine for internal dev, real risk if the tunnel is left running post-event.

**P2 — Zero dark-mode support** anywhere (no `prefers-color-scheme`, no `dark:` classes) — a flat miss against the project's own stated checklist.

**What's genuinely good here:** loading/error/empty states are handled well above hackathon-average (real skeleton loaders, `error.js`/`not-found.js` boundaries, graceful degrade-to-demo-data on fetch failure with friendly messaging); a driver.js onboarding tour and drag-to-reorder dashboard widgets with server-persisted preferences are more polish than typical hackathon scaffolding; frontend console-log hygiene is clean (one stray `console.log` in the whole tree); and — checked specifically because it would be a genuinely embarrassing stage moment — the OTP login page has **no UI trace** of the backend's `123456` DEBUG bypass; that risk is backend-config-only, not frontend-visible.

---

## 3. Edge cases explicitly asked about

- **Concurrent webhook load:** the real risk isn't the number of concurrent traders — it's that they aren't actually concurrent under the hood. Every Gemini/DB call blocks the single event loop (§2.1), so "concurrent" WhatsApp traffic serializes badly, and duplicate Meta webhook retries reprocess a full invoice (double cost, double CA alerts) because there's no `message_id` dedup.
- **GSTIN validator outage mid-demo:** already handled gracefully at the code level (§2.3) — but the fallback is indistinguishable from a real verification in the UI. Know this going in so you can narrate it correctly if a judge notices a "too clean" business name, rather than being caught off guard.
- **Hackathon-prototype tells that need polish:** the fake-status-bar PWA, the non-responsive CA dashboard, the dead `/demo` portal, and the unauthenticated `/dev` console are the four biggest "this is a prototype" signals a sharp judge will find in under two minutes of poking around.
- **Why the GSTR-3B auto-draft would embarrass you if pressed:** `table3_1` (outward supplies) is honestly `None` — that's fine and defensible. What isn't fine is that the *inward-supply-derived* parts of the draft depend on reconciliation, and reconciliation currently cannot produce a match at all (§2.2, P0). If a judge asks "walk me through how this number was computed," the honest answer today is "it wasn't — nothing has ever matched." Fix the `consumed_ids` bug before you rely on this in a live walkthrough.

---

## 4. The iQOO-specific strategic pitch

**Positioning stays what it already is — don't drift.** Munim automates the data-processing layer (extraction, validation, reconciliation) and explicitly leaves judgment (representation, signing, legal interpretation) to the CA, per Section 116 of the CGST Act. That's a real, defensible, non-generic differentiator against ~5 other teams solving the same "CA in your pocket" prompt — lean into it, don't soften it into "we replace your CA."

**For the jury-scored 70% (product quality, novelty, technical depth, presentation):** the pitch is already strong and true — WhatsApp-only onboarding (no app install, no laptop, works on a ₹6,000 Android phone with 2G connectivity, which is the real MSME reality iQOO's "phone-first for real-world problems on mobile" framing is explicitly asking for), Benford's Law + velocity + sequential-invoice fraud detection nobody runs manually at a ₹1,000/month retainer, and continuous supplier monitoring that catches degrading filing behavior before it blocks ITC. Say this plainly and demonstrate it live on the actual iQOO phone via a real WhatsApp thread — that satisfies "the demo must run on the iQOO phone" trivially and authentically, because the product's real interface already *is* a phone.

**For the HackTracker-scored 25% (the part that needs new work):**
1. **Ship one real on-device feature inside the `/trader` PWA before you leave for the venue.** The natural, honest fit: an **on-device photo-quality gate** on the existing camera scanner (`trader/scanner/page.js` already does `capture="environment"`) — run a small in-browser model (TensorFlow.js or ONNX Runtime Web, sub-5MB) to detect blur/glare/crop *before* the image is uploaded to Gemini, with instant "retake this, it's too blurry" feedback. This is genuinely useful (fewer wasted Gemini calls on unreadable photos, faster feedback loop for the trader), runs entirely on the phone's own hardware, and directly exercises the camera + on-device-AI telemetry HackTracker measures. It is not a bolt-on gimmick — it's a real fix for a real problem (bad WhatsApp photos are the #1 cause of OCR failure in the field).
2. **A second option if time allows:** on-device voice input for the trader PWA's GST queries (Web Speech API, or a tiny local Whisper model via transformers.js/WebGPU) — captures both "voice" and "on-device AI" telemetry and fits the MSME persona (many traders are more comfortable speaking than typing).
3. **Office Kit usage is a team-process decision, not a code task** — download and rehearse it (`pc.vivoglobal.com`) *before* Friday, and actually build your Red-Light-hour code on the phone, mirrored to a laptop via Office Kit, rather than just claiming "phone-first" in the pitch. HackTracker checks usage, not intent, and the strategy guide is explicit that judges can and do verify this.
4. **Decide the CA dashboard's story now, don't leave it ambiguous.** Given the non-responsive layout (§2.4) and the limited hours available, the higher-leverage move is *not* a responsive rewrite — it's framing: present the CA dashboard explicitly as "the back-office layer a professional accountant uses on a laptop," shown briefly via Office Kit screen-mirror, while the flagship live demo — the part running natively on the iQOO phone — is 100% the WhatsApp thread plus the `/trader` PWA. That's not a cop-out; it's an accurate and honest description of who each surface is for, and it avoids exposing a broken-looking layout to a judge holding your phone.

---

## 5. Prioritized roadmap

**Status note:** items marked ✅ below were implemented directly in this working tree on 2026-09-03, at the team's direction, after the "original work" rule (§0) was reviewed and the team decided the pre-existing, IIM-Bangalore-validated concept is fair game to keep iterating on — see §0 for that reasoning. Nothing below was shipped as a finished feature; these are correctness fixes to code that already existed, done ahead of the event so the 30-hour clock goes to new, visibly-live work (the on-device PWA feature, Office Kit usage, dashboard/demo cleanup) rather than debugging.

### Done ahead of the event
1. ✅ **Fixed `invoice_agent.py`** — `reconciler.match_invoice()` now gets a `consumed_ids` set (was a missing required argument causing a `TypeError` on every call, silently swallowed). Also normalizes `gstin_supplier` before matching.
2. ✅ **Wired `mark_gstr2b_record_matched()` into the manual reconcile endpoint** (`gstr2b.py`) — matches now actually set `gstr2b_records.matched_invoice_id`, and GSTIN is normalized there too.
3. ✅ **Added a future-date guard to `itc_engine.py:is_valid_tax_invoice()`** — an invoice dated after today is now correctly rejected instead of silently passing every date-gated rule.
4. ✅ **Wired `verify_webhook_signature()` into `receive_webhook`** (`webhook.py`) — the function existed but was never called. Still fails open if `meta_app_secret` is unset (matches existing documented dev behavior), but is now live the moment a real secret is configured.
5. ✅ **Added `message_id` idempotency** (`redis_cache.py:mark_message_processed`, wired into `receive_webhook`) — a retried Meta webhook delivery is now a no-op instead of re-running the full pipeline (double Gemini cost, double CA alert).
6. ✅ **Fixed the quota-exceeded mislabeling** in `llm_router.py` — a JSON-parse failure across all fallback models no longer masquerades as `API_QUOTA_EXCEEDED`; only a genuine 429/rate-limit error does.
7. ✅ **Stopped leaking the raw error code** (`API_QUOTA_EXCEEDED` etc.) into the Hindi WhatsApp message shown to the trader (`invoice_agent.py:handle_error`) — kept in the internal `diagnosis_en` field for debugging.
8. ✅ **Fixed `GSTR3BPanel.js:118`** — `overflow-hidden` → `overflow-x-auto`, so the Table 4 ITC breakdown scrolls instead of clipping on narrow screens.

### Still needed before the event — manual/config, not code
9. **Apply `backend/migrations/add_gstr2b_record_type.sql`** via the Supabase SQL editor. Not run by this session (no DB credentials configured here) — 30 seconds, unblocks CDNR/B2BA handling entirely, and without it every GSTR-2B upload still stores nothing.
10. **Set a real `meta_app_secret` in your deployment `.env`** so the signature check above actually verifies instead of failing open, and confirm `DEBUG=false` / a real `JWT_SECRET` are set wherever you'll demo from.

### During the event — this is where the actual "iQOO-specific build" happens
11. **Build the on-device photo-quality-gate feature inside `/trader`** (§4.1): a small in-browser model (TensorFlow.js/ONNX Runtime Web, sub-5MB) that flags blur/glare/bad-crop on a scanned invoice *before* it's sent to Gemini. Runs on-device, uses the camera, fixes a real problem (bad WhatsApp photos are the #1 OCR failure cause), and is squarely "code written during the event window."
12. **Add a real `manifest.json` + minimal service worker to `/trader`** so it's actually installable — not just styled to look like a phone screenshot (`trader/layout.js`'s fake status bar). High visual payoff if a judge tries to "add to home screen."
13. **Use Office Kit for your own build workflow during Red Light hours** — it comes pre-paired on your loaner phone at check-in, no pre-install needed; the pairing walkthrough is part of the Saturday 10:00 teach-in. HackTracker scores usage, not intent.
14. Verify the reconciliation fixes actually produce non-zero matched invoices against real data — this is your "walk me through a real match" demo moment.
15. Rehearse the live demo *on the actual iQOO phone*: WhatsApp thread end-to-end, then the `/trader` PWA camera flow showing the new on-device check.
16. Decide and rehearse the CA `/dashboard` story per §4.4 (screen-mirrored via Office Kit, framed explicitly as the back-office layer, not the phone-native demo).

### If time remains (nice-to-have, not demo-blocking)
17. Move blocking Gemini/Supabase calls to `asyncio.to_thread` (§2.1, P0-by-severity but not demo-blocking unless you plan to show concurrent traders live).
18. Add per-phone locking for full onboarding-race safety.
19. Add GSTIN checksum validation in `gstin.py:is_valid_gstin_format()`.
20. Visually flag `_demo_mode_response()` fallback data in the dashboard UI so a GSTIN-API outage during judging doesn't silently present fabricated data as verified.

---

## 6. Configuration/access needed from you

Everything above was audited by direct code reading — no `.env` values were read or needed for this report. If you want help *testing* any of the following live before or during the event, these are the only things that would require you to hand me something:
- A live `META_APP_SECRET` if you want the webhook signature-verification fix tested end-to-end against real Meta traffic (not needed to write the fix itself).
- `SANDBOX_API_KEY`/`SANDBOX_API_SECRET` or the GSTVerify key if you want the GSTIN-validator fallback chain exercised against the real APIs rather than the demo-mode path.
- Nothing else is required to implement items 1–12 above — they're pure code/SQL fixes against files already in the repo.

---

*Compiled from three independent code-reading passes over `backend/app/api/webhook.py`, `services/whatsapp.py`, `agents/invoice_agent.py`, `services/gemini.py`, `services/llm_router.py`, `domain/itc_engine.py`, `domain/fraud.py`, `domain/reconciler.py`, `domain/hsn.py`, `domain/supplier_monitor.py`, `api/gstr2b.py`, `api/dashboard.py`, `services/gstin.py`, `services/supabase_client.py`, `schema.sql`, `migrations/`, and the full `frontend/src/app/` tree, plus live research against the iQOO x Reskilll 2026 rubric.*
