// The backend's /api/v1/admin/* router requires this header (see
// ADMIN_API_KEY in backend/.env) since it has no per-user login of its
// own -- it's a shared dev/ops surface (Gemini key pool, system status,
// admin invoice delete), not something a trader or CA authenticates into.
//
// This key is NEVER built into the bundle. It used to come from
// NEXT_PUBLIC_ADMIN_API_KEY, which Next.js inlines into the client
// JavaScript -- meaning the production key that gates DELETE
// /api/v1/admin/invoices/{id} was downloadable by anyone who opened the
// site. An operator now types it once per browser session instead; it
// lives in sessionStorage and nowhere else, so it is never published to
// the repo, the build logs, or the served bundle.
const ADMIN_KEY_STORAGE = "munim_admin_key";

export const getAdminKey = () => {
  if (typeof window === "undefined") return "";
  try {
    return sessionStorage.getItem(ADMIN_KEY_STORAGE) || "";
  } catch {
    return "";
  }
};

export const setAdminKey = (key) => {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(ADMIN_KEY_STORAGE, (key || "").trim());
  } catch {
    /* private mode / storage disabled -- admin calls will 403, which is correct */
  }
};

export const clearAdminKey = () => {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(ADMIN_KEY_STORAGE);
  } catch {
    /* nothing to clear */
  }
};

export const adminHeaders = () => {
  const key = getAdminKey();
  return key ? { "X-Admin-Key": key } : {};
};

// Ask for the key once per session. Only the internal ops surfaces (/dev,
// /admin) should call this -- user-facing pages like /dashboard render
// admin-backed widgets too, and a CA must never be prompted for an ops
// credential. Those callers just use adminHeaders() and degrade quietly
// to an empty header when no key is present.
export const ensureAdminKey = () => {
  if (typeof window === "undefined") return "";
  if (getAdminKey()) return getAdminKey();
  const entered = window.prompt(
    "Admin key required for this internal tool.\n\n" +
      "Held in this browser session only -- it is not stored in the app bundle."
  );
  if (entered && entered.trim()) setAdminKey(entered);
  return getAdminKey();
};

// Uploads a recorded voice-query clip (see utils/voiceRecording.js) to the
// backend for transcription and returns the transcript text. Thin wrapper
// so VoiceQueryButton.js doesn't need to know the endpoint shape.
export const transcribeAudio = async (apiBase, blob) => {
  const formData = new FormData();
  formData.append("audio", blob, "voice-query.webm");
  const res = await authFetch(`${apiBase}/api/v1/dashboard/transcribe-audio`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Transcription failed");
  const data = await res.json();
  return data.text || "";
};

// Sends a transcribed voice (or future typed) question to the same
// LLM-backed answer engine WhatsApp's text/voice queries already use
// (backend/app/services/gemini.py::answer_trader_question, via the new
// /dashboard/ask/{traderId} endpoint) -- real, flexible answers instead of
// utils/voiceIntent.js's fixed 3-intent local matcher.
export const askTraderQuestion = async (apiBase, traderId, question) => {
  const res = await authFetch(`${apiBase}/api/v1/dashboard/ask/${traderId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error("Ask failed");
  const data = await res.json();
  return data.answer || "";
};

// Input tax credit a supplier has already reported to the portal but the
// trader never claimed, i.e. GSTR-2B rows with no invoice matched to them.
// Deliberately hits the read-only endpoint: /gstr2b/reconcile computes the
// same figure but also writes match results and can fire vendor warnings,
// so it must never be called just to render a number.
export const getMissedItc = async (apiBase, traderId, month, year) => {
  const qs = new URLSearchParams();
  if (month) qs.set("month", String(month));
  if (year) qs.set("year", String(year));
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await authFetch(`${apiBase}/api/v1/gstr2b/missed-itc/${traderId}${suffix}`);
  if (!res.ok) throw new Error(`Could not load unclaimed credit (HTTP ${res.status})`);
  return res.json();
};

// A request that never settles is worse than one that fails: the panel spins
// forever and the user cannot tell a slow network from a dead backend.
//
// The ceiling has to clear this app's genuinely slow work, not just a typical
// REST read. Invoice upload runs vision OCR through the LLM pipeline, report
// generation and voice transcription are both model calls, and a Cloud Run
// cold start sits on top of any of them. Two minutes covers all of those with
// room to spare while still failing a dead backend in bounded time.
//
// Reconciliation is the exception and passes its own timeoutMs: it does two
// database writes per invoice, so a full month of a few hundred invoices runs
// for minutes by design. Anything long-running should opt in explicitly
// rather than the default being stretched to fit the slowest thing here.
const DEFAULT_TIMEOUT_MS = 120000;

export const authFetch = async (url, options = {}) => {
  options.cache = 'no-store';
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('munim_auth_token');
    if (token) {
      options.headers = {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      };
    }
  }

  let timer;
  if (!options.signal && typeof AbortController !== 'undefined') {
    const controller = new AbortController();
    options.signal = controller.signal;
    timer = setTimeout(() => controller.abort(), options.timeoutMs || DEFAULT_TIMEOUT_MS);
  }
  delete options.timeoutMs;

  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    // Surface an abort as something a human can act on. Left raw it reads as
    // "AbortError: signal is aborted without reason", which tells nobody
    // anything -- and PanelState renders whatever message it is handed.
    if (err?.name === 'AbortError') {
      throw new Error('The server took too long to respond. It may be starting up — try again.');
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }

  if (res.status === 401 && typeof window !== 'undefined') {
    // Prevent redirect loop if already on login page or dev portal
    if (window.location.pathname !== "/" && window.location.pathname !== "/dev") {
      localStorage.removeItem('munim_auth_token');
      localStorage.removeItem('munim_auth_trader');
      window.location.href = "/";
    }
  }
  
  return res;
};

// --- The CA's practice view ---------------------------------------------
//
// Every client at once, ranked by rupees at risk. Slow by nature: it reads
// every invoice and GSTR-2B row the practice owns, so the default 120s ceiling
// applies rather than a shorter one.

export const getPracticeOverview = async (apiBase) => {
  const res = await authFetch(`${apiBase}/api/v1/practice/overview`);
  if (!res.ok) throw new Error(`Could not load your practice (HTTP ${res.status})`);
  return res.json();
};

export const getClientBrief = async (apiBase, traderId) => {
  const res = await authFetch(`${apiBase}/api/v1/practice/client/${traderId}/brief`);
  if (!res.ok) throw new Error(`Could not load this client's brief (HTTP ${res.status})`);
  return res.json();
};

// --- Missed-ITC recovery -------------------------------------------------

// Sends a real WhatsApp message to a real trader, so it is never called on
// render. The response's `status` distinguishes "sent" from every reason
// nothing was sent (not reconciled, nothing unclaimed, already asked, no
// number on file) -- the caller must show that, not assume success.
export const askTraderForMissingBills = async (apiBase, traderId, { month, year, limit } = {}) => {
  const res = await authFetch(`${apiBase}/api/v1/gstr2b/missed-itc/${traderId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ month: month || null, year: year || null, limit: limit || 3 }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Could not send the request (HTTP ${res.status})`);
  return data;
};

export const getRecoveryRequests = async (apiBase, traderId) => {
  const res = await authFetch(`${apiBase}/api/v1/gstr2b/missed-itc/${traderId}/requests`);
  if (!res.ok) throw new Error(`Could not load recovery requests (HTTP ${res.status})`);
  return res.json();
};

// --- Statutory citation --------------------------------------------------

// "Says who?" for one invoice. `citation` may legitimately be null -- the
// backend refuses to quote a clause it cannot trace the verdict to, and the
// UI renders that absence rather than inventing a section number.
export const explainInvoice = async (apiBase, invoiceId) => {
  const res = await authFetch(`${apiBase}/api/v1/dashboard/explain/${invoiceId}`);
  if (!res.ok) throw new Error(`Could not load the explanation (HTTP ${res.status})`);
  return res.json();
};

// --- Network supplier intelligence ---------------------------------------

export const getSupplierNetwork = async (apiBase, traderId) => {
  const res = await authFetch(`${apiBase}/api/v1/dashboard/supplier-network/${traderId}`);
  if (!res.ok) throw new Error(`Could not load supplier network data (HTTP ${res.status})`);
  return res.json();
};

// --- Vendor fix links ----------------------------------------------------

export const createVendorFixLink = async (apiBase, invoiceId) => {
  const res = await authFetch(`${apiBase}/api/v1/vendor/link/${invoiceId}`, { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Could not create a link (HTTP ${res.status})`);
  return data;
};

export const getVendorResponses = async (apiBase, traderId) => {
  const res = await authFetch(`${apiBase}/api/v1/vendor/responses/${traderId}`);
  if (!res.ok) throw new Error(`Could not load vendor responses (HTTP ${res.status})`);
  return res.json();
};

// The two public ones. Deliberately plain fetch, not authFetch: the vendor
// page is opened by a supplier who has no Munim account, and attaching a
// stale Authorization header from whoever last used this browser would be
// both pointless and a way to leak one.
export const openVendorFix = async (apiBase, token) => {
  const res = await fetch(`${apiBase}/api/v1/vendor/fix/${token}`, { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "This link is not valid.");
  return data;
};

export const submitVendorFix = async (apiBase, token, body) => {
  const res = await fetch(`${apiBase}/api/v1/vendor/fix/${token}/respond`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Could not record your answer.");
  return data;
};
