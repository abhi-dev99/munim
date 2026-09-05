import { describe, it, expect } from "vitest";
import { matchVoiceIntent, answerVoiceIntent, VOICE_INTENTS } from "./voiceIntent";

// matchVoiceIntent is pure keyword/regex matching over a plain string — no
// SpeechRecognition or other browser API involved — so it's fully
// unit-testable in Node, unlike the recognition wrapper around it.

describe("matchVoiceIntent", () => {
  it("matches the ITC balance intent for Hindi phrasing", () => {
    const result = matchVoiceIntent("mera ITC kitna bacha hai");
    expect(result.intent).toBe(VOICE_INTENTS.ITC_BALANCE);
    expect(result.transcript).toBe("mera ITC kitna bacha hai");
  });

  it("matches the ITC balance intent for English phrasing", () => {
    expect(matchVoiceIntent("how much ITC do I have left").intent).toBe(
      VOICE_INTENTS.ITC_BALANCE
    );
  });

  it("matches the invoice count intent for English phrasing", () => {
    expect(matchVoiceIntent("how many invoices do I have").intent).toBe(
      VOICE_INTENTS.INVOICE_COUNT
    );
  });

  it("matches the invoice count intent for Hinglish (mixed Hindi/English) phrasing", () => {
    expect(matchVoiceIntent("mere kitne invoices hai").intent).toBe(
      VOICE_INTENTS.INVOICE_COUNT
    );
  });

  it("matches the supplier status intent", () => {
    expect(matchVoiceIntent("supplier ka status kaisa hai").intent).toBe(
      VOICE_INTENTS.SUPPLIER_STATUS
    );
  });

  it("prefers supplier status over invoice count when both subjects appear", () => {
    expect(matchVoiceIntent("supplier ke kitne invoice hai, status batao").intent).toBe(
      VOICE_INTENTS.SUPPLIER_STATUS
    );
  });

  it("returns UNKNOWN for random unrelated text", () => {
    expect(matchVoiceIntent("what is the weather today").intent).toBe(
      VOICE_INTENTS.UNKNOWN
    );
  });

  it("returns UNKNOWN for a subject word with no query word", () => {
    expect(matchVoiceIntent("invoice").intent).toBe(VOICE_INTENTS.UNKNOWN);
  });

  it("returns UNKNOWN for an empty string", () => {
    const result = matchVoiceIntent("");
    expect(result.intent).toBe(VOICE_INTENTS.UNKNOWN);
    expect(result.transcript).toBe("");
  });

  it("returns UNKNOWN for whitespace-only input", () => {
    expect(matchVoiceIntent("   ").intent).toBe(VOICE_INTENTS.UNKNOWN);
  });

  it("returns UNKNOWN for non-string input without throwing", () => {
    expect(matchVoiceIntent(undefined).intent).toBe(VOICE_INTENTS.UNKNOWN);
    expect(matchVoiceIntent(null).intent).toBe(VOICE_INTENTS.UNKNOWN);
  });

  it("is case-insensitive", () => {
    expect(matchVoiceIntent("MERA ITC KITNA BACHA HAI").intent).toBe(
      VOICE_INTENTS.ITC_BALANCE
    );
  });

  it("trims surrounding whitespace from the returned transcript", () => {
    const result = matchVoiceIntent("  kitne invoice hai  ");
    expect(result.transcript).toBe("kitne invoice hai");
    expect(result.intent).toBe(VOICE_INTENTS.INVOICE_COUNT);
  });
});

describe("answerVoiceIntent", () => {
  const summary = {
    itc_buckets: { confirmed: 99820, at_risk: 15000 },
    invoices_processed: 583,
    suppliers_monitored: 26,
    issues_open: 3,
  };

  it("answers ITC balance from the already-loaded summary, no new call", () => {
    const answer = answerVoiceIntent(VOICE_INTENTS.ITC_BALANCE, summary);
    expect(answer).toContain("₹99,820");
    expect(answer).toContain("₹15,000");
  });

  it("omits the at-risk clause when nothing is at risk", () => {
    const answer = answerVoiceIntent(VOICE_INTENTS.ITC_BALANCE, {
      itc_buckets: { confirmed: 5000, at_risk: 0 },
    });
    expect(answer).toContain("₹5,000");
    expect(answer).not.toContain("at-risk");
  });

  it("answers invoice count from the summary", () => {
    expect(answerVoiceIntent(VOICE_INTENTS.INVOICE_COUNT, summary)).toContain("583");
  });

  it("answers supplier status, flagging open issues", () => {
    const answer = answerVoiceIntent(VOICE_INTENTS.SUPPLIER_STATUS, summary);
    expect(answer).toContain("26");
    expect(answer).toContain("3");
  });

  it("reports all-clear when no supplier issues are open", () => {
    const answer = answerVoiceIntent(VOICE_INTENTS.SUPPLIER_STATUS, {
      suppliers_monitored: 10,
      issues_open: 0,
    });
    expect(answer.toLowerCase()).toContain("theek");
  });

  it("gives a helpful fallback for UNKNOWN without throwing", () => {
    expect(() => answerVoiceIntent(VOICE_INTENTS.UNKNOWN, summary)).not.toThrow();
    expect(answerVoiceIntent(VOICE_INTENTS.UNKNOWN, summary).length).toBeGreaterThan(0);
  });

  it("does not throw when summary is missing or incomplete", () => {
    expect(() => answerVoiceIntent(VOICE_INTENTS.ITC_BALANCE, undefined)).not.toThrow();
    expect(() => answerVoiceIntent(VOICE_INTENTS.ITC_BALANCE, {})).not.toThrow();
  });
});
