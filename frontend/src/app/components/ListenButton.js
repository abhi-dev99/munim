"use client";
import { useEffect, useState, useCallback } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { isSpeechSupported, speakText, stopSpeaking } from "../utils/speech";

// Reads `text` aloud on-device via the Web Speech API (see utils/speech.js).
// Renders nothing when the browser has no speechSynthesis support instead
// of showing a button that would silently do nothing (or throw).
export default function ListenButton({ text, lang = "hi-IN", className = "" }) {
  const [supported, setSupported] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    setSupported(isSpeechSupported());
  }, []);

  // Stop on-device speech if this control disappears mid-utterance (e.g.
  // the scan-result toast auto-dismisses while it's still talking).
  useEffect(() => {
    return () => stopSpeaking();
  }, []);

  const handleClick = useCallback(() => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    speakText(text, {
      lang,
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    });
  }, [speaking, text, lang]);

  if (!supported || !text) return null;

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest transition-colors ${
        speaking ? "text-[var(--red-primary)]" : "text-[var(--text-secondary)] hover:text-black"
      } ${className}`}
      aria-label={speaking ? "Stop reading diagnosis aloud" : "Listen to diagnosis"}
    >
      {speaking ? <VolumeX size={13} className="animate-pulse" /> : <Volume2 size={13} />}
      {speaking ? "Stop" : "Listen"}
    </button>
  );
}
