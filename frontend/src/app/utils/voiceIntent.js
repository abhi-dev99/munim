// Deterministic keyword matcher for voice queries in the trader PWA.
//
// This is deliberately NOT a general NLU system — that would need an LLM
// round-trip and defeat the point of on-device speech input (see VOI-3 in
// IQOO_DEVICE_CAPABILITY_SPEC.md). Instead we recognize a small, fixed set
// of question shapes a shopkeeper is likely to ask after the on-device
// SpeechRecognition transcript comes back, using keyword/regex matching
// that tolerates Hindi, English, and Hinglish phrasing. Pure and
// browser-API-free by design, so it's fully unit-testable in Node.
//
// Known intents:
//   ITC_BALANCE      "mera ITC kitna bacha hai" / "how much ITC do I have"
//   INVOICE_COUNT    "kitne invoice hai" / "how many invoices"
//   SUPPLIER_STATUS  "supplier ka status kaisa hai" / "supplier health"
//   UNKNOWN          nothing matched — caller shows the raw transcript
//                     plus a fallback hint instead of failing silently.

export const VOICE_INTENTS = {
  ITC_BALANCE: "ITC_BALANCE",
  INVOICE_COUNT: "INVOICE_COUNT",
  SUPPLIER_STATUS: "SUPPLIER_STATUS",
  UNKNOWN: "UNKNOWN",
};

// Each pattern is a set of keyword/phrase regexes (case-insensitive). An
// intent matches when at least one "subject" term AND at least one
// "query" term are both present — this is what lets "ITC" alone (which
// could appear incidentally) require an actual question shape around it,
// while still accepting varied Hindi/English/Hinglish wording for that
// question shape.
const PATTERNS = [
  {
    intent: VOICE_INTENTS.ITC_BALANCE,
    subject: [/\bitc\b/i, /input\s*tax\s*credit/i],
    query: [/kitn[aei]/i, /bach[ae]/i, /balance/i, /how much/i, /total/i, /left/i, /remaining/i, /baki/i],
  },
  {
    intent: VOICE_INTENTS.SUPPLIER_STATUS,
    // Checked before INVOICE_COUNT so "supplier ke kitne invoice" style
    // phrasing (rare, but plausible) still resolves to supplier status
    // when a supplier-specific word is present.
    subject: [/supplier/i, /vendor/i, /vyapari/i],
    query: [/status/i, /health/i, /kaisa/i, /kaise/i, /theek/i, /kharab/i, /flag/i],
  },
  {
    intent: VOICE_INTENTS.INVOICE_COUNT,
    subject: [/invoice/i, /\bbill\b/i, /bijak/i, /chalan/i],
    query: [/kitn[aei]/i, /how many/i, /count/i, /total/i, /number of/i, /sankhya/i],
  },
];

/**
 * Match a transcribed voice query string against the known intent set.
 *
 * @param {string} transcript raw text from SpeechRecognition (any case,
 *   Hindi/English/Hinglish).
 * @returns {{ intent: string, transcript: string }} the matched intent
 *   (one of VOICE_INTENTS) plus the original transcript, trimmed. Returns
 *   VOICE_INTENTS.UNKNOWN when nothing matches, including for empty or
 *   non-string input.
 */
export function matchVoiceIntent(transcript) {
  const text = typeof transcript === "string" ? transcript.trim() : "";

  if (!text) {
    return { intent: VOICE_INTENTS.UNKNOWN, transcript: text };
  }

  for (const pattern of PATTERNS) {
    const hasSubject = pattern.subject.some((re) => re.test(text));
    const hasQuery = pattern.query.some((re) => re.test(text));
    if (hasSubject && hasQuery) {
      return { intent: pattern.intent, transcript: text };
    }
  }

  return { intent: VOICE_INTENTS.UNKNOWN, transcript: text };
}

function formatINR(n) {
  const value = Number(n) || 0;
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

/**
 * Turn a matched intent into a spoken/displayed Hindi answer, using data
 * the trader page has already fetched (dashboard summary) — deliberately
 * no new network call, since the whole point of on-device voice input is
 * a fast, local round trip, not one more request layered on top of it.
 *
 * @param {string} intent one of VOICE_INTENTS.
 * @param {object} summary the DashboardSummary object trader/page.js
 *   already holds in state (itc_buckets, invoices_processed,
 *   suppliers_monitored, issues_open).
 * @returns {string} a short Hindi sentence to display and speak back.
 */
export function answerVoiceIntent(intent, summary) {
  const s = summary || {};
  const itc = s.itc_buckets || {};

  switch (intent) {
    case VOICE_INTENTS.ITC_BALANCE:
      return `Aapka confirmed ITC ${formatINR(itc.confirmed)} hai. ${
        itc.at_risk > 0 ? `${formatINR(itc.at_risk)} at-risk hai.` : ""
      }`.trim();

    case VOICE_INTENTS.INVOICE_COUNT:
      return `Aapke ${s.invoices_processed ?? 0} invoices is mahine process ho chuke hain.`;

    case VOICE_INTENTS.SUPPLIER_STATUS:
      return s.issues_open > 0
        ? `Aap ${s.suppliers_monitored ?? 0} suppliers monitor kar rahe hain, ${s.issues_open} mein issue hai.`
        : `Aap ${s.suppliers_monitored ?? 0} suppliers monitor kar rahe hain, sab theek hain.`;

    default:
      return "Samajh nahi aaya. ITC balance ya invoice count ke baare mein poochiye.";
  }
}
