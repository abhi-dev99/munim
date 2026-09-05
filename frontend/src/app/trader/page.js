"use client";
import { authFetch } from "@/src/app/utils/api";
import { assessPhotoQuality } from "@/src/app/utils/imageQuality";
import { vibrateAlert, vibrateSuccess, vibrateWarning } from "@/src/app/utils/haptics";


import { useState, useEffect, useRef } from "react";
import { Menu, Camera, FileText, CheckCircle2, ShieldAlert, X, Loader2, Home, BarChart2, ChevronRight, Upload } from "lucide-react";
import MoneyMeter from "../components/MoneyMeter";
import ActionQueue from "../components/ActionQueue";
import InvoiceDetailModal from "../components/InvoiceDetailModal";
import ReportsPanel from "../components/ReportsPanel";
import ListenButton from "../components/ListenButton";
import VoiceQueryButton from "../components/VoiceQueryButton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Longest-edge size (px) a captured photo is downscaled to before the
// on-device quality analysis runs. Keeps the Laplacian-variance pass fast
// even for a multi-megapixel phone camera capture — only the analysis frame
// is downscaled, the original full-resolution file is still what gets
// uploaded when the photo passes (or the user overrides a warning).
const QUALITY_ANALYSIS_MAX_DIMENSION = 800;

/**
 * On-device blur/glare check: draws the captured file to an off-screen
 * canvas, extracts ImageData, and runs the pure imageQuality assessment —
 * entirely client-side, before any network request. Resolves to null for
 * non-image files (e.g. PDF) or if analysis fails for any reason, so the
 * upload flow always has a safe fallback and is never blocked by this check.
 */
function analyzeImageFile(file) {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !file?.type?.startsWith("image/")) {
      resolve(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const img = new window.Image();

    const cleanup = () => URL.revokeObjectURL(objectUrl);

    img.onload = () => {
      try {
        const scale = Math.min(1, QUALITY_ANALYSIS_MAX_DIMENSION / Math.max(img.width, img.height));
        const width = Math.max(1, Math.round(img.width * scale));
        const height = Math.max(1, Math.round(img.height * scale));

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, width, height);
        const imageData = ctx.getImageData(0, 0, width, height);
        resolve(assessPhotoQuality(imageData));
      } catch (err) {
        console.warn("On-device photo quality check failed, skipping check.", err);
        resolve(null);
      } finally {
        cleanup();
      }
    };
    img.onerror = () => {
      cleanup();
      resolve(null);
    };
    img.src = objectUrl;
  });
}

export default function TraderApp() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);
  const [traderName, setTraderName] = useState("");
  const [traderPhone, setTraderPhone] = useState(null);
  const [scanState, setScanState] = useState("idle");
  const [scanResult, setScanResult] = useState(null);
  const [activeTab, setActiveTab] = useState("home"); // home | history | reports
  const [invoiceHistory, setInvoiceHistory] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [checkingPhoto, setCheckingPhoto] = useState(false);
  const [retakePrompt, setRetakePrompt] = useState(null); // { file, verdict } | null
  const fileInputRef = useRef(null);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const tradersRes = await authFetch(`${API_BASE}/api/v1/dashboard/traders`);
        if (!tradersRes.ok) throw new Error("Failed to fetch traders");
        const tradersData = await tradersRes.json();
        const activeTrader = tradersData.traders?.[0];
        const activeId = activeTrader?.id || "demo";
        setTraderName(activeTrader?.business_name || activeTrader?.name || "My Business");
        setTraderPhone(activeTrader?.whatsapp_number || null);

        const res = await authFetch(`${API_BASE}/api/v1/dashboard/summary/${activeId}`);
      if (res.ok) {
          const data = await res.json();
          setSummary(data);
          setTraderId(data.trader_id);
          const invRes = await authFetch(`${API_BASE}/api/v1/dashboard/invoices/${data.trader_id}`);
          if (invRes.ok) {
            const invData = await invRes.json();
            setInvoiceHistory((invData.invoices || []).slice(0, 20));
          }
        }
      } catch (err) {
        console.warn("Using demo data (backend unavailable)", err);
        setSummary({
          trader_id: "demo",
          month: new Date().getMonth() + 1,
          year: new Date().getFullYear(),
          itc_buckets: { confirmed: 0, fixable_blocked: 0, at_risk: 0, missed: 0, ineligible: 0 },
        });
        setTraderId("demo");
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (scanState !== "success" || !scanResult) return;
    if (scanResult.status === "FRAUD_FLAGGED") vibrateAlert();
    else if (scanResult.status === "AT_RISK" || scanResult.status === "FIXABLE_BLOCKED") vibrateWarning();
    else if (scanResult.status === "CONFIRMED") vibrateSuccess();
  }, [scanState, scanResult]);

  async function handleInvoiceUpload(file) {
    if (!file || !traderId || traderId === "demo") {
      setScanState("error");
      setScanResult({ message: "No active trader. Please set up your GSTIN first." });
      return;
    }

    setScanState("uploading");
    setScanResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("trader_id", traderId);

    try {
      const res = await authFetch(`${API_BASE}/api/v1/webhook/upload-invoice`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setScanState("success");
        setScanResult({
          status: data.itc_verdict?.status || "PROCESSING",
          itc_amount: data.itc_verdict?.itc_amount || 0,
          message: data.diagnosis_hi || data.diagnosis_en || "Invoice processed!",
          // Hint the TTS voice picker toward Hindi only when we actually got
          // Hindi text back — otherwise fall back to English.
          lang: data.diagnosis_hi ? "hi-IN" : "en-IN",
        });
        setTimeout(() => {
          setScanState("idle");
          setScanResult(null);
        }, 8000);
        
        // Refresh invoice history after successful upload
        const invRes = await authFetch(`${API_BASE}/api/v1/dashboard/invoices/${traderId}`);
        if (invRes.ok) {
          const invData = await invRes.json();
          setInvoiceHistory((invData.invoices || []).slice(0, 20));
        }
      } else {
        setScanState("error");
        setScanResult({ message: data.detail || "Processing failed. Try again." });
      }
    } catch (err) {
      setScanState("error");
      setScanResult({ message: "Network error — check your connection." });
    }
  }

  function triggerScan() {
    fileInputRef.current?.click();
  }

  // Gate: run the on-device blur/glare check before this file ever reaches
  // handleInvoiceUpload (i.e. before the network round-trip + paid Gemini
  // Vision OCR call). A bad photo shows a retake prompt with the specific
  // reason instead of silently uploading and burning an API call on a scan
  // that's going to come back garbled anyway. Not a hard block — the user
  // can always choose "Upload Anyway", since some real invoices are
  // genuinely hard to photograph cleanly and a false positive shouldn't
  // trap them.
  async function handleFileSelected(file) {
    if (!file) return;

    setCheckingPhoto(true);
    const verdict = await analyzeImageFile(file);
    setCheckingPhoto(false);

    if (verdict && !verdict.isAcceptable) {
      setRetakePrompt({ file, verdict });
      return;
    }

    handleInvoiceUpload(file);
  }

  const statusColors = {
    CONFIRMED: "text-[var(--green-primary)]",
    FIXABLE_BLOCKED: "text-[var(--orange-primary)]",
    AT_RISK: "text-[var(--red-primary)]",
    INELIGIBLE: "text-[var(--text-muted)]",
    FRAUD_FLAGGED: "text-[var(--red-primary)]",
  };

  const getRowBackground = (status, fraudScore) => {
    if (fraudScore >= 70) return "bg-red-50/50 border-red-200";
    switch (status) {
      case "FRAUD_FLAGGED":
      case "AT_RISK": return "bg-red-50/50 border-red-200";
      case "FIXABLE_BLOCKED": return "bg-orange-50/50 border-orange-200";
      default: return "bg-white border-[var(--border-subtle)]";
    }
  };

  return (
    <div className="flex flex-col min-h-screen pb-20">
      {/* Hidden file input — mobile camera capture */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) handleFileSelected(file);
        }}
      />

      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[var(--border-subtle)] bg-white sticky top-0 z-10">
        <div className="flex flex-col">
          <h1 className="text-xl font-bold tracking-tight text-black">Munim.ai</h1>
          <span className="text-[10px] uppercase font-bold text-[var(--green-primary)] tracking-widest">Active</span>
        </div>
        <button className="p-2 -mr-2 text-black" onClick={() => setSidebarOpen(true)}>
          <Menu size={24} />
        </button>
      </header>

      {/* Slide-out Sidebar Drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40" onClick={() => setSidebarOpen(false)} />
          {/* Drawer */}
          <div className="relative ml-auto w-72 h-full bg-white flex flex-col shadow-2xl">
            {/* Drawer header */}
            <div className="flex items-center justify-between p-5 border-b border-[var(--border-subtle)]">
              <div>
                <p className="font-bold text-black text-base">Munim.ai</p>
                <p className="text-xs text-[var(--text-secondary)] truncate max-w-[180px]">{traderName}</p>
              </div>
              <button onClick={() => setSidebarOpen(false)} className="p-1.5 rounded hover:bg-[var(--bg-primary)] transition-colors">
                <X size={20} className="text-black" />
              </button>
            </div>

            {/* Nav items */}
            <nav className="flex-1 p-4 space-y-1">
              {[
                { id: "home",    label: "Dashboard",       icon: <Home size={18} /> },
                { id: "history", label: "Invoice History",  icon: <FileText size={18} /> },
                { id: "reports", label: "Reports & GSTR-2B", icon: <BarChart2 size={18} /> },
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => { setActiveTab(item.id); setSidebarOpen(false); }}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === item.id
                      ? "bg-black text-white"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] hover:text-black"
                  }`}
                >
                  <span className="flex items-center gap-3">{item.icon}{item.label}</span>
                  <ChevronRight size={14} className="opacity-50" />
                </button>
              ))}
            </nav>

            {/* Upload invoice from sidebar */}
            <div className="p-4 border-t border-[var(--border-subtle)]">
              <button
                onClick={() => { setSidebarOpen(false); fileInputRef.current?.click(); }}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-black text-white font-bold text-sm hover:bg-gray-800 transition-colors"
              >
                <Upload size={16} /> Upload Invoice
              </button>
            </div>
          </div>
        </div>
      )}

      {/* On-device photo quality check — runs before any upload/network call */}
      {checkingPhoto && (
        <div className="mx-4 mt-4 p-4 rounded-none border border-[var(--border-subtle)] bg-white flex items-center gap-3">
          <Loader2 size={18} className="animate-spin text-black flex-shrink-0" />
          <p className="font-bold text-black text-sm">Checking photo quality on your device...</p>
        </div>
      )}

      {/* Scan Result Toast */}
      {scanState !== "idle" && (
        <div className="mx-4 mt-4 p-4 rounded-none border border-[var(--border-subtle)] bg-white flex items-start gap-3">
          {scanState === "uploading" && <Loader2 size={18} className="animate-spin text-black mt-0.5 flex-shrink-0" />}
          {scanState === "success" && <CheckCircle2 size={18} className="text-black mt-0.5 flex-shrink-0" />}
          {scanState === "error" && <ShieldAlert size={18} className="text-[var(--red-primary)] mt-0.5 flex-shrink-0" />}
          <div className="flex-1">
            {scanState === "uploading" && (
              <>
                <p className="font-bold text-black text-sm">Processing invoice...</p>
                <p className="text-xs text-[var(--text-secondary)]">Checking GSTIN, HSN codes, GSTR-2B match</p>
              </>
            )}
            {scanState === "success" && scanResult && (
              <>
                <p className="font-bold text-black text-sm">
                  Invoice Analyzed —{" "}
                  <span className={statusColors[scanResult.status] || "text-black"}>{scanResult.status}</span>
                </p>
                {scanResult.itc_amount > 0 && (
                  <p className="text-xs font-bold text-black">ITC: ₹{scanResult.itc_amount.toLocaleString("en-IN")}</p>
                )}
                <p className="text-xs text-[var(--text-secondary)] mt-1">{scanResult.message}</p>
                <ListenButton text={scanResult.message} lang={scanResult.lang} className="mt-1.5" />
              </>
            )}
            {scanState === "error" && scanResult && (
              <>
                <p className="font-bold text-[var(--red-primary)] text-sm">Processing Failed</p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {scanResult.message.includes("limit") || scanResult.message.includes("quota") 
                    ? "API Usage Limit Reached. Please try again tomorrow or contact support." 
                    : scanResult.message}
                </p>
              </>
            )}
          </div>
          {scanState !== "uploading" && (
            <button onClick={() => { setScanState("idle"); setScanResult(null); }}>
              <X size={16} className="text-[var(--text-muted)]" />
            </button>
          )}
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 p-4 overflow-y-auto space-y-6 bg-[var(--bg-primary)]">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-none h-8 w-8 border-b-2 border-black"></div>
          </div>
        ) : activeTab === "home" ? (
          <>
            <div className="mb-2">
              <VoiceQueryButton summary={summary} />
            </div>
            <div className="mb-2">
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Financial Snapshot</h2>
              <MoneyMeter summary={summary} apiBase={API_BASE} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Required Actions</h2>
              <ActionQueue traderId={traderId} apiBase={API_BASE} traderPhone={traderPhone} />
            </div>
          </>
        ) : activeTab === "reports" ? (
          <ReportsPanel traderId={traderId} apiBase={API_BASE} />
        ) : (
          <div>
            <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-3">Invoice History</h2>
            {invoiceHistory.length === 0 ? (
              <div className="text-center py-12 text-[var(--text-muted)] text-sm">No invoices processed yet. Scan your first invoice!</div>
            ) : (
              <div className="space-y-2">
                {invoiceHistory.map((inv, index) => (
                  <div 
                    key={inv.id} 
                    onClick={() => setSelectedIndex(index)}
                    className={`border rounded-none p-4 flex items-center justify-between cursor-pointer active:scale-[0.98] transition-transform ${getRowBackground(inv.itc_status, inv.fraud_score)}`}
                  >
                    <div>
                      <div className="flex items-center gap-1">
                        <p className="font-bold text-black text-sm">{inv.supplier_name || inv.gstin_supplier || "Unknown Supplier"}</p>
                        {inv.fraud_score >= 70 && <ShieldAlert size={12} className="text-[var(--red-primary)]" />}
                      </div>
                      <p className="text-xs text-[var(--text-muted)]">{inv.invoice_number} · {inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString("en-IN") : ""}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-black text-sm">₹{Number(inv.total_amount || 0).toLocaleString("en-IN")}</p>
                      <span className={`text-[10px] font-bold uppercase ${
                        inv.itc_status === "CONFIRMED" ? "text-[var(--green-primary)]" :
                        inv.itc_status === "FIXABLE_BLOCKED" ? "text-[var(--orange-primary)]" :
                        "text-[var(--red-primary)]"
                      }`}>{inv.itc_status || "PENDING"}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Fixed Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white border-t border-[var(--border-subtle)] p-4 flex gap-4">
        <button
          onClick={() => setActiveTab(activeTab === "history" ? "home" : "history")}
          className={`flex-1 flex flex-col items-center justify-center gap-1 p-2 transition-colors ${activeTab === "history" ? "text-black" : "text-[var(--text-secondary)] hover:text-black"}`}
        >
          <FileText size={20} />
          <span className="text-[10px] font-bold">History</span>
        </button>
        
        {/* Massive Scan Button */}
        <button
          onClick={() => { setActiveTab("home"); triggerScan(); }}
          disabled={scanState === "uploading" || checkingPhoto}
          className="flex-2 flex items-center justify-center gap-2 px-6 py-3 rounded-none bg-black text-white  hover:bg-gray-900 transition-all transform hover:scale-105 w-full disabled:opacity-60 disabled:scale-100"
        >
          {scanState === "uploading" || checkingPhoto ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Camera size={20} />
          )}
          <span className="font-bold text-sm">
            {checkingPhoto ? "Checking Photo..." : scanState === "uploading" ? "Processing..." : "Scan Invoice"}
          </span>
        </button>
      </div>

      {/* Modal */}
      {selectedIndex !== null && (
        <InvoiceDetailModal
          invoice={invoiceHistory[selectedIndex]}
          onClose={() => setSelectedIndex(null)}
          onNext={() => setSelectedIndex(selectedIndex < invoiceHistory.length - 1 ? selectedIndex + 1 : selectedIndex)}
          onPrev={() => setSelectedIndex(selectedIndex > 0 ? selectedIndex - 1 : selectedIndex)}
          hasNext={selectedIndex < invoiceHistory.length - 1}
          hasPrev={selectedIndex > 0}
        />
      )}

      {/* Retake prompt — on-device blur/glare check failed. Not a hard
          block: the trader can override and upload anyway, since a false
          positive on a genuinely hard-to-photograph invoice shouldn't trap
          them. */}
      {retakePrompt && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm bg-white rounded-none border border-[var(--border-subtle)] p-6 shadow-2xl">
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert size={20} className="text-[var(--orange-primary)] flex-shrink-0" />
              <h2 className="font-bold text-black text-base">Photo may not scan well</h2>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mb-6">{retakePrompt.verdict.reason}</p>

            <div className="flex flex-col gap-2">
              <button
                onClick={() => {
                  setRetakePrompt(null);
                  fileInputRef.current?.click();
                }}
                className="w-full py-3 rounded-none bg-black text-white font-bold text-sm hover:bg-gray-800 transition-colors"
              >
                Retake Photo
              </button>
              <button
                onClick={() => {
                  const file = retakePrompt.file;
                  setRetakePrompt(null);
                  handleInvoiceUpload(file);
                }}
                className="w-full py-3 rounded-none border border-[var(--border-subtle)] text-[var(--text-secondary)] font-bold text-sm hover:bg-[var(--bg-primary)] transition-colors"
              >
                Upload Anyway
              </button>
            </div>

            <p className="text-[10px] text-[var(--text-muted)] mt-4 text-center">
              Checked on your device — no data was uploaded for this check.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
