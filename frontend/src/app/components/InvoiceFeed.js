"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect } from "react";
import { Clock, CheckCircle2, AlertTriangle, ShieldAlert, Search, Filter } from "lucide-react";
import InvoiceDetailModal from "./InvoiceDetailModal";

export default function InvoiceFeed({ traderId, apiBase }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [transitioning, setTransitioning] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  function navigate(newIndex) {
    setTransitioning(true);
    setTimeout(() => {
      setSelectedIndex(newIndex);
      setTransitioning(false);
    }, 160);
  }

  useEffect(() => {
    if (!traderId) return;

    async function fetchInvoices() {
      try {
        const res = await authFetch(`${apiBase}/api/v1/dashboard/invoices/${traderId}`);
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
    return (
      <div className="flex-1 min-h-0 bg-white border border-gray-200 overflow-hidden flex flex-col">
        {/* Header skeleton */}
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <div className="h-4 w-28 bg-gray-200 rounded animate-pulse" />
          <div className="h-3 w-16 bg-gray-100 rounded animate-pulse" />
        </div>
        {/* Search bar skeleton */}
        <div className="px-4 py-2 border-b border-gray-100 flex gap-2">
          <div className="flex-1 h-7 bg-gray-100 rounded animate-pulse" />
          <div className="w-24 h-7 bg-gray-100 rounded animate-pulse" />
        </div>
        {/* Row skeletons */}
        <div className="divide-y divide-gray-100 overflow-hidden">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-3">
              <div className="space-y-1.5">
                <div className="h-3.5 bg-gray-200 rounded animate-pulse" style={{ width: `${100 + i * 20}px` }} />
                <div className="h-2.5 bg-gray-100 rounded animate-pulse" style={{ width: `${60 + i * 10}px` }} />
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <div className="h-3.5 w-14 bg-gray-200 rounded animate-pulse" />
                <div className="h-5 w-20 bg-gray-100 rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
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
        
        {/* wrapper */}
        <div className="overflow-y-auto flex-1 bg-white">
          {/* Quick Metrics to fill gap */}
          <div className="grid grid-cols-3 gap-4 p-4 border-b border-[var(--border-subtle)] bg-gray-50/50">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Total Invoices</span>
              <span className="text-xl font-bold text-gray-900">{filteredInvoices.length}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Total ITC Value</span>
              <span className="text-xl font-bold text-gray-900">₹{filteredInvoices.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0).toLocaleString('en-IN')}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Blocked/Risk</span>
              <span className="text-xl font-bold text-red-600">
                {filteredInvoices.filter(inv => inv.itc_status === 'FIXABLE_BLOCKED' || inv.itc_status === 'AT_RISK' || inv.itc_status === 'FRAUD_FLAGGED').length}
              </span>
            </div>
          </div>

          {/* Grid Header */}
          <div className="grid grid-cols-12 gap-3 px-4 py-2 border-b border-[var(--border-subtle)] bg-gray-50 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider sticky top-0 z-10">
            <div className="col-span-4">Supplier & Invoice</div>
            <div className="col-span-2">GSTIN</div>
            <div className="col-span-2 text-right">Taxable Val</div>
            <div className="col-span-2 text-right">Total ITC</div>
            <div className="col-span-2 text-right">Status</div>
          </div>
          
          {filteredInvoices.length === 0 ? (
            <div className="p-8 text-center text-xs text-gray-400">No records found.</div>
          ) : (
            <div className="space-y-0">
              {filteredInvoices.map((inv, index) => {
                // Calculate tax manually if backend sends cgst/sgst/igst
                const taxTotal = (Number(inv.cgst_amount) || 0) + (Number(inv.sgst_amount) || 0) + (Number(inv.igst_amount) || 0);
                const isTaxCalculated = taxTotal > 0;
                
                return (
                  <div 
                    key={inv.id} 
                    onClick={() => setSelectedIndex(index)}
                    className={`group px-4 py-3 transition-colors grid grid-cols-12 gap-3 items-center border-b border-[var(--border-subtle)] last:border-0 cursor-pointer ${getRowBackground(inv.itc_status, inv.fraud_score)}`}
                  >
                    {/* Supplier & Invoice */}
                    <div className="col-span-4 flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-bold text-black truncate">{inv.supplier_name || inv.gstin_supplier || "Unknown Supplier"}</span>
                        {inv.fraud_score >= 70 && <ShieldAlert size={14} className="text-[var(--red-primary)] flex-shrink-0" />}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-[var(--text-secondary)] mt-0.5">
                        <span className="font-mono tracking-tight">{inv.invoice_number || "NO-INV-NUM"}</span>
                        <span>•</span>
                        <span>{new Date(inv.processed_at).toLocaleDateString('en-GB', {day: '2-digit', month: 'short'})}</span>
                      </div>
                    </div>

                    {/* GSTIN */}
                    <div className="col-span-2 flex items-center">
                      <span className="text-[11px] font-mono text-[var(--text-secondary)]">
                        {inv.gstin_supplier || "—"}
                      </span>
                    </div>

                    {/* Taxable */}
                    <div className="col-span-2 text-right flex flex-col justify-center">
                      <span className="text-[12px] font-medium text-[var(--text-secondary)]">
                        {inv.taxable_amount ? `₹${Number(inv.taxable_amount).toLocaleString('en-IN')}` : '—'}
                      </span>
                    </div>
                    
                    {/* Total ITC */}
                    <div className="col-span-2 text-right flex flex-col justify-center gap-0.5">
                      <span className="text-[13px] font-bold text-black">
                        ₹{Number(inv.total_amount || 0).toLocaleString('en-IN')}
                      </span>
                      {isTaxCalculated && (
                        <span className="text-[9px] text-[var(--text-muted)] font-mono">
                          Tax: ₹{taxTotal.toLocaleString('en-IN')}
                        </span>
                      )}
                    </div>

                    {/* Status */}
                    <div className="col-span-2 flex justify-end items-center">
                      <div className="flex items-center gap-1.5 px-2 py-1 bg-white border border-[var(--border-subtle)] rounded-md shadow-sm">
                        {getStatusIcon(inv.itc_status)}
                        <span className="text-[9px] font-bold uppercase tracking-widest whitespace-nowrap">
                          {getStatusLabel(inv.itc_status)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
      
      {selectedIndex !== null && (
        transitioning ? (
          /* Skeleton flash while navigating between invoices */
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-md p-8">
            <div className="bg-white w-full max-w-5xl max-h-[95vh] flex overflow-hidden">
              {/* Left: image placeholder */}
              <div className="w-1/2 bg-gray-100 animate-pulse" />
              {/* Right: detail skeleton */}
              <div className="w-1/2 p-8 space-y-5">
                <div className="h-5 w-2/3 bg-gray-200 rounded animate-pulse" />
                <div className="h-3 w-1/3 bg-gray-100 rounded animate-pulse" />
                <div className="mt-6 space-y-3">
                  {[1,2,3,4,5].map(i => <div key={i} className="h-3 bg-gray-100 rounded animate-pulse" style={{ width: `${80 - i * 8}%` }} />)}
                </div>
                <div className="mt-6 h-10 w-32 bg-gray-200 rounded animate-pulse" />
              </div>
            </div>
          </div>
        ) : (
          <InvoiceDetailModal
            invoice={invoices[selectedIndex]}
            onClose={() => setSelectedIndex(null)}
            onNext={() => navigate(selectedIndex < invoices.length - 1 ? selectedIndex + 1 : selectedIndex)}
            onPrev={() => navigate(selectedIndex > 0 ? selectedIndex - 1 : selectedIndex)}
            hasNext={selectedIndex < invoices.length - 1}
            hasPrev={selectedIndex > 0}
          />
        )
      )}
    </>
  );
}
