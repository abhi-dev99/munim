"use client";

import { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";
import { X, QrCode, XCircle, Copy, Check, ExternalLink } from "lucide-react";
import { authFetch } from "../utils/api";
import { extractJoinCode } from "../utils/onboardLink";
import useModalA11y from "./useModalA11y";

// No bundled WhatsApp asset anywhere in this repo -- a small hand-drawn
// glyph avoids pulling in a new dependency or asset file for one icon.
function WhatsAppLogo({ size = 28 }) {
  return (
    <div
      className="rounded-full bg-[#25D366] flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6} fill="white">
        <path d="M12.04 2c-5.46 0-9.9 4.44-9.9 9.9 0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38c1.45.79 3.08 1.21 4.79 1.21 5.46 0 9.9-4.44 9.9-9.9s-4.44-9.93-9.9-9.93zm0 18.1c-1.5 0-2.97-.4-4.25-1.16l-.3-.18-3.12.82.83-3.04-.2-.31a8.15 8.15 0 0 1-1.25-4.33c0-4.51 3.67-8.19 8.2-8.19 2.19 0 4.25.85 5.8 2.4a8.13 8.13 0 0 1 2.4 5.8c0 4.51-3.68 8.19-8.11 8.19zm4.48-6.13c-.25-.12-1.46-.72-1.68-.8-.23-.08-.39-.12-.56.12-.16.25-.64.8-.78.96-.14.16-.29.18-.53.06-.25-.12-1.04-.38-1.99-1.22-.73-.66-1.23-1.46-1.37-1.71-.14-.25-.02-.38.11-.5.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.16.04-.31-.02-.43-.06-.12-.56-1.35-.77-1.85-.2-.48-.41-.42-.56-.43h-.48c-.16 0-.43.06-.66.31-.23.25-.86.84-.86 2.05 0 1.21.88 2.38 1 2.54.12.16 1.74 2.66 4.22 3.73.59.25 1.05.4 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.46-.6 1.66-1.17.21-.58.21-1.08.15-1.18-.06-.11-.23-.17-.48-.29z" />
      </svg>
    </div>
  );
}

export default function OnboardTraderModal({ isOpen, onClose, apiBase = "http://localhost:8000" }) {
  const [deepLink, setDeepLink] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [webAppCopied, setWebAppCopied] = useState(false);
  const canvasRef = useRef(null);
  const webAppCanvasRef = useRef(null);
  const dialogRef = useRef(null);

  useModalA11y(dialogRef, { active: isOpen, onClose });

  // The web-app QR doesn't need a backend round trip at all -- it's just
  // this deployed frontend's own /trader route, computable the moment the
  // modal opens. Kept entirely independent of the WhatsApp QR's fetch/error
  // state below, so one failing never blocks the other.
  const webAppLink = typeof window !== "undefined" ? `${window.location.origin}/trader` : "";

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setErrorMsg("");
    setDeepLink(null);
    authFetch(`${apiBase}/api/v1/dashboard/onboard-link`)
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to fetch onboarding link");
        const data = await res.json();
        setDeepLink(data.deep_link);
      })
      .catch(() => setErrorMsg("Could not load the onboarding QR code. Please try again."))
      .finally(() => setLoading(false));
  }, [isOpen, apiBase]);

  useEffect(() => {
    if (!deepLink || !canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, deepLink, { width: 140, margin: 1 }, (err) => {
      if (err) setErrorMsg("Could not render the QR code.");
    });
  }, [deepLink]);

  useEffect(() => {
    if (!isOpen || !webAppLink || !webAppCanvasRef.current) return;
    QRCode.toCanvas(webAppCanvasRef.current, webAppLink, { width: 140, margin: 1 }, () => {
      // Silently ignore -- the web-app QR is a nice-to-have alongside the
      // WhatsApp one, not something worth its own error banner.
    });
  }, [isOpen, webAppLink]);

  if (!isOpen) return null;

  const joinCode = extractJoinCode(deepLink);

  const handleCopy = () => {
    if (!deepLink) return;
    navigator.clipboard.writeText(deepLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleWebAppCopy = () => {
    if (!webAppLink) return;
    navigator.clipboard.writeText(webAppLink);
    setWebAppCopied(true);
    setTimeout(() => setWebAppCopied(false), 1500);
  };

  const goTo = (url) => {
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboard-trader-title"
        tabIndex={-1}
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full flex flex-col overflow-hidden border border-gray-100 outline-none"
      >
        <div className="px-5 py-4 bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-between border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-500/20 rounded-xl border border-emerald-500/30 text-[#10b981]">
              <QrCode size={18} aria-hidden="true" />
            </div>
            <h2 id="onboard-trader-title" className="font-extrabold text-sm tracking-tight">Onboard a New Trader</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close onboarding dialog"
            className="p-2 hover:bg-gray-700/70 rounded-lg text-gray-300 hover:text-white transition-colors"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="p-6 flex flex-col sm:flex-row gap-6 sm:gap-4 items-start justify-center">
          {/* Option 1: WhatsApp onboarding -- depends on the backend call above */}
          <div className="flex flex-col items-center gap-3 flex-1 min-w-0">
            <WhatsAppLogo />
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">WhatsApp</p>
            {errorMsg && (
              <div className="w-full p-3 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200 flex items-center gap-2">
                <XCircle size={15} />
                <span>{errorMsg}</span>
              </div>
            )}
            {loading ? (
              <div className="h-[140px] w-[140px] bg-gray-100 rounded-xl animate-pulse" />
            ) : deepLink ? (
              <>
                <canvas ref={canvasRef} role="img" aria-label="QR code that opens a WhatsApp chat with Munim to onboard this trader" className="rounded-xl border border-gray-200" />
                {joinCode && (
                  <p className="text-xs text-gray-500 text-center">
                    Or send <span className="font-mono font-bold text-gray-700">JOIN-{joinCode}</span> manually
                  </p>
                )}
                <div className="w-full flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    aria-label="Copy the WhatsApp onboarding link"
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-lg transition-colors"
                  >
                    {copied ? <Check size={13} className="text-[#10b981]" /> : <Copy size={13} />}
                    <span>{copied ? "Copied!" : "Copy link"}</span>
                  </button>
                  <button
                    onClick={() => goTo(deepLink)}
                    aria-label="Open the WhatsApp onboarding link in a new tab"
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-[#25D366] hover:bg-[#20b858] text-black text-xs font-semibold rounded-lg transition-colors"
                  >
                    <ExternalLink size={13} />
                    <span>Go to link</span>
                  </button>
                </div>
              </>
            ) : null}
          </div>

          <div className="hidden sm:block w-px bg-gray-100 self-stretch" />
          <div className="sm:hidden h-px bg-gray-100 w-full" />

          {/* Option 2: straight to the web app -- computed client-side, no backend call, no WhatsApp needed */}
          <div className="flex flex-col items-center gap-3 flex-1 min-w-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icons/icon-192.png" alt="Munim.ai logo" className="w-7 h-7 rounded-lg" />
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Munim web app</p>
            <canvas ref={webAppCanvasRef} role="img" aria-label="QR code that opens the Munim web app for this trader" className="rounded-xl border border-gray-200" />
            <div className="w-full flex items-center gap-2">
              <button
                onClick={handleWebAppCopy}
                aria-label="Copy the Munim web app link"
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-lg transition-colors"
              >
                {webAppCopied ? <Check size={13} className="text-[#10b981]" /> : <Copy size={13} />}
                <span>{webAppCopied ? "Copied!" : "Copy link"}</span>
              </button>
              <button
                onClick={() => goTo(webAppLink)}
                aria-label="Open the Munim web app in a new tab"
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                <ExternalLink size={13} />
                <span>Go to link</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
