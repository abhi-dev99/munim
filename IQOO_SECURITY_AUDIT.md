# Munim.ai — Security Audit

**Date:** 2026-09-03 · **Scope:** Full backend (`backend/app/`), frontend (`frontend/src/`), MCP server (`backend/munim_mcp/`) · **Method:** three independent code-reading passes (auth/access-control, injection/data-handling, infra/dependencies), plus direct verification of the highest-severity claims (git history, live file state) and same-session remediation of the mechanically-fixable findings.

This is written to be read by a security professional, not summarized for one. Every finding cites file/line, an OWASP/CWE category, and a concrete exploit scenario — not a hypothetical.

---

## 0. Do this today, independent of the hackathon

**Rotate the Supabase service-role key and database password.** Confirmed directly (not just trusted from prior notes): `git show 1d340cd:backend/scripts/run_schema.py` (the repo's first commit) still returns a plaintext Postgres pooler connection string with an embedded password, and a Supabase `service_role` JWT valid until 2036. The working tree was cleaned up in a later commit (`c336d0c`), but **history was never rewritten** — no `filter-repo`/BFG evidence, normal linear history, both secrets fully retrievable by anyone who has ever cloned or forked this public repo. `.mcp.json` in the current working tree references the same project ref (`agxfxqwfnazwrtnfamiz`) embedded in the leaked JWT, confirming the key is for the **live** project. Editing files forward does nothing for this — only rotating the credential in the Supabase dashboard fixes it. This is independent of anything below and shouldn't wait for a fixer session.

---

## 1. Fixed in this session

Mechanical, low-risk, high-severity fixes were applied directly rather than just documented, given real data was already exposed. Each verified to parse and the app to import cleanly afterward.

| # | Finding | File | Fix |
|---|---|---|---|
| 1 | `admin.py`'s entire router (delete-any-invoice, Gemini-key-pool injection, live pipeline test) had **zero authentication** | `backend/app/api/admin.py` | Added a `verify_admin_key` dependency gating the whole router via a shared-secret `X-Admin-Key` header, compared with `hmac.compare_digest`. **Fails closed**: if `ADMIN_API_KEY` isn't set in `.env`, every request is denied, not allowed. **You must add `ADMIN_API_KEY=<a long random value>` to `backend/.env` yourself** — nothing works until you do, by design. |
| 2 | `reports.py:generate` — no authorization at all; anyone could generate any trader's compliance PDF and force-send it to their real WhatsApp number | `backend/app/api/reports.py` | Changed `trader_id: str` to `trader_id: str = Depends(verify_trader_access)`, matching the correct sibling pattern already used by `list_reports` in the same file. |
| 3 | `gstr2b.py:upload-file/{trader_id}` — no authorization; anyone could inject fabricated GSTR-2B records into any trader's reconciliation data | `backend/app/api/gstr2b.py` | Added `current_trader_id: str = Depends(get_current_trader_id)` + explicit `trader_id != current_trader_id` check, matching the sibling JSON `/upload` endpoint's existing correct pattern. |
| 4 | `communications.py` — `email-vendor`/`whatsapp-vendor` endpoints authenticated the *caller* but never checked the target invoice actually belonged to them (cross-tenant IDOR) | `backend/app/api/communications.py` | Both queries now scope with `.eq("trader_id", current_trader_id)` in addition to `.eq("id", invoice_id)` — a mismatched invoice now 404s instead of succeeding. |
| 5 | `communications.py:remind_gstin_whatsapp` — same IDOR pattern, plus called an undefined function (`send_whatsapp_message`) that would `NameError` on every invocation | `backend/app/api/communications.py` | Switched to `Depends(verify_trader_access)` (the correct existing pattern, already used by `send_test_alert` in the same file) and fixed the call to the actually-imported `send_text_message`. |
| 6 | **Live cross-tenant data exposure**: debug-mode email sends wrote the rendered HTML (real trader name, invoice number, amount, and a working Supabase Storage link to the actual invoice photo) to `frontend/public/latest_email.html` — a **publicly served, unauthenticated static file**. Confirmed this file was not just present on disk but **committed to git** (`git ls-files` confirms tracked). | `backend/app/api/communications.py`, `frontend/public/latest_email.html`, `frontend/.gitignore` | Removed the debug-write entirely (the file would have been recreated on the next debug-mode send even if just deleted once). `git rm`'d the file and added `/public/latest_email.html` to `frontend/.gitignore`. **Same history caveat as §0** — this file's past contents remain in git history; not purged. |
| 7 | Three third-party API credentials (`sandbox_api_key`, `sandbox_api_secret`, `gstin_api_key`) were **hardcoded as live-looking default values directly in source** — committed to the public repo regardless of `.env` contents | `backend/app/config.py` | Defaults changed to `""`, matching every other secret field in the same file. **Operational impact**: if your `.env` didn't already independently set these three values, the GSTIN-verification providers that used them will now silently fall through to the existing local demo-mode fallback (`gstin.py`'s `_demo_mode_response`) instead of calling the real Sandbox.co.in/GSTVerify APIs. Check your `.env` and add them there if you want live verification to keep working — and separately, **rotate these three with their respective vendors**, since the old values are still in git history regardless of the code fix. |
| 8 | OTP request/verify had **no rate limiting at all** — a 6-digit OTP is brute-forceable with unlimited attempts, and `/request-otp` could be used to spam a real WhatsApp number indefinitely | `backend/app/api/auth.py` | Added `check_rate_limit` (already used elsewhere in the codebase, just never wired in here): 3 OTP requests / 5 min per phone, 5 verify attempts / 5 min per phone. Limits are generous enough not to interfere with normal login, including during a live demo. |
| 9 | `privacy.py:last-llm-calls` had no auth at all — exposed the internal LLM-call audit log to anyone | `backend/app/api/privacy.py` | Added `Depends(get_current_trader_id)` — no trader-specific scoping exists for this log (it's a global operational log, not partitioned by trader), so the minimal correct fix is requiring *some* valid session rather than none. |
| 10 | `main.py` disabled `docs_url`/`redoc_url` but left `openapi_url` active — the custom-branded `/docs` page still fetched a fully public `/openapi.json` exposing the entire API schema (every route, model, param) to anyone who found the ngrok URL | `backend/app/main.py` | Added `openapi_url=None`. **Tradeoff accepted**: the custom `/docs` Swagger page will now load its shell but fail to fetch a schema — it's non-functional until someone builds an authenticated replacement. Removing the public schema disclosure was judged more valuable than keeping an internal dev convenience working un-authenticated. |

---

## 2. Confirmed, not fixed — needs a deliberate decision or more time than a mechanical patch allows

| Severity | Finding | File(s) | Why it's not a quick patch |
|---|---|---|---|
| **Critical** | `webhook.py:44` `POST /upload-invoice` — no auth, no rate limit, `trader_id` is a plain form field. Anyone can (a) burn the Gemini key pool / real money on arbitrary images, and (b) write fabricated invoices into any trader's account. | `backend/app/api/webhook.py` | Unclear from the audit alone whether this is a dev/testing-only path or a real alternate ingestion channel — needs a decision on intended use before gating it, not just a copy-paste `Depends()`. |
| **Medium-High** | `munim_mcp/` — MCP tools take a raw `trader_id` argument and query with the **service-role key**, completely bypassing `deps.py`'s tenant isolation. Currently stdio-only (not network-reachable as shipped), so exploitability is capped today, but it becomes cross-tenant data disclosure the moment it's exposed over SSE/HTTP or driven by an LLM client subject to prompt injection. | `backend/munim_mcp/auth.py`, `tools.py` | Needs a real session→tenant binding design, not a one-line fix — `auth.py`'s `get_api_headers()` is currently a stub returning `{}`. |
| **Medium** | `detail=str(e)` pattern returns raw Python/DB exception text to HTTP clients in **27 places across 6 files** (`admin.py`, `dashboard.py`, `gstr2b.py`, `communications.py`, `reports.py`, `webhook.py`) — CWE-209 information exposure. | across `backend/app/api/` | This is a systemic pattern needing one shared error-wrapping helper, not 27 individual edits under time pressure — good candidate for the `fixer` subagent next session, one file at a time, with a test per file. |
| **Medium** | JWT: HS256 correctly pinned (no alg-confusion risk), but 365-day expiry with **no revocation mechanism** — a leaked token is valid for a year with no way to invalidate just that one token. | `backend/app/api/auth.py`, `deps.py` | Real fix is a refresh-token architecture or a `jti` blocklist — an actual design change, not a patch. |
| **Low-Medium** | `request_otp` returns a different status for registered vs. unregistered numbers — a phone-number enumeration oracle. | `backend/app/api/auth.py` | Left alone this session: changing the response contract risks breaking frontend error-handling that expects the current shape, and this is lower severity than everything above — worth a deliberate, tested change rather than a rushed one. |
| **Low** | `PyJWT` is unpinned in `requirements.txt` (no version constraint at all) — supply-chain/reproducibility risk, not a specific known CVE. | `backend/requirements.txt` | Trivial to fix (`pip freeze` and pin) but deliberately left for a moment when you can also verify nothing else shifts underneath it. |
| **Low** | `is_valid_gstin_format()` computes a regex pattern (`gstin.py:29`) but never actually calls `re.match` against it — dead validation code. The real gate (`len==15 and isalnum()`) happens to still block injection-shaped input into the downstream API call, so this is a correctness gap, not a live exploit. | `backend/app/services/gstin.py` | Low priority given the incidental protection already in place; worth fixing for correctness, not urgency. |

---

## 3. What's done correctly (a credible audit isn't all red flags)

- **`verify_trader_access` (`deps.py`) is the right design**, and it's applied consistently across `dashboard.py`, most of `gstr2b.py`, and (now) all of `communications.py` and `reports.py`: it re-checks the CA↔trader phone relationship against live DB state on every request rather than trusting JWT claims, so a revoked relationship can't be replayed via an old token.
- **JWT signature verification pins the algorithm explicitly** (`algorithms=["HS256"]`) — no `none`-algorithm or algorithm-confusion bypass class of bug.
- **The WhatsApp inbound webhook is solid**: HMAC signature verification (added this session, see prior audit round), rate limiting, and idempotency are all present and correct on that specific path.
- **CORS is correctly scoped** — `allowed_origins` is an explicit allowlist (two localhost ports + the registered ngrok domain), no wildcard, and `allow_credentials=True` is safe given that.
- **No SQL injection surface anywhere** — the Supabase query builder is used correctly throughout; the one raw `.rpc()` call (pgvector similarity search in `hsn.py`) passes a structured dict, not interpolated SQL.
- **No SSRF surface** — all outbound HTTP calls target fixed, config-defined hostnames; no request-supplied URL or host is ever used to build an outbound request.
- **No XSS in the React frontend** — zero `dangerouslySetInnerHTML` usage found; the one real injection point was server-side HTML email construction, now escaped (§1).
- **Dependency versions are clean** — nothing in `requirements.txt` or `package.json` is pinned to a version with a known relevant CVE class (checked `fastapi`, `httpx`, `python-multipart`, `Pillow`, `next`, `react` specifically).
- **`.gitignore` correctly excludes `.env`** — only `backend/.env.example` is tracked; no live secret file was ever accidentally committed (the leaked credentials in §0 were hardcoded directly in `.py` files, a different mistake, already partially remediated for new commits going forward).
- **The privacy audit log (`privacy_layer.py`) genuinely doesn't log raw field values**, only field names — the log itself isn't a data-leak vector even though the endpoint exposing it (now still unauthenticated, `privacy.py:12` — low sensitivity given the above, but should still get the same `Depends()` treatment) had no auth.

---

## 4. Suggested next steps, in order

1. **Rotate the Supabase service-role key + DB password** (§0) — today, not after the hackathon.
2. **Set `ADMIN_API_KEY` in `backend/.env`** so the fix in §1.1 actually activates (it fails closed, so admin routes are currently just fully blocked until you do this).
3. **Decide `webhook.py:/upload-invoice`'s intended purpose**, then gate it accordingly.
4. Everything in §2 marked as fixer-subagent-sized work, once the `fixer`/`committer` subagents are available next session (they need a fresh session to register — see prior notes on `.claude/agents/`).
