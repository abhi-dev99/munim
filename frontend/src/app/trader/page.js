"use client";

import { useState, useEffect, useRef } from "react";
import { Menu, Camera, FileText, CheckCircle2, ShieldAlert, X, Loader2 } from "lucide-react";
import MoneyMeter from "../components/MoneyMeter";
import ActionQueue from "../components/ActionQueue";
import InvoiceDetailModal from "../components/InvoiceDetailModal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function TraderApp() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);
  const [scanState, setScanState] = useState("idle"); // idle | uploading | success | error
  const [scanResult, setScanResult] = useState(null);
  const [activeTab, setActiveTab] = useState("home"); // home | history
  const [invoiceHistory, setInvoiceHistory] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const tradersRes = await fetch(`${API_BASE}/api/v1/dashboard/traders`);
        if (!tradersRes.ok) throw new Error("Failed to fetch traders");
        const tradersData = await tradersRes.json();
        const activeTrader = tradersData.traders?.[0]?.id || "demo";

        const res = await fetch(`${API_BASE}/api/v1/dashboard/summary/${activeTrader}`);
      if (res.ok) {
          const data = await res.json();
          setSummary(data);
          setTraderId(data.trader_id);
          // Fetch invoice history
          const invRes = await fetch(`${API_BASE}/api/v1/dashboard/invoices/${data.trader_id}`);
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
          itc_buckets: { confirmed: 41200, fixable_blocked: 8600, at_risk: 12400, missed: 3200, ineligible: 0 },
        });
        setTraderId("demo");
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, []);

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
      const res = await fetch(`${API_BASE}/api/v1/webhook/upload-invoice`, {
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
        });
        setTimeout(() => {
          setScanState("idle");
          setScanResult(null);
        }, 8000);
        
        // Refresh invoice history after successful upload
        const invRes = await fetch(`${API_BASE}/api/v1/dashboard/invoices/${traderId}`);
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
          if (file) handleInvoiceUpload(file);
          e.target.value = "";
        }}
      />

      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[var(--border-subtle)] bg-white sticky top-0 z-10">
        <div className="flex flex-col">
          <h1 className="text-xl font-bold tracking-tight text-black">Munim.ai</h1>
          <span className="text-[10px] uppercase font-bold text-[var(--green-primary)] tracking-widest">Active</span>
        </div>
        <button className="p-2 -mr-2 text-black">
          <Menu size={24} />
        </button>
      </header>

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
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Financial Snapshot</h2>
              <MoneyMeter summary={summary} apiBase={API_BASE} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Required Actions</h2>
              <ActionQueue traderId={traderId} apiBase={API_BASE} />
            </div>
          </>
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
          disabled={scanState === "uploading"}
          className="flex-2 flex items-center justify-center gap-2 px-6 py-3 rounded-none bg-black text-white  hover:bg-gray-900 transition-all transform hover:scale-105 w-full disabled:opacity-60 disabled:scale-100"
        >
          {scanState === "uploading" ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Camera size={20} />
          )}
          <span className="font-bold text-sm">
            {scanState === "uploading" ? "Processing..." : "Scan Invoice"}
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
    </div>
  );
}
