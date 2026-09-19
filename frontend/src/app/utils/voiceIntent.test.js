import { describe, it, expect } from "vitest";
import { matchVoiceIntent, VOICE_INTENTS } from "./voiceIntent";

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
