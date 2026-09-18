import { authFetch } from "@/src/app/utils/api";
import { useEffect } from "react";
import { X, CheckCircle2, AlertTriangle, ShieldAlert, FileText, Image as ImageIcon, ChevronLeft, ChevronRight, Check } from "lucide-react";

export default function InvoiceDetailModal({ invoice, onClose, onNext, onPrev, hasNext, hasPrev }) {
  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasPrev) onPrev();
      if (e.key === "ArrowRight" && hasNext) onNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, onNext, onPrev, hasNext, hasPrev]);

  if (!invoice) return null;

  const isAnalysisFailed = !invoice.gstin_supplier && !invoice.supplier_name && !invoice.invoice_number && !invoice.invoice_date;

  const getStatusIcon = (status) => {
    if (isAnalysisFailed) return <AlertTriangle size={20} className="text-[var(--text-muted)]" />;
    switch (status) {
      case "CONFIRMED": return <CheckCircle2 size={20} className="text-[var(--green-primary)]" />;
      case "FIXABLE_BLOCKED": return <AlertTriangle size={20} className="text-[var(--orange-primary)]" />;
      case "AT_RISK": return <AlertTriangle size={20} className="text-[var(--red-primary)]" />;
      case "FRAUD_FLAGGED": return <ShieldAlert size={20} className="text-[var(--red-primary)]" />;
      case "RESOLVED": return <CheckCircle2 size={20} className="text-[var(--text-muted)]" />;
      default: return <FileText size={20} className="text-[var(--text-secondary)]" />;
    }
  };

  const getStatusLabel = (status) => {
    if (isAnalysisFailed) return "Failed / Unprocessed";
    switch (status) {
      case "CONFIRMED": return "Confirmed";
      case "FIXABLE_BLOCKED": return "Blocked (Fixable)";
      case "AT_RISK": return "At Risk";
      case "FRAUD_FLAGGED": return "Fraud Flagged";
      case "RESOLVED": return "Resolved";
      case "INELIGIBLE": return "Ineligible";
      default: return status || "Pending";
    }
  };

  const isPDF = invoice.image_url && invoice.image_url.toLowerCase().includes('.pdf');

  // Format Date to e.g., "20 May, 2025"
  const formattedDate = invoice.invoice_date 
    ? new Date(invoice.invoice_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).replace(' ', ' ').replace(/ (\d{4})/, ', $1')
    : "N/A";

  // Generate a short Unique ID from the UUID
  const shortId = invoice.id ? `INV-${invoice.id.substring(0, 6).toUpperCase()}` : "INV-UNKNOWN";

  const isHardFraud = invoice.fraud_score >= 70;
  const isEligibleZero = !invoice.itc_amount_eligible || invoice.itc_amount_eligible === 0;

  // Extract triggered fraud signals if any
  let triggeredSignals = [];
  if (invoice.fraud_signals) {
    // Check if it's an object of { signal_name: { triggered, detail } }
    Object.entries(invoice.fraud_signals).forEach(([name, data]) => {
      if (data && data.triggered) {
        triggeredSignals.push({ name, detail: data.detail });
      }
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/70 p-2 md:p-8 transition-all duration-300 ease-in-out">
      {/* Outside Navigation - Close */}
      <button onClick={onClose} className="absolute top-4 right-4 md:top-8 md:right-8 z-[60] p-4 text-white/70 hover:text-white transition-all duration-300 ease-in-out">
        <X size={32} />
      </button>

      {/* Outside Navigation - Prev */}
      {hasPrev && (
        <button onClick={onPrev} className="hidden md:flex absolute left-8 z-[60] p-4 text-white/70 hover:text-white transition-all duration-300 ease-in-out hover:scale-110">
          <ChevronLeft size={36} />
        </button>
      )}

      {/* Outside Navigation - Next */}
      {hasNext && (
        <button onClick={onNext} className="hidden md:flex absolute right-8 z-[60] p-4 text-white/70 hover:text-white transition-all duration-300 ease-in-out hover:scale-110">
          <ChevronRight size={36} />
        </button>
      )}

      {/* Main Card */}
      <div className="bg-white rounded-2xl w-full max-w-5xl max-h-[95vh] overflow-hidden flex flex-col md:flex-row relative shadow-2xl border border-gray-200">
        
        {/* Mobile Navigation inside card if needed (kept minimal) */}
        <div className="md:hidden absolute bottom-4 right-4 z-20 flex gap-2 shadow-lg">
          {hasPrev && (
            <button onClick={onPrev} className="p-2 bg-gray-900 text-white rounded-full">
              <ChevronLeft size={20} />
            </button>
          )}
          {hasNext && (
            <button onClick={onNext} className="p-2 bg-black text-white rounded-none">
              <ChevronRight size={20} />
            </button>
          )}
        </div>

        {/* Media Preview Section */}
        <div className="w-full md:w-1/2 bg-gray-100 flex flex-col border-b md:border-b-0 md:border-r border-[var(--border-subtle)] relative max-h-[40vh] md:max-h-full">
          {invoice.image_url ? (
            isPDF ? (
              <iframe
                src={`${invoice.image_url}#view=FitH`}
                className="w-full h-full border-0"
                title="Invoice PDF"
              />
            ) : (
              <div className="w-full h-full relative group flex items-center justify-center overflow-hidden bg-black/5 p-4">
                <img
                  src={invoice.image_url}
                  alt="Invoice Document"
                  className="w-full h-full object-contain "
                />
                <a 
                  href={invoice.image_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white font-bold "
                >
                  View Full Resolution
                </a>
              </div>
            )
          ) : (
            <div className="w-full h-full min-h-[200px] flex flex-col items-center justify-center text-[var(--text-muted)] p-8 text-center">
              <ImageIcon size={48} className="mb-2 opacity-50" />
              <p className="text-sm font-bold">No document image available</p>
              <p className="text-xs mt-1">This invoice may have been imported directly</p>
            </div>
          )}
        </div>

        {/* Details Section */}
        <div className="w-full md:w-1/2 flex flex-col overflow-y-auto bg-white">
          {/* Status Banner */}
          {isAnalysisFailed ? (
            <div className="bg-gray-800 text-white p-3 flex items-center gap-3 px-6">
              <AlertTriangle size={24} className="flex-shrink-0 text-yellow-400" />
              <div>
                <p className="font-black tracking-widest text-sm uppercase text-yellow-400">ANALYSIS FAILED</p>
                <p className="text-xs text-gray-200 font-medium">Failed to extract data. The image might be unreadable or API limits exceeded.</p>
              </div>
            </div>
          ) : !invoice.gstin_supplier ? (
            <div className="bg-red-600 text-white p-3 flex items-center gap-3 px-6 animate-pulse">
              <ShieldAlert size={24} className="flex-shrink-0" />
              <div>
                <p className="font-black tracking-widest text-sm uppercase">CRITICAL: NO GSTIN FOUND</p>
                <p className="text-xs text-red-100 font-medium">Invalid tax invoice. Cannot claim ITC without supplier GSTIN.</p>
              </div>
            </div>
          ) : null}

          <div className="p-4 flex-1 flex flex-col">
            
            {/* Main Identifier */}
            <div className="mb-4 pt-2">
              <span className="text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest mb-1 block">
                {isAnalysisFailed ? "Scan Failed" : "Supplier"}
              </span>
              <h2 className="text-3xl md:text-4xl font-black text-black tracking-tighter uppercase leading-none break-words">
                {invoice.supplier_name || invoice.gstin_supplier || "UNKNOWN SUPPLIER"}
              </h2>
              <div className="mt-1 text-sm font-bold text-[var(--text-secondary)] uppercase tracking-widest">
                GSTIN: {invoice.gstin_supplier || "NO GSTIN FOUND"}
              </div>
              {isAnalysisFailed && (
                <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-red-100 text-red-800 text-xs font-bold uppercase tracking-wider rounded-none">
                  <AlertTriangle size={14} /> Analysis Failed
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="bg-gray-50 p-3 border border-[var(--border-subtle)] rounded-none">
                <p className="text-[10px] uppercase font-bold text-[var(--text-secondary)] tracking-widest mb-0.5">Invoice Number</p>
                <p className="text-sm font-bold text-black">{invoice.invoice_number || "N/A"}</p>
              </div>
              <div className="bg-gray-50 p-3 border border-[var(--border-subtle)] rounded-none">
                <p className="text-[10px] uppercase font-bold text-[var(--text-secondary)] tracking-widest mb-0.5">Invoice Date</p>
                <p className="text-sm font-bold text-black">{formattedDate}</p>
              </div>
            </div>

            {/* Amounts - Sleek, no borders */}
            <h3 className="text-[10px] uppercase font-bold text-[var(--text-secondary)] tracking-widest mb-2 border-b border-[var(--border-subtle)] pb-1">Financial Details</h3>
            <div className="mb-4">
              <div className="flex justify-between py-1 border-b border-[var(--border-subtle)]">
                <span className="text-sm font-bold text-[var(--text-secondary)]">Total Amount</span>
                <span className="text-base font-black text-black">₹{Number(invoice.total_amount || 0).toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border-subtle)]">
                <span className="text-sm font-medium text-[var(--text-secondary)]">Taxable Value</span>
                <span className="text-sm font-bold text-black">₹{Number(invoice.taxable_amount || 0).toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className={`text-sm font-bold flex items-center gap-1 ${isEligibleZero ? 'text-[var(--text-secondary)]' : 'text-[var(--green-primary)]'}`}>
                  ITC Eligible
                </span>
                <span className={`text-base font-black ${isEligibleZero ? 'text-gray-500' : 'text-[var(--green-primary)]'}`}>₹{Number(invoice.itc_amount_eligible || 0).toLocaleString('en-IN')}</span>
              </div>
            </div>

            {/* ITC Status & Block Reason */}
            <h3 className="text-[10px] uppercase font-bold text-[var(--text-secondary)] tracking-widest mb-2 border-b border-[var(--border-subtle)] pb-1">Compliance Verdict</h3>
            
            <div className="flex items-start gap-2 mb-3 p-3 bg-gray-50 border border-gray-100 rounded-none">
              <div className="mt-0.5">
                {getStatusIcon(invoice.itc_status)}
              </div>
              <div>
                <p className="text-sm font-black text-black">{getStatusLabel(invoice.itc_status)}</p>
                {invoice.itc_block_reason && !isAnalysisFailed && (
                  <p className="text-xs font-medium text-[var(--text-secondary)] mt-0.5">{invoice.itc_block_reason}</p>
                )}
              </div>
            </div>

            {invoice.fraud_score > 0 && !isAnalysisFailed && (
              <div className={`mt-1 p-3 border rounded-none ${isHardFraud ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200'}`}>
                <p className={`text-[10px] font-bold uppercase tracking-wide mb-1 flex items-center gap-1 ${isHardFraud ? 'text-red-700' : 'text-orange-700'}`}>
                  <ShieldAlert size={12} /> {isHardFraud ? 'FRAUD SIGNALS DETECTED' : 'ANOMALY DETECTED'} (Score: {invoice.fraud_score}/100)
                </p>
                {triggeredSignals.length > 0 ? (
                  <ul className="space-y-0.5">
                    {triggeredSignals.map((signal, idx) => (
                      <li key={idx} className={`text-[10px] ${isHardFraud ? 'text-red-900 font-medium' : 'text-orange-900'}`}>
                        <span className="font-bold">{signal.name.replace(/_/g, ' ')}:</span> {signal.detail}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={`text-[10px] ${isHardFraud ? 'text-red-900 font-medium' : 'text-orange-900'}`}>
                    {isHardFraud ? 'Please manually review this invoice immediately.' : 'Some irregular patterns detected. Verify if needed.'}
                  </p>
                )}
              </div>
            )}

            {/* GSTR-2B Warning Panel */}
            {(invoice.gstr2b_match_status === "UNRECONCILED" || invoice.gstr2b_match_status === "ITC_AT_RISK") && (
              <div className="mt-4 p-4 border rounded-none bg-yellow-50 border-yellow-300">
                <p className="text-xs font-bold uppercase tracking-wide mb-2 flex items-center gap-1 text-yellow-800">
                  <AlertTriangle size={14} /> Missed GSTR-1 Filing (Vendor)
                </p>
                <p className="text-sm text-yellow-900 mb-3">
                  This vendor has not filed this invoice in their GSTR-1. Send them a warning to file it immediately.
                </p>
                <div className="flex gap-2">
                  <button 
                    onClick={async () => {
                      try {
                        const res = await authFetch(`http://localhost:8000/api/v1/communicate/email-vendor/${invoice.id}`, { method: 'POST' });
                        if (res.ok) {
                          alert("Warning Email sent successfully!");
                        } else {
                          const err = await res.json();
                          alert(`Failed to send email: ${err.detail}`);
                        }
                      } catch (e) {
                        alert("Failed to send email");
                      }
                    }}
                    disabled={!invoice.supplier_email}
                    className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-none ${invoice.supplier_email ? 'bg-black text-white hover:bg-gray-800' : 'bg-gray-200 text-gray-500 cursor-not-allowed'}`}
                  >
                    Email Warning
                  </button>
                  <button 
                    onClick={async () => {
                      try {
                        const res = await authFetch(`http://localhost:8000/api/v1/communicate/whatsapp-vendor/${invoice.id}`, { method: 'POST' });
                        if (res.ok) {
                          alert("WhatsApp Warning sent successfully!");
                        } else {
                          const err = await res.json();
                          alert(`Failed to send WhatsApp: ${err.detail}`);
                        }
                      } catch (e) {
                        alert("Failed to send WhatsApp");
                      }
                    }}
                    disabled={!invoice.supplier_phone}
                    className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-none ${invoice.supplier_phone ? 'bg-[#25D366] text-white hover:bg-[#128C7E]' : 'bg-gray-200 text-gray-500 cursor-not-allowed'}`}
                  >
                    WhatsApp Warning
                  </button>
                </div>
              </div>
            )}

            {/* CA Actions */}
            <div className="mt-auto pt-4">
              <div className="flex gap-2">
                <button 
                  onClick={() => {/* Integration for mark resolved could go here */ onClose()}}
                  className="flex-1 bg-black text-white py-2.5 rounded-none font-bold text-xs hover:bg-gray-800 transition-colors flex items-center justify-center gap-1.5"
                >
                  <Check size={14} /> Mark as Resolved
                </button>
                <button 
                  className="flex-1 bg-white text-black border border-gray-300 py-2.5 rounded-none font-bold text-xs hover:bg-gray-50 transition-colors flex items-center justify-center gap-1.5"
                >
                  <AlertTriangle size={14} /> Flag for Review
                </button>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}
