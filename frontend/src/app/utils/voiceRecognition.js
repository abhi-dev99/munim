// On-device speech-to-text for the trader PWA, built on the browser's
// native Web Speech API (`window.SpeechRecognition` /
// `window.webkitSpeechRecognition`). On many Android browsers (Chrome
// included) recognition for on-device-capable languages runs locally on
// the device rather than round-tripping audio to a cloud service — no
// server call from this app either way. This is the input-side
// counterpart to utils/speech.js's on-device TTS: many MSME shopkeepers
// Munim serves are more comfortable speaking than typing, especially in
// Hindi. (See VOI-3 in IQOO_DEVICE_CAPABILITY_SPEC.md.)
//
// This module only wraps the browser API (start/stop/events) — it does
// NOT interpret what was said. Turning the transcript into an answer is
// utils/voiceIntent.js's job, kept separate so that logic stays pure and
// unit-testable.

/**
 * Feature-detect the Web Speech API's recognition side. Support is
 * inconsistent across browsers (notably missing in Firefox and many
 * in-app webviews) — callers should hide/disable mic UI rather than
 * calling startListening() when this is false.
 */
export function isRecognitionSupported() {
  return (
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
  );
}

function getRecognitionCtor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

/**
 * Start on-device speech recognition for a single query. Configured for
 * Hindi (`hi-IN`) by default since the trader base is Hindi-first, with a
 * caller-supplied fallback to the browser default when Hindi recognition
 * isn't available on the device.
 *
 * Returns the recognition instance (so the caller can abort() it early,
 * e.g. if the user navigates away), or null if unsupported.
 *
 * @param {object} opts
 * @param {string} [opts.lang="hi-IN"]
 * @param {(transcript: string) => void} [opts.onResult] called once with
 *   the final transcript when recognition succeeds.
 * @param {() => void} [opts.onStart] called when the mic actually opens.
 * @param {() => void} [opts.onEnd] called when recognition stops, success
 *   or failure — good place to reset UI state.
 * @param {(error: string) => void} [opts.onError] called with a short
 *   error code (e.g. "not-allowed", "no-speech", "network",
 *   "unsupported") on failure. "not-allowed" means the user (or the OS)
 *   denied microphone permission — the most common real-world failure.
 */
export function startListening({
  lang = "hi-IN",
  onResult,
  onStart,
  onEnd,
  onError,
} = {}) {
  const Recognition = getRecognitionCtor();
  if (!Recognition) {
    onError?.("unsupported");
    return null;
  }

  const recognition = new Recognition();
  recognition.lang = lang;
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => onStart?.();
  recognition.onend = () => onEnd?.();

  recognition.onresult = (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript || "";
    onResult?.(transcript);
  };

  recognition.onerror = (event) => {
    // event.error is one of the spec's fixed error codes: "not-allowed",
    // "no-speech", "audio-capture", "network", "aborted", etc.
    onError?.(event?.error || "unknown");
  };

  try {
    recognition.start();
  } catch (err) {
    // start() throws synchronously if called while already listening, or
    // in some browsers when the mic is unavailable.
    onError?.("start-failed");
    return null;
  }

  return recognition;
}

/** Stop an in-progress recognition instance returned by startListening(). */
export function stopListening(recognition) {
  recognition?.stop?.();
}
