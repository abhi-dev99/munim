import { describe, it, expect } from "vitest";
import { pickVoice } from "./speech";

// pickVoice is the one piece of speech.js that's pure (no window/
// speechSynthesis touched), so it's the part worth unit testing — actual
// browser TTS is untestable in Node and is left to manual verification.

function voice(lang, isDefault = false, name = lang) {
  return { lang, default: isDefault, name };
}

describe("pickVoice", () => {
  it("returns null for an empty voice list", () => {
    expect(pickVoice([], "hi-IN")).toBeNull();
  });

  it("returns null when voices is not an array", () => {
    expect(pickVoice(undefined, "hi-IN")).toBeNull();
    expect(pickVoice(null, "hi-IN")).toBeNull();
  });

  it("prefers an exact lang match", () => {
    const voices = [voice("en-US"), voice("hi-IN"), voice("hi-Latn")];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("hi-IN"));
  });

  it("is case-insensitive on the lang tag", () => {
    const voices = [voice("HI-in")];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("HI-in"));
  });

  it("falls back to the same base language when no exact match exists", () => {
    const voices = [voice("en-US"), voice("hi-Latn")];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("hi-Latn"));
  });

  it("prefers the default voice among same-base-language candidates", () => {
    const voices = [voice("hi-Latn", false), voice("hi-XX", true)];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("hi-XX", true));
  });

  it("falls back to the browser's default voice when no language match exists", () => {
    const voices = [voice("en-US", false), voice("fr-FR", true)];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("fr-FR", true));
  });

  it("falls back to the first voice when nothing else matches", () => {
    const voices = [voice("en-US", false), voice("fr-FR", false)];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("en-US", false));
  });

  it("handles a missing/empty lang argument without throwing", () => {
    const voices = [voice("en-US", true), voice("hi-IN")];
    expect(pickVoice(voices, undefined)).toEqual(voice("en-US", true));
    expect(pickVoice(voices, "")).toEqual(voice("en-US", true));
  });

  it("tolerates malformed voice entries (missing lang field)", () => {
    const voices = [{ name: "broken" }, voice("hi-IN")];
    expect(pickVoice(voices, "hi-IN")).toEqual(voice("hi-IN"));
  });
});
