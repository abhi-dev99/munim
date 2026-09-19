// Raw audio capture for the trader PWA's voice-query button, built on
// getUserMedia()/MediaRecorder rather than the Web Speech API
// (utils/voiceRecognition.js's approach). Reason for the split: the Web
// Speech API's SpeechRecognition interface is unsupported inside Android's
// System WebView -- exactly the environment the mobile app's native shell
// embeds this page in (react-native-webview wraps System WebView, not
// Chrome) -- so VoiceQueryButton.js's mic never even rendered there.
// getUserMedia/MediaRecorder ARE supported by System WebView (they're
// standard Chromium APIs, not the special Google-service integration
// SpeechRecognition needs), and react-native-webview's Android
// implementation already auto-grants a getUserMedia("audio") request
// against the app's existing RECORD_AUDIO manifest permission with no
// native code changes needed on this app's side (see
// RNCWebChromeClient.java's onPermissionRequest, which maps
// RESOURCE_AUDIO_CAPTURE straight to that permission).
//
// This module only captures raw audio -- turning it into text is
// utils/api.js's transcribeAudio(), which uploads to the backend's
// /dashboard/transcribe-audio endpoint (same Groq Whisper call
// webhook.py's WhatsApp voice-note handler already uses). Turning the
// transcript into an answer stays utils/voiceIntent.js's job, entirely
// unchanged by this module.

/** Feature-detect getUserMedia + MediaRecorder support. */
export function isRecordingSupported() {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined"
  );
}

/**
 * Opens the mic and starts recording. Returns the active MediaRecorder (so
 * the caller can pass it to stopRecording()), or null if unsupported/denied.
 *
 * @param {object} opts
 * @param {() => void} [opts.onStart] called once the mic is actually open.
 * @param {(error: string, detail?: string) => void} [opts.onError] short
 *   error code: "unsupported" | "not-allowed" | "start-failed", plus the
 *   real `Error.name`/`message` as `detail` -- surfaced so a real-device
 *   failure is actually diagnosable from what the UI shows, not just
 *   "something went wrong" (this API has enough distinct failure modes
 *   across different WebView/Android versions that guessing which one hit
 *   without the real error text is unreliable).
 */
export async function startRecording({ onStart, onError } = {}) {
  if (!isRecordingSupported()) {
    onError?.("unsupported");
    return null;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = window.MediaRecorder.isTypeSupported?.("audio/webm") ? "audio/webm" : "";
    const recorder = new window.MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) chunks.push(event.data);
    });
    // Stashed on the instance rather than a module-level variable so two
    // VoiceQueryButton instances (unlikely today, but cheap to get right)
    // never share state.
    recorder.__chunks = chunks;
    recorder.start();
    onStart?.();
    return recorder;
  } catch (err) {
    const code = err?.name === "NotAllowedError" ? "not-allowed" : "start-failed";
    onError?.(code, `${err?.name || "Error"}: ${err?.message || String(err)}`);
    return null;
  }
}

/**
 * Stops an in-progress recording and resolves with the captured audio Blob.
 * Also stops the underlying media stream tracks, releasing the mic (and
 * clearing the OS mic-in-use indicator) rather than leaving it open.
 */
export function stopRecording(recorder) {
  return new Promise((resolve, reject) => {
    if (!recorder) {
      reject(new Error("No active recording"));
      return;
    }
    recorder.addEventListener(
      "stop",
      () => {
        recorder.stream.getTracks().forEach((track) => track.stop());
        resolve(new Blob(recorder.__chunks, { type: recorder.mimeType || "audio/webm" }));
      },
      { once: true },
    );
    recorder.stop();
  });
}
