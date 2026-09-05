# Changelog

All notable changes to Munim.ai are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — dated entries instead of semver, since this project ships continuously rather than in numbered releases. Newest first.

---

## 2026-09-04

### Added
- **On feature branch, not yet merged to `main`:**
  - `iqoo/qr-onboarding` — QR-code-based trader onboarding: the CA's dashboard renders a `wa.me` deep link (`JOIN-<short_code>`) as a scannable QR code (native OS camera QR decode, zero app code, zero network call to scan); a trader's first WhatsApp message matching `JOIN-<code>` auto-links the CA and skips the manual CA-phone-number step in the registration flow. New `short_code` column on `traders` (migration not yet applied to the live DB) and `GET /api/v1/dashboard/onboard-link`.

## 2026-09-03

### Added
- On-device voice queries in the trader PWA ("Munim se poochein") — tap the mic, ask about ITC balance/invoice count/supplier status in Hindi or English, get an instant answer from data already loaded on the page (no new network call, no cloud speech round trip on supporting browsers).
- The trader app is now a real, installable PWA (`frontend/public/manifest.json`, app icons, a minimal app-shell service worker) — previously it was only styled to *look* like a mobile app (a hardcoded fake iOS status bar) with no manifest, no service worker, and nothing for a browser's installability check to find.
- JWT revocation: tokens now carry a `jti` claim, checked against a Redis-backed revocation list on every request; `POST /api/v1/auth/logout` revokes the caller's current token. Tokens issued before this migration have no `jti` and can't be individually revoked (an accepted limitation, not a bug).
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
- CA dashboard was not responsive at all — fixed sidebar, unresponsive two-column grid, and multiple bare `grid-cols-3`/`grid-cols-4` stat tiles squeezed a 375px phone screen into a broken desktop layout. Sidebar is now an off-canvas drawer below `md`, the main grid stacks to one column below `lg`, and every stat-tile grid found in a full sweep of `dashboard/` and `components/` (not just the originally-flagged three files) now has a responsive breakpoint. Verified live at a 375×812 viewport via Chrome DevTools, not just by reading the CSS — screenshotted both the stacked layout and the drawer actually opening over a backdrop.
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
- Four `async def` functions made synchronous, blocking Gemini SDK calls (`.generate_content()` / `.embed_content()`) with no `await`/`asyncio.to_thread`, stalling FastAPI's single event loop — and every other concurrent request — for the full multi-second duration of each call: `llm_router.py`'s `_generate_online()` and `extract_invoice()` (the OCR path, the slowest call in the system), and `gemini.py`'s `transcribe_voice_note()` and `embed_text()`. Wrapped each in `asyncio.to_thread(...)`, matching the existing pattern already used for the Resend email send in `webhook.py`/`communications.py`. Added `backend/tests/services/test_gemini_concurrency.py`, which mocks the SDK call with a real (non-`asyncio`) `time.sleep` and asserts two concurrent calls finish in ~1x a single call's duration rather than ~2x.
- `request-otp` returned a different response (404 vs 200) for unregistered vs. registered phone numbers — a direct enumeration oracle. Now returns an identical response either way.
- Two fast WhatsApp messages from the same number during onboarding could both read stale conversation state before either wrote its transition — added a per-phone processing lock.

### Security
- Removed three hardcoded, live-looking third-party API keys (`sandbox_api_key`, `sandbox_api_secret`, `gstin_api_key`) from `config.py` source defaults.
- Pinned `PyJWT` to an exact version (was previously unpinned — a supply-chain/reproducibility gap, not a specific CVE).
- **Confirmed still open, needs direct action, not a code fix**: the Supabase service-role key and database password are permanently retrievable from this public repo's git history (first commit) — history was cleaned up in a later commit but never rewritten. Rotation is the only real fix; tracked in `IQOO_SECURITY_AUDIT.md` §0.

### Documentation
- This file.
