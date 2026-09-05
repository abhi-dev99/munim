"use client";

import { useState, useEffect } from "react";
import { Clock, CheckCircle2, AlertTriangle, ShieldAlert, Search, Filter } from "lucide-react";
import InvoiceDetailModal from "./InvoiceDetailModal";

export default function InvoiceFeed({ traderId, apiBase }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

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
        
        setInvoices(sorted); // Store all, filter later
      } catch (err) {
        console.error("Error fetching invoices:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchInvoices();
    
    const interval = setInterval(fetchInvoices, 10000);
    return () => clearInterval(interval);
  }, [traderId, apiBase]);

  const getStatusIcon = (status) => {
    switch (status) {
      case "CONFIRMED": return <CheckCircle2 size={16} className="text-[var(--green-primary)]" />;
      case "FIXABLE_BLOCKED": return <AlertTriangle size={16} className="text-[var(--orange-primary)]" />;
      case "AT_RISK": return <AlertTriangle size={16} className="text-[var(--red-primary)]" />;
      case "FRAUD_FLAGGED": return <ShieldAlert size={16} className="text-[var(--red-primary)]" />;
      case "DUPLICATE": return <Clock size={16} className="text-gray-500" />;
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
      case "DUPLICATE": return "⧉ Duplicate";
      case "RESOLVED": return "✓ Resolved";
      case "INELIGIBLE": return "— Ineligible";
      default: return "Pending";
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

  const filteredInvoices = invoices.filter(inv => {
    const matchesSearch = 
      (inv.supplier_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (inv.gstin_supplier || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (inv.invoice_number || "").toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || inv.itc_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return <div className="text-[var(--text-secondary)] text-sm animate-pulse">Loading invoice records...</div>;
  }

  return (
    <>
      <div className="flex-1 min-h-0 bg-white border border-[var(--border-subtle)] overflow-hidden flex flex-col">
        <div className="p-4 border-b border-[var(--border-subtle)] bg-white space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm uppercase tracking-wider text-black">Invoice Records</h3>
            <span className="flex items-center gap-2 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-widest">
              <span className="w-2 h-2 rounded-none bg-black animate-pulse"></span>
              Live Sync
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2 text-[var(--text-muted)]" size={14} />
              <input 
                type="text" 
                placeholder="Search Supplier, GSTIN, Invoice..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full text-xs pl-8 pr-3 py-1.5 border border-[var(--border-subtle)] rounded-none focus:outline-none focus:border-black"
              />
            </div>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-[var(--border-subtle)] py-1.5 px-2 rounded-none bg-white focus:outline-none focus:border-black"
            >
              <option value="ALL">All Status</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="FIXABLE_BLOCKED">Blocked</option>
              <option value="AT_RISK">At Risk</option>
              <option value="FRAUD_FLAGGED">Fraud</option>
            </select>
          </div>
        </div>
        
        <div className="overflow-y-auto flex-1 p-2">
          {filteredInvoices.length === 0 ? (
            <div className="p-4 text-center text-xs text-[var(--text-secondary)]">No records found.</div>
          ) : (
            <div className="space-y-1">
              {filteredInvoices.map((inv, index) => (
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
          )}
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
