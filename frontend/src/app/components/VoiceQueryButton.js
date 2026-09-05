"use client";

import { useState, useCallback } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";
import { isRecognitionSupported, startListening, stopListening } from "../utils/voiceRecognition";
import { matchVoiceIntent, answerVoiceIntent } from "../utils/voiceIntent";

/**
 * "Ask Munim" — on-device voice query for a trader's own dashboard summary.
 * Tap the mic, ask something like "mera ITC kitna bacha hai", get an
 * instant answer from data already loaded on this page (see
 * utils/voiceIntent.js's answerVoiceIntent — no extra network call).
 *
 * Renders nothing if the browser doesn't support on-device speech
 * recognition (Firefox, many in-app webviews) rather than showing a mic
 * that silently fails when tapped.
 */
export default function VoiceQueryButton({ summary }) {
  const [state, setState] = useState("idle"); // idle | listening | answered | error
  const [answer, setAnswer] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [recognition, setRecognition] = useState(null);

  const ERROR_MESSAGES = {
    "not-allowed": "Mic permission allow karein settings mein.",
    "no-speech": "Kuch sunai nahi diya, dobara try karein.",
    unsupported: "Ye phone/browser voice input support nahi karta.",
  };

  const handleTap = useCallback(() => {
    if (state === "listening") {
      stopListening(recognition);
      return;
    }

    setAnswer("");
    setErrorMsg("");
    setState("listening");

    const rec = startListening({
      lang: "hi-IN",
      onResult: (transcript) => {
        const { intent } = matchVoiceIntent(transcript);
        setAnswer(answerVoiceIntent(intent, summary));
        setState("answered");
      },
      onError: (code) => {
        setErrorMsg(ERROR_MESSAGES[code] || "Kuch galat ho gaya, dobara try karein.");
        setState("error");
      },
      onEnd: () => {
        setState((s) => (s === "listening" ? "idle" : s));
      },
    });
    setRecognition(rec);
  }, [state, recognition, summary]);

  if (!isRecognitionSupported()) return null;

  return (
    <div className="rounded-none border border-[var(--border-subtle)] bg-white p-4">
      <div className="flex items-center gap-3">
        <button
          onClick={handleTap}
          aria-label={state === "listening" ? "Sunna band karein" : "Munim se poochein"}
          className={`flex-none w-11 h-11 rounded-none flex items-center justify-center transition-colors ${
            state === "listening" ? "bg-red-600 text-white" : "bg-black text-white hover:bg-gray-800"
          }`}
        >
          {state === "listening" ? <MicOff size={18} /> : <Mic size={18} />}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
            Munim se poochein
          </p>
          {state === "listening" && (
            <p className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5 mt-0.5">
              <Loader2 size={13} className="animate-spin" /> Sun raha hoon...
            </p>
          )}
          {state === "answered" && <p className="text-sm font-medium mt-0.5">{answer}</p>}
          {state === "error" && <p className="text-sm text-[var(--red-primary)] mt-0.5">{errorMsg}</p>}
          {state === "idle" && (
            <p className="text-xs text-[var(--text-muted)] mt-0.5">"Mera ITC kitna bacha hai?"</p>
          )}
        </div>
      </div>
    </div>
  );
}
