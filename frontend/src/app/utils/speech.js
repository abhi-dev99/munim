// On-device text-to-speech for the trader PWA, built on the browser's native
// Web Speech API (`window.speechSynthesis`). No network call, no external
// model — the synthesis runs entirely on the device's own OS/browser TTS
// engine. This exists for accessibility: many MSME shopkeepers Munim serves
// have limited literacy, and hearing the `diagnosis_hi` verdict aloud matters
// more than reading it. (See VOI-2 in IQOO_DEVICE_CAPABILITY_SPEC.md.)

/**
 * Feature-detect Web Speech API support. Some in-app webviews and older
 * browsers don't implement it — callers should hide/disable UI rather than
 * calling speakText/stopSpeaking when this is false.
 */
export function isSpeechSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/**
 * Current voices known to the browser. May be empty on first call in some
 * browsers (notably Chrome) until the async `voiceschanged` event fires —
 * speakText() below handles that case.
 */
export function getVoices() {
  if (!isSpeechSupported()) return [];
  return window.speechSynthesis.getVoices() || [];
}

/**
 * Pure selection logic (no browser APIs touched) — pick the best available
 * voice for a target language tag from a list of voice-like objects
 * ({ lang, default, ... }). Exported standalone so it can be unit tested
 * with plain mock objects instead of real SpeechSynthesisVoice instances.
 *
 * Preference order:
 *   1. Exact lang match (e.g. "hi-IN" === "hi-IN")
 *   2. Same base language (e.g. "hi-IN" -> any "hi-*" voice), preferring
 *      the browser's marked default among those
 *   3. Browser's overall default voice
 *   4. First voice in the list
 *   5. null if the list is empty
 */
export function pickVoice(voices, lang) {
  if (!Array.isArray(voices) || voices.length === 0) return null;

  const target = String(lang || "").toLowerCase();
  const targetBase = target.split("-")[0];

  const exact = voices.find((v) => String(v?.lang || "").toLowerCase() === target);
  if (exact) return exact;

  const sameBase = voices.filter(
    (v) => String(v?.lang || "").toLowerCase().split("-")[0] === targetBase && targetBase
  );
  if (sameBase.length > 0) {
    return sameBase.find((v) => v?.default) || sameBase[0];
  }

  const browserDefault = voices.find((v) => v?.default);
  if (browserDefault) return browserDefault;

  return voices[0];
}

/**
 * Speak `text` aloud on-device. Cancels any speech already in progress first
 * (only one diagnosis should ever be read at a time). Returns false without
 * doing anything if speech synthesis isn't supported or there's no text.
 */
export function speakText(text, { lang = "hi-IN", onStart, onEnd, onError } = {}) {
  if (!isSpeechSupported() || !text) return false;

  const synth = window.speechSynthesis;
  synth.cancel();

  const utter = new window.SpeechSynthesisUtterance(text);
  utter.lang = lang;
  utter.onstart = () => onStart?.();
  utter.onend = () => onEnd?.();
  utter.onerror = (event) => onError?.(event);

  const applyVoice = () => {
    const voice = pickVoice(getVoices(), lang);
    if (voice) utter.voice = voice;
  };

  const existingVoices = getVoices();
  if (existingVoices.length > 0) {
    applyVoice();
    synth.speak(utter);
  } else {
    // Chrome loads voices asynchronously; wait once for them, but don't
    // block forever — speak with the lang tag alone if they never arrive.
    let spoken = false;
    const speakOnce = () => {
      if (spoken) return;
      spoken = true;
      applyVoice();
      synth.speak(utter);
    };
    synth.addEventListener?.("voiceschanged", speakOnce, { once: true });
    setTimeout(speakOnce, 250);
  }

  return true;
}

/** Stop any in-progress on-device speech immediately. */
export function stopSpeaking() {
  if (!isSpeechSupported()) return;
  window.speechSynthesis.cancel();
}

/** Whether the browser is currently speaking something we started. */
export function isSpeaking() {
  if (!isSpeechSupported()) return false;
  return window.speechSynthesis.speaking;
}
