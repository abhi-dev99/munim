"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle2, XCircle, Search, ChevronUp, ChevronDown, ArrowUpRight, X, FileText, ShieldAlert } from "lucide-react";
import InvoiceDetailModal from "./InvoiceDetailModal";

const STATUS_CONFIG = {
  GOOD:     { label: "Good",     chip: "bg-emerald-50 text-emerald-700 border-emerald-200",  dot: "bg-emerald-500", bar: "bg-emerald-500" },
  RISK:     { label: "At Risk",  chip: "bg-amber-50 text-amber-700 border-amber-200",        dot: "bg-amber-500",   bar: "bg-amber-500"   },
  CRITICAL: { label: "Blocked",  chip: "bg-red-50 text-red-700 border-red-200",              dot: "bg-red-500",     bar: "bg-red-500"     },
};

function formatINR(amount) {
  if (!amount || amount === 0) return "—";
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000)   return `₹${(amount / 1000).toFixed(0)}K`;
  return `₹${amount}`;
}

function getStatusIcon(status) {
  switch (status) {
    case "CONFIRMED":       return <CheckCircle2 size={13} className="text-emerald-500" />;
    case "FIXABLE_BLOCKED": return <AlertTriangle size={13} className="text-amber-500" />;
    case "AT_RISK":         return <AlertTriangle size={13} className="text-red-500" />;
    case "FRAUD_FLAGGED":   return <ShieldAlert size={13} className="text-red-600" />;
    default:                return <FileText size={13} className="text-gray-400" />;
  }
}

function getStatusLabel(status) {
  switch (status) {
    case "CONFIRMED":       return "Confirmed";
    case "FIXABLE_BLOCKED": return "Blocked";
    case "AT_RISK":         return "At Risk";
    case "FRAUD_FLAGGED":   return "Fraud";
    case "INELIGIBLE":      return "Ineligible";
    default:                return status || "Pending";
  }
}

/* ─── Supplier Invoice Overlay ─────────────────────────────────────────── */
function SupplierInvoiceOverlay({ supplier, apiBase, traderId, onClose }) {
  const [invoices, setInvoices]           = useState([]);
  const [loading, setLoading]             = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    if (!traderId || !supplier) return;
    setLoading(true);
    fetch(`${apiBase}/api/v1/dashboard/invoices/${traderId}`)
      .then(r => r.json())
      .then(data => {
        const all = (data.invoices || []).filter(
          inv => inv.gstin_supplier === supplier.gstin || inv.supplier_name === supplier.name
        ).sort((a, b) => new Date(b.processed_at) - new Date(a.processed_at));
        setInvoices(all);
      })
      .catch(() => setInvoices([]))
      .finally(() => setLoading(false));
  }, [supplier, traderId, apiBase]);

  function navigate(newIndex) {
    setTransitioning(true);
    setTimeout(() => { setSelectedIndex(newIndex); setTransitioning(false); }, 150);
  }

  const cfg = STATUS_CONFIG[supplier.status];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-gray-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
            <div>
              <p className="font-bold text-gray-900 text-sm">{supplier.name}</p>
              <p className="text-[10px] font-mono text-gray-400">{supplier.gstin}</p>
            </div>
            <span className={`ml-2 inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${cfg.chip}`}>
              {cfg.label}
            </span>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X size={16} className="text-gray-500" />
          </button>
        </div>

        {/* Stats strip */}
        <div className="flex divide-x divide-gray-100 border-b border-gray-100 text-center">
          <div className="flex-1 py-3">
            <p className="text-lg font-black text-gray-900">{invoices.length}</p>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Invoices</p>
          </div>
          <div className="flex-1 py-3">
            <p className="text-lg font-black text-gray-900">{supplier.health}</p>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Health Score</p>
          </div>
          <div className="flex-1 py-3">
            <p className={`text-lg font-black ${supplier.issues > 0 ? "text-red-600" : "text-gray-900"}`}>{supplier.issues}</p>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Open Issues</p>
          </div>
        </div>

        {/* Invoice list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="space-y-0 p-1">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <div className="space-y-1.5">
                    <div className="h-3 w-32 bg-gray-100 rounded animate-pulse" />
                    <div className="h-2 w-20 bg-gray-50 rounded animate-pulse" />
                  </div>
                  <div className="h-4 w-16 bg-gray-100 rounded animate-pulse" />
                </div>
              ))}
            </div>
          ) : invoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
              <FileText size={32} className="opacity-30" />
              <p className="text-sm">No invoices found for this supplier</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {invoices.map((inv, idx) => {
                const rowBg = inv.itc_status === "AT_RISK" || inv.itc_status === "FRAUD_FLAGGED"
                  ? "hover:bg-red-50/60"
                  : inv.itc_status === "FIXABLE_BLOCKED"
                  ? "hover:bg-amber-50/60"
                  : "hover:bg-gray-50";
                return (
                  <button
                    key={inv.id}
                    onClick={() => setSelectedIndex(idx)}
                    className={`w-full flex items-center justify-between px-4 py-3 transition-colors ${rowBg} group text-left`}
                  >
                    <div>
                      <p className="text-sm font-semibold text-gray-900 group-hover:text-[#10b981] transition-colors flex items-center gap-1.5">
                        {inv.invoice_number || "No Invoice #"}
                        <ArrowUpRight size={11} className="opacity-0 group-hover:opacity-100 transition-opacity text-[#10b981]" />
                      </p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {new Date(inv.processed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <p className="text-sm font-bold text-gray-900">₹{Number(inv.total_amount || 0).toLocaleString("en-IN")}</p>
                      <div className="flex items-center gap-1 text-[10px] font-semibold text-gray-500">
                        {getStatusIcon(inv.itc_status)}
                        {getStatusLabel(inv.itc_status)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Invoice detail modal (on top of overlay) */}
      {selectedIndex !== null && (
        transitioning ? (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/50 backdrop-blur-md p-8">
            <div className="bg-white w-full max-w-5xl h-[80vh] flex overflow-hidden">
              <div className="w-1/2 bg-gray-100 animate-pulse" />
              <div className="w-1/2 p-8 space-y-4">
                {[...Array(5)].map((_, i) => <div key={i} className="h-3 bg-gray-100 rounded animate-pulse" style={{ width: `${80 - i * 8}%` }} />)}
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

/* ─── Main SupplierHealth Component ────────────────────────────────────── */
export default function SupplierHealth({ traderId, apiBase, onSwitchTab }) {
  const [suppliers, setSuppliers]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [sortField, setSortField]     = useState("health");
  const [sortDir, setSortDir]         = useState("asc");
  const [activeSupplier, setActiveSupplier] = useState(null); // supplier overlay

  useEffect(() => {
    if (!traderId) return;
    setLoading(true);
    fetch(`${apiBase}/api/v1/dashboard/suppliers/${traderId}`)
      .then((r) => r.json())
      .then((data) => {
        const list = (data.suppliers || []).map((s) => ({
          id:            s.id,
          name:          s.name || s.legal_name || "Unknown",
          gstin:         s.gstin || "—",
          health:        s.health_score ?? 100,
          status:        (s.health_score ?? 100) > 80 ? "GOOD" : (s.health_score ?? 100) > 40 ? "RISK" : "CRITICAL",
          issues:        s.flags?.length ?? 0,
          flags:         s.flags || [],
          itcAmount:     s.total_amount || 0,
          lastFiled:     s.last_filed || null,
          totalInvoices: s.total_invoices || 0,
        }));
        setSuppliers(list);
      })
      .catch(() => setSuppliers([]))
      .finally(() => setLoading(false));
  }, [traderId, apiBase]);

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  const displayed = suppliers
    .filter((s) => filterStatus === "ALL" || s.status === filterStatus)
    .filter((s) => !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.gstin.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const av = a[sortField], bv = b[sortField];
      const cmp = typeof av === "string" ? av.localeCompare(bv) : av - bv;
      return sortDir === "asc" ? cmp : -cmp;
    });

  const totalGood     = suppliers.filter(s => s.status === "GOOD").length;
  const totalAtRisk   = suppliers.filter(s => s.status === "RISK").length;
  const totalBlocked  = suppliers.filter(s => s.status === "CRITICAL").length;

  const SortIcon = ({ field }) => sortField !== field ? null : sortDir === "asc"
    ? <ChevronUp size={13} className="inline ml-0.5" />
    : <ChevronDown size={13} className="inline ml-0.5" />;

  if (loading) return (
    <div className="space-y-3">
      {[1,2,3].map(i => <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />)}
    </div>
  );

  return (
    <>
      <div className="space-y-4 w-full">
        {/* Summary stat cards */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Good Standing", value: totalGood,    color: "emerald", filter: "GOOD"     },
            { label: "At Risk",       value: totalAtRisk,  color: "amber",   filter: "RISK"     },
            { label: "Blocked",       value: totalBlocked, color: "red",     filter: "CRITICAL" },
          ].map(({ label, value, color, filter }) => (
            <button
              key={filter}
              onClick={() => setFilterStatus(f => f === filter ? "ALL" : filter)}
              className={`text-left bg-white rounded-xl border p-3 transition-all hover:shadow-sm ${
                filterStatus === filter
                  ? `border-${color}-400 ring-1 ring-${color}-300`
                  : "border-gray-200"
              }`}
            >
              <p className={`text-2xl font-bold text-${color}-600`}>{value}</p>
              <p className={`text-xs text-${color}-500 mt-0.5 font-medium`}>{label}</p>
            </button>
          ))}
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search supplier or GSTIN…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981]/20"
            />
          </div>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-[#10b981] text-gray-700"
          >
            <option value="ALL">All Status</option>
            <option value="GOOD">Good</option>
            <option value="RISK">At Risk</option>
            <option value="CRITICAL">Blocked</option>
          </select>
        </div>

        {/* Table — w-full, no forced min-w so it doesn't overflow */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {[
                    { label: "Supplier",     field: "name",      cls: "text-left pl-4 pr-3 w-[28%]" },
                    { label: "GSTIN",        field: null,        cls: "text-left w-[22%]"            },
                    { label: "Health",       field: "health",    cls: "text-left w-[18%]"            },
                    { label: "Status",       field: "status",    cls: "text-left w-[14%]"            },
                    { label: "ITC",          field: "itcAmount", cls: "text-right w-[10%]"           },
                    { label: "Issues",       field: "issues",    cls: "text-center w-[8%]"           },
                  ].map(({ label, field, cls }) => (
                    <th
                      key={label}
                      onClick={() => field && handleSort(field)}
                      className={`py-2.5 px-3 text-[10px] font-bold uppercase tracking-wide text-gray-400 ${cls} ${field ? "cursor-pointer hover:text-gray-700 select-none" : ""}`}
                    >
                      {label}<SortIcon field={field} />
                    </th>
                  ))}
                  <th className="py-2.5 px-3 text-[10px] font-bold uppercase tracking-wide text-gray-400 text-center w-[10%]">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {displayed.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="py-10 text-center text-sm text-gray-400">
                      {search || filterStatus !== "ALL" ? "No suppliers match your filter." : "No supplier data yet. Upload a GSTR-2B to start."}
                    </td>
                  </tr>
                ) : displayed.map((sup) => {
                  const cfg = STATUS_CONFIG[sup.status];
                  return (
                    <tr
                      key={sup.id}
                      className="hover:bg-gray-50/80 transition-colors group cursor-pointer"
                      onClick={() => setActiveSupplier(sup)}
                    >
                      {/* Supplier name */}
                      <td className="py-3 pl-4 pr-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full flex-none ${cfg.dot}`} />
                          <span className="font-semibold text-gray-900 group-hover:text-[#10b981] transition-colors text-sm">{sup.name}</span>
                        </div>
                      </td>
                      {/* GSTIN */}
                      <td className="py-3 px-3">
                        <span className="font-mono text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{sup.gstin}</span>
                      </td>
                      {/* Health bar + score */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${cfg.bar} transition-all duration-500`}
                              style={{ width: `${sup.health}%` }}
                            />
                          </div>
                          <span className={`text-xs font-bold ${sup.health > 80 ? "text-emerald-700" : sup.health > 40 ? "text-amber-700" : "text-red-700"}`}>
                            {sup.health}
                          </span>
                        </div>
                      </td>
                      {/* Status chip */}
                      <td className="py-3 px-3">
                        <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${cfg.chip}`}>
                          {sup.status === "GOOD"     && <CheckCircle2 size={10} />}
                          {sup.status === "RISK"     && <AlertTriangle size={10} />}
                          {sup.status === "CRITICAL" && <XCircle size={10} />}
                          {cfg.label}
                        </span>
                      </td>
                      {/* ITC Amount */}
                      <td className="py-3 px-3 text-right font-semibold text-gray-900 text-sm">
                        {formatINR(sup.itcAmount)}
                      </td>
                      {/* Issues */}
                      <td className="py-3 px-3 text-center" onClick={e => { e.stopPropagation(); onSwitchTab?.("actions"); }}>
                        {sup.issues > 0 ? (
                          <span className="inline-flex items-center gap-0.5 text-xs font-bold text-red-600 hover:underline cursor-pointer">
                            {sup.issues}<ArrowUpRight size={10} />
                          </span>
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                      {/* Action */}
                      <td className="py-3 px-3 text-center" onClick={e => e.stopPropagation()}>
                        {sup.status === "GOOD" ? (
                          <button
                            onClick={() => setActiveSupplier(sup)}
                            className="text-[10px] text-gray-400 hover:text-gray-700 font-medium px-2 py-1 rounded hover:bg-gray-100 transition-colors"
                          >
                            View
                          </button>
                        ) : (
                          <button
                            onClick={e => { e.stopPropagation(); onSwitchTab?.("actions"); }}
                            className="text-[10px] font-bold text-white bg-[#10b981] hover:bg-emerald-600 px-2 py-1 rounded-lg transition-colors"
                          >
                            Fix
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Supplier invoice overlay */}
      {activeSupplier && (
        <SupplierInvoiceOverlay
          supplier={activeSupplier}
          apiBase={apiBase}
          traderId={traderId}
          onClose={() => setActiveSupplier(null)}
        />
      )}
    </>
  );
}
