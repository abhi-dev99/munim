"use client";

import { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";
import { X, QrCode, XCircle, Copy, Check } from "lucide-react";
import { authFetch } from "../utils/api";
import { extractJoinCode } from "../utils/onboardLink";

export default function OnboardTraderModal({ isOpen, onClose, apiBase = "http://localhost:8000" }) {
  const [deepLink, setDeepLink] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef(null);

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
    QRCode.toCanvas(canvasRef.current, deepLink, { width: 220, margin: 1 }, (err) => {
      if (err) setErrorMsg("Could not render the QR code.");
    });
  }, [deepLink]);

  if (!isOpen) return null;

  const joinCode = extractJoinCode(deepLink);

  const handleCopy = () => {
    if (!deepLink) return;
    navigator.clipboard.writeText(deepLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full flex flex-col overflow-hidden border border-gray-100">
        <div className="px-5 py-4 bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-between border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-500/20 rounded-xl border border-emerald-500/30 text-[#10b981]">
              <QrCode size={18} />
            </div>
            <h2 className="font-extrabold text-sm tracking-tight">Onboard a New Trader</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700/70 rounded-lg text-gray-300 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 flex flex-col items-center gap-4">
          {errorMsg && (
            <div className="w-full p-3 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200 flex items-center gap-2">
              <XCircle size={15} />
              <span>{errorMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="h-[220px] w-[220px] bg-gray-100 rounded-xl animate-pulse" />
          ) : deepLink ? (
            <>
              <canvas ref={canvasRef} className="rounded-xl border border-gray-200" />
              <p className="text-sm font-semibold text-gray-800 text-center">
                Scan to onboard on WhatsApp
              </p>
              {joinCode && (
                <p className="text-xs text-gray-500 text-center">
                  Or send <span className="font-mono font-bold text-gray-700">JOIN-{joinCode}</span> to
                  Munim on WhatsApp manually
                </p>
              )}
              <button
                onClick={handleCopy}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-lg transition-colors"
              >
                {copied ? <Check size={13} className="text-[#10b981]" /> : <Copy size={13} />}
                <span>{copied ? "Copied!" : "Copy link"}</span>
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
