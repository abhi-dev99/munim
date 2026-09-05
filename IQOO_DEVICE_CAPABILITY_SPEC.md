# iQOO Device Capability Utilization Spec — Munim.ai / Pune City Battle

**Doc type:** Technical feature catalog + prioritization (PRD/SRS hybrid)
**Scope:** Every credible way to use iQOO-provided hardware/tooling (Snapdragon NPU, camera, mic, Office Kit) inside Munim's FinTech & Commerce track submission
**Constraints this spec is written against:** team of 3 students, 3× Windows laptops, 3× iQOO loaner phones (one per member) issued at check-in, 30-hour window (Sat 08:00 check-in → Sun ~17:00 awards), extending the existing Munim.ai codebase (not a from-scratch build), track = FinTech and Commerce (city-battle only, drops at Finale)

---

## 1. Classification framework

Every idea below is tagged with exactly one primary category. Conflating these is how teams end up with fake-looking telemetry — keep them separate in both planning and pitch language.

| Tag | Meaning | Judged by |
|---|---|---|
| **`SCORE`** | Build-time behavior whose only purpose is HackTracker telemetry (Office Kit usage, camera/voice/on-device-AI counts+durations) | Device data, 25% of total |
| **`PRODUCT`** | A real feature an actual trader/CA would use after the hackathon — must survive the question "would this exist if HackTracker didn't exist?" | Jury: end product (30%), novelty (20%), technical depth (15%) |
| **`DEMO`** | A presentation-time tactic — doesn't run in production, only exists to make the live pitch land | Jury: demo & presentation (10%) |

Ideas tagged `PRODUCT` earn `SCORE` credit as a side effect if they touch camera/voice/on-device-AI — that overlap is the goal, not a coincidence. Ideas that are `SCORE`-only and not `PRODUCT` are lower priority and should be minimized — a judge asking "why does this exist" with no good answer is a worse outcome than a slightly lower telemetry number.

---

## 2. Feature catalog

Each entry: **ID · name** — mechanism → why → effort (S/M/L) → tags → verdict.

### OCV — On-device computer vision (camera + NPU)

**OCV-1 · Photo quality gate** — small in-browser/on-device model (TFLite via MediaPipe, or ONNX Runtime Web if PWA-only) flags blur/glare/bad-crop on a scanned invoice *before* it's sent to Gemini, with instant "retake" feedback in the `/trader` scanner. → Bad WhatsApp photos are the #1 cause of OCR failure in the field per existing pipeline behavior (confirmed: Gemini extraction fallback chain exists specifically to survive garbled output) — this fixes the actual failure mode instead of papering over it downstream. → **M** → `PRODUCT` + `SCORE` (camera + on-device AI) → **BUILD — this is the anchor feature.**

  **Status: BUILT** (branch `iqoo/photo-quality-gate`). Shipped as pure JS
  Laplacian-variance sharpness + overexposure-ratio analysis rather than a
  loaded TFLite/ONNX model — same on-device, zero-network guarantee, no
  model-loading risk under a 30-hour clock, and it is unit-tested (Vitest)
  since it's plain math over `ImageData`. Also corrects this entry's
  original assumption: the real `capture="environment"` file input and
  upload call live in `frontend/src/app/trader/page.js`
  (`handleInvoiceUpload`), not `/trader/scanner`, which is unwired demo
  code with no link pointing to it and no backend call. The gate runs in
  `handleFileSelected` before `handleInvoiceUpload`, with a non-blocking
  retake prompt ("Upload Anyway" override). Core logic:
  `frontend/src/app/utils/imageQuality.js`; tests:
  `frontend/src/app/utils/imageQuality.test.js`. Auto-crop (OCV-2) was not
  attempted — out of scope for this pass.

**OCV-2 · On-device edge-detect + auto-crop** — real-time document-boundary detection (OpenCV.js or a lightweight on-device segmentation model) auto-crops/deskews before OCR, same pipeline stage as OCV-1. → Directly improves Gemini extraction accuracy (cleaner input = fewer OCR retries = fewer wasted paid API calls) and is a natural pairing with OCV-1 in the same camera-capture moment. → **S–M** (can share OCV-1's model-loading scaffolding) → `PRODUCT` + `SCORE` → **BUILD if OCV-1 lands with time to spare, same commit surface.**

**OCV-3 · On-device OCR triage for offline capture** — Android's on-device text-recognition (or a tiny local OCR pass) does a first read when network is unavailable, queues the raw text + image locally, and defers full structured Gemini extraction until connectivity returns. → This is the *only* item in this catalog that's a genuine architectural extension of Munim's own positioning ("checks invoices while there's still time to fix a filing," built for low-connectivity Bharat MSMEs) rather than a bolt-on — it's the on-device story the product already claims to need. → **L** (requires an offline queue + sync-on-reconnect flow that doesn't exist today) → `PRODUCT` + `SCORE` → **catalog for Grand Finale, too large for this weekend.**

**OCV-4 · Tamper/re-photograph forensics signal** — on-device error-level-analysis or a small tamper-detection pass run on the captured image before upload, feeding a **7th fraud signal** ("was this image itself manipulated") alongside the existing 6-signal scorer (Benford's Law, sequential-invoice, velocity, GSTIN age, etc.). → Genuinely novel: none of the existing fraud signals look at the image itself, only at the extracted data. A security-literate judge will recognize this as a real, non-obvious contribution. → **L** (forensics models are finicky, false-positive risk is real, needs careful threshold tuning under time pressure) → `PRODUCT` → **catalog, don't attempt live-coded under a 30-hour clock — a bad demo of this is worse than not having it.**

### VOI — Voice (mic + on-device speech)

**VOI-1 · Voice GST queries** — on-device speech-to-text (Web Speech API where offline-capable, or a small local Whisper variant) for typed-vs-spoken parity in the trader PWA ("mera ITC kitna bacha hai?"). → Matches the MSME persona directly — many traders are more comfortable speaking than typing, and this is stated as differentiator-adjacent in existing positioning. → **M** → `PRODUCT` + `SCORE` (voice + on-device AI) → **BUILD if OCV-1 lands early and time remains — second priority, not first.**

**VOI-2 · On-device TTS for the Hindi diagnosis** — read the existing `diagnosis_hi` text aloud via the phone's built-in on-device TTS instead of (or alongside) the WhatsApp text bubble. → Directly serves literacy-accessibility for the exact user this product targets, and is nearly free to build (TTS engines are OS-native, no model integration needed) — a very high value-to-effort ratio. → **S** → `PRODUCT` + `SCORE` (voice/on-device AI, arguably the cheapest genuine on-device AI touchpoint in this entire catalog) → **BUILD — cheapest real win here, do this even if nothing else voice-related lands.**
  - **Status: BUILT** (branch `iqoo/on-device-tts`). `frontend/src/app/utils/speech.js` wraps `window.speechSynthesis`; `frontend/src/app/components/ListenButton.js` is the Listen/Stop control; wired into the post-upload scan-result toast in `frontend/src/app/trader/page.js`. Not yet wired into invoice history / `InvoiceDetailModal.js` — good follow-up, same utility already covers it.

**VOI-3 · Voice-note context capture** — trader adds a short voice memo alongside a photo ("cash payment, Ramesh Traders") transcribed on-device to enrich extraction context (e.g. payment method for the 180-day reversal rule). → Nice-to-have, addresses a real gap (payment status is currently manual), but adds a new data-capture UX mid-hackathon with no existing hook to hang it on. → **M–L** → `PRODUCT` → **catalog.**

### UX — Haptic feedback

**UX-1 · Haptic feedback on invoice scan results** — `navigator.vibrate()` fires a short pattern the instant a scan result renders in the trader PWA: single pulse for a clean `CONFIRMED` result, double pulse for `AT_RISK`/`FIXABLE_BLOCKED`, and a distinct longer triple pulse for `FRAUD_FLAGGED`. → A trader glancing away from the screen mid-scan (common on a shop counter) still gets an instant, wordless signal of good/bad/urgent before they read the text — and it's a real device-capability touchpoint (vibration motor) that costs almost nothing to add on top of an already-working scan-result flow. → **S** → `PRODUCT` + `SCORE` (device hardware, on-device only, no network) → **BUILD — trivial effort, real UX value, no risk to the existing flow.**

  **Status: BUILT** (branch `iqoo/haptic-feedback`). `frontend/src/app/utils/haptics.js`
  wraps `navigator.vibrate()` behind a feature check with `vibrateSuccess()`,
  `vibrateWarning()`, and `vibrateAlert()`, each a no-op (never throws) on
  browsers without vibration support (notably iOS Safari). Wired into
  `frontend/src/app/trader/page.js` via a `useEffect` keyed on
  `[scanState, scanResult]` so it fires exactly once per new scan result, not
  on unrelated re-renders. Unit-tested in
  `frontend/src/app/utils/haptics.test.js`.

### OFK — Office Kit (build-time usage, not a product dependency)

Be explicit about this distinction in the pitch: **Office Kit is a hackathon build tool provided by iQOO, not something a real trader's CA has installed.** Do not present any of these as end-user product features — that's a fabricated claim a technical judge will catch instantly. All OFK items are pure `SCORE`.

**OFK-1 · Screen-mirror + remote-control as the default Red Light dev workflow** — literally drive the IDE from the phone via Office Kit during Red Light blocks rather than defaulting to laptop-solo. → This is the single highest-leverage `SCORE` item in the whole catalog since it's explicitly HackTracker-measured usage, at zero product risk. → **S** (behavioral, not code) → `SCORE` → **DO, continuously, per the [[Red Light Playbook]] checklist.**

**OFK-2 · Clipboard + file-transfer for real artifacts** — move actual commit messages, test GSTINs, screenshots, and scanned test invoices between phone and laptop through Office Kit instead of USB/cloud. → Same rationale as OFK-1 — genuine usage tied to genuine work product, not manufactured usage. → **S** → `SCORE` → **DO.**

### MDX — Multi-device demo (3 phones, 1 per teammate)

**MDX-1 · Live three-actor demo** — Phone A sends a real WhatsApp invoice photo on stage; Phone B is a second trader whose supplier just degraded in `supplier_monitor.py`'s health check, showing the proactive alert arrive live; Phone C runs the CA-side view. → This is the single best `DEMO` idea in the catalog: it turns "continuous monitoring across many traders" from a claimed differentiator into something judges watch happen in real time across three physical devices, instead of one person clicking through one flow. Directly exploits having 3 loaner phones, which most 1-2-person teams won't have. → **M** (needs a pre-seeded "about to degrade" supplier and a rehearsed sequence, not new code) → `DEMO` → **BUILD the rehearsal, not new code — highest-leverage use of team size 3.**

**MDX-2 · Office-Kit-mirrored pitch delivery** — present the Top 10 pitch slides mirrored *from* a phone via Office Kit's remote-control, so "phone is in the loop" is demonstrated during the pitch itself, not just the product demo segment. → Cheap, reinforces the phone-first claim at the exact moment judges are scoring demo & presentation. → **S** → `DEMO` + `SCORE` → **BUILD (just a rehearsal decision).**

### NPU — "Local or open-source model at the core" (the stack rule's actual bar)

**NPU-1 · On-device semantic HSN match** — replace/front the existing pgvector semantic-fallback pass in `hsn.py` with a small on-device sentence-embedding model (ONNX, NPU-accelerated) for the *first* pass, falling back to the cloud pgvector path only on low-confidence. → This is the one idea in the whole catalog that satisfies "local model at the core" without being a bolt-on gimmick — it accelerates and localizes a real, already-existing, already-correct engine component (`hsn.py`'s two-pass exact+semantic design), rather than adding a cosmetic feature next to the real product. → **L** (swapping a model into a working pipeline under time pressure is genuinely risky) → `PRODUCT` + `SCORE` → **catalog unless the Saturday teach-in reveals iQOO-provided tooling that makes this trivial (they mention free AI credits + NPU-targeted tooling at check-in — reassess after that).**

---

## 3. What to actually build (priority order, given 30 hours and existing bug-fix backlog)

1. **VOI-2 (on-device TTS)** — build first. Cheapest genuine win, nearly zero integration risk, real accessibility value.
2. **OCV-1 (photo quality gate)** — the anchor. Budget the most Red Light hours here; it's the one item that's simultaneously the best product fix, the clearest on-device-AI telemetry, and the most defensible under judge questioning.
3. **OCV-2 (auto-crop)** — only if OCV-1 lands with room to spare; shares its scaffolding.
4. **MDX-1 + MDX-2 (demo choreography)** — zero new code, pure rehearsal; do this regardless of how the build goes, since it costs nothing but planning time.
5. **VOI-1 (voice queries)** — stretch goal, after 1–4 are solid.
6. Everything else in the catalog (OCV-3, OCV-4, VOI-3, NPU-1) — **do not attempt live**. These are Grand Finale / post-event roadmap items. Naming them in the pitch as "what's next" costs nothing and signals technical range without the risk of a half-built feature failing on stage.

Do not let `SCORE`-chasing crowd out the actual bug-fix backlog (§ below) — a product that's polished on telemetry but breaks when a judge asks for a real reconciled invoice loses more on the 70% jury-scored side than it gains on the 25% device-scored side.

---

## 4. Explicitly rejected ideas (and why)

- **Location/GPS-based supplier verification** — technically interesting (phone-native capture enables a check a desktop upload flow couldn't) but raises real consent/privacy questions with financial data that shouldn't be improvised under a 30-hour clock, and adds an entirely new data dimension to the schema.
- **Device attestation / anti-screenshot fraud signal** — sophisticated, but Android attestation APIs have real integration friction and this would consume disproportionate build time for a signal that can't be convincingly demoed in a 3-5 minute pitch.
- **"Office Kit as a product feature"** — rejected on principle, see § OFK above. Office Kit is iQOO's dev bridge, not something a trader's CA has installed; presenting it as end-user functionality is a claim a judge will immediately see through.
