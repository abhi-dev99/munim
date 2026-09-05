# Changelog

All notable changes to Munim.ai are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — dated entries instead of semver, since this project ships continuously rather than in numbered releases. Newest first.

---

## 2026-09-03

### Added
- On-device voice queries in the trader PWA ("Munim se poochein") — tap the mic, ask about ITC balance/invoice count/supplier status in Hindi or English, get an instant answer from data already loaded on the page (no new network call, no cloud speech round trip on supporting browsers).
- First real backend test suite: 48 tests across `itc_engine`, `fraud`, `reconciler`, `gstin`, and a new shared error-handling helper — this repo had zero test infrastructure before today.
- `safe_http_error()` helper (`backend/app/utils/errors.py`) — logs the real exception server-side with a correlation ID, returns a generic client-safe message. Applied across all 27 previously-leaky call sites.
- GSTIN check-digit validation (`has_valid_checksum()` in `gstin.py`) — previously only format/length was checked, never the actual checksum algorithm.
- Shared-secret admin authentication (`ADMIN_API_KEY`) gating the entire `admin.py` router, which previously had none.
- OTP request/verify rate limiting (`auth.py`).
- Message-ID idempotency on the WhatsApp webhook, so retried Meta deliveries no longer re-run the full invoice pipeline.
- `.claude/agents/` subagents: `committer` (stage + commit + push, Haiku), `fixer` (implement a spec'd change + regression test, Haiku), `upstream-watcher` (read-only check of `origin` for new activity, Haiku).
- `IQOO_MASTER_REPORT.md`, `IQOO_SECURITY_AUDIT.md`, `IQOO_DEVICE_CAPABILITY_SPEC.md` — architecture/bug audit, full security audit, and the device-capability feature catalog for the iQOO Hackathon submission.
- **On feature branches, not yet merged to `main`:**
  - `iqoo/on-device-tts` — on-device Hindi/English text-to-speech readout of the invoice diagnosis in the trader PWA (`window.speechSynthesis`, fully client-side).
  - `iqoo/photo-quality-gate` — on-device blur/glare detection (Laplacian-variance sharpness + overexposure ratio) on a scanned invoice photo before it's uploaded for OCR, with a retake prompt.

### Fixed
- **Reconciliation could never succeed on the automatic (WhatsApp/PWA) ingestion path** — `reconciler.match_invoice()` was being called without its required `consumed_ids` argument, throwing a `TypeError` on every single call that a broad `except` silently swallowed. Every invoice was landing as `UNRECONCILED` regardless of whether a real GSTR-2B match existed.
- The manual reconcile endpoint found matches but never persisted `gstr2b_records.matched_invoice_id` — fixed by wiring in the existing (previously unused) `mark_gstr2b_record_matched()`.
- GSTIN not normalized (upper/strip) on the OCR-extraction path before matching, while the upload path already was — silently broke matches on any lowercase/whitespace variance.
- Future-dated invoices could pass every date-gated ITC rule and render as `CONFIRMED` — `is_valid_tax_invoice()` now rejects a date after today.
- Gemini extraction fallback chain mislabeled non-quota JSON-parse failures as `API_QUOTA_EXCEEDED`, giving the trader a wrong diagnosis for what might just be a bad photo.
- Raw internal error codes (e.g. `API_QUOTA_EXCEEDED`) were being shown verbatim in the trader-facing Hindi WhatsApp message.
- GSTR-3B Table 4 breakdown clipped instead of scrolling on narrow screens (`overflow-hidden` → `overflow-x-auto`).
- **`main`'s frontend build was silently broken for any fresh clone**: a bare `context/` rule in `.gitignore` matched *any* directory named `context` at any depth, so `frontend/src/app/context/LanguageContext.js` (a real file `layout.js` and the dashboard depend on) had never been committed. Anchored the rule to `/context/` and committed the missing file.
- Cross-tenant IDOR on `reports.py:generate`, `gstr2b.py:upload-file`, and both `communications.py` vendor-warning endpoints — each let an authenticated (or in some cases unauthenticated) caller act on another trader's data.
- `communications.py:remind_gstin_whatsapp` called an undefined function (`send_whatsapp_message`) — a guaranteed `NameError` on every invocation.
- Live data exposure: debug-mode vendor emails wrote real trader/invoice data (including a working Supabase Storage link) to `frontend/public/latest_email.html`, a publicly-served, unauthenticated static file that was also committed to git. Write path removed, file deleted, gitignored.
- Full API schema was publicly exposed via `/openapi.json` despite `/docs`/`/redoc` looking disabled (`docs_url=None` didn't also disable `openapi_url`).
- Webhook signature verification (`verify_webhook_signature`) existed but was never actually called on incoming WhatsApp payloads.
- Direct invoice-upload endpoint (`webhook.py:/upload-invoice`) had no authentication or rate limiting despite triggering a paid Gemini OCR call per request.

### Security
- Removed three hardcoded, live-looking third-party API keys (`sandbox_api_key`, `sandbox_api_secret`, `gstin_api_key`) from `config.py` source defaults.
- Pinned `PyJWT` to an exact version (was previously unpinned — a supply-chain/reproducibility gap, not a specific CVE).
- **Confirmed still open, needs direct action, not a code fix**: the Supabase service-role key and database password are permanently retrievable from this public repo's git history (first commit) — history was cleaned up in a later commit but never rewritten. Rotation is the only real fix; tracked in `IQOO_SECURITY_AUDIT.md` §0.

### Documentation
- This file.
