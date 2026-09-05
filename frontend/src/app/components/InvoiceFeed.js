"use client";

import { useState, useEffect } from "react";
import { Clock, CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import InvoiceDetailModal from "./InvoiceDetailModal";

export default function InvoiceFeed({ traderId, apiBase }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);

  useEffect(() => {
    if (!traderId) return;

    async function fetchInvoices() {
      try {
        const res = await fetch(`${apiBase}/api/v1/dashboard/invoices/${traderId}`);
        if (!res.ok) throw new Error("Failed to fetch invoices");
        const data = await res.json();
        
        // Sort by processed_at descending
        const sorted = (data.invoices || []).sort((a, b) => {
          return new Date(b.processed_at) - new Date(a.processed_at);
        });
        
        setInvoices(sorted.slice(0, 15)); // Show recent 15
      } catch (err) {
        console.error("Error fetching invoices:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchInvoices();
    
    // Poll every 10 seconds for the "live feed" effect
    const interval = setInterval(fetchInvoices, 10000);
    return () => clearInterval(interval);
  }, [traderId, apiBase]);

  const getStatusIcon = (status) => {
    switch (status) {
      case "CONFIRMED": return <CheckCircle2 size={16} className="text-[var(--green-primary)]" />;
      case "FIXABLE_BLOCKED": return <AlertTriangle size={16} className="text-[var(--orange-primary)]" />;
      case "AT_RISK": return <AlertTriangle size={16} className="text-[var(--red-primary)]" />;
      case "FRAUD_FLAGGED": return <ShieldAlert size={16} className="text-[var(--red-primary)]" />;
      case "RESOLVED": return <CheckCircle2 size={16} className="text-[var(--text-muted)]" />;
      default: return <Clock size={16} className="text-[var(--text-secondary)]" />;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case "CONFIRMED": return "✓ Confirmed";
      case "FIXABLE_BLOCKED": return "⚠ Blocked";
      case "AT_RISK": return "↯ At Risk";
      case "FRAUD_FLAGGED": return "✕ Fraud";
      case "RESOLVED": return "✓ Resolved";
      case "INELIGIBLE": return "— Ineligible";
      default: return status || "Pending";
    }
  };

  const getRowBackground = (status, fraudScore) => {
    if (fraudScore >= 70) return "bg-red-50/50 hover:bg-red-50";
    switch (status) {
      case "FRAUD_FLAGGED":
      case "AT_RISK": return "bg-red-50/50 hover:bg-red-50";
      case "FIXABLE_BLOCKED": return "bg-orange-50/50 hover:bg-orange-50";
      default: return "hover:bg-[var(--bg-primary)]";
    }
  };

  if (loading) {
    return <div className="text-[var(--text-secondary)] text-sm animate-pulse">Loading live feed...</div>;
  }

  if (invoices.length === 0) {
    return <div className="text-[var(--text-secondary)] text-sm">No recent invoices processed.</div>;
  }

  return (
    <>
      <div className="bg-white border border-[var(--border-subtle)] overflow-hidden flex flex-col h-full max-h-[600px]">
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between sticky top-0 bg-white">
          <h3 className="font-bold text-sm uppercase tracking-wider text-black">Live Invoice Feed</h3>
          <span className="flex items-center gap-2 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest">
            <span className="w-2 h-2 rounded-none bg-black animate-pulse"></span>
            Live Sync
          </span>
        </div>
        
        <div className="overflow-y-auto flex-1 p-2">
          <div className="space-y-1">
            {invoices.map((inv, index) => (
              <div 
                key={inv.id} 
                onClick={() => setSelectedIndex(index)}
                className={`group p-3 transition-colors flex items-center justify-between border-b border-[var(--border-subtle)] last:border-0 cursor-pointer ${getRowBackground(inv.itc_status, inv.fraud_score)}`}
              >
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-black">{inv.supplier_name || inv.gstin_supplier || "Unknown Supplier"}</span>
                    {inv.fraud_score >= 70 && <ShieldAlert size={14} className="text-[var(--red-primary)]" />}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] mt-1">
                    <span className="uppercase tracking-widest text-[10px]">{inv.invoice_number || "NO-INV-NUM"}</span>
                    <span>•</span>
                    <span>{new Date(inv.processed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  </div>
                </div>
                
                <div className="flex flex-col items-end gap-1">
                  <span className="text-sm font-bold text-black">
                    ₹{Number(inv.total_amount || 0).toLocaleString('en-IN')}
                  </span>
                  <div className="flex items-center gap-1.5 px-2 py-0.5 bg-white border border-[var(--border-subtle)] rounded-none">
                    {getStatusIcon(inv.itc_status)}
                    <span className="text-[10px] font-bold uppercase tracking-wider">
                      {getStatusLabel(inv.itc_status)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {selectedIndex !== null && (
        <InvoiceDetailModal 
          invoice={invoices[selectedIndex]} 
          onClose={() => setSelectedIndex(null)} 
          onNext={() => setSelectedIndex(selectedIndex < invoices.length - 1 ? selectedIndex + 1 : selectedIndex)}
          onPrev={() => setSelectedIndex(selectedIndex > 0 ? selectedIndex - 1 : selectedIndex)}
          hasNext={selectedIndex < invoices.length - 1}
          hasPrev={selectedIndex > 0}
        />
      )}
    </>
  );
}
