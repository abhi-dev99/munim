"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect, useRef } from "react";
import { AlertTriangle, CheckCircle2, XCircle, Search, ChevronUp, ChevronDown, ArrowUpRight, X, FileText, ShieldAlert, ChevronRight } from "lucide-react";
import InvoiceDetailModal from "./InvoiceDetailModal";
import { useLanguage } from "../context/LanguageContext";

const STATUS_CONFIG = {
  GOOD:     { labelKey: "sup_good_standing", chip: "bg-emerald-50 text-emerald-700 border-emerald-200",  dot: "bg-emerald-500", bar: "bg-emerald-500" },
  RISK:     { labelKey: "sup_at_risk",  chip: "bg-amber-50 text-amber-700 border-amber-200",        dot: "bg-amber-500",   bar: "bg-amber-500"   },
  CRITICAL: { labelKey: "sup_blocked",  chip: "bg-red-50 text-red-700 border-red-200",              dot: "bg-red-500",     bar: "bg-red-500"     },
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
  const { t } = useLanguage();
  const [invoices, setInvoices]           = useState([]);
  const [loading, setLoading]             = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    if (!traderId || !supplier) return;
    setLoading(true);
    authFetch(`${apiBase}/api/v1/dashboard/invoices/${traderId}`)
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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900/50 p-2 md:p-8 backdrop-blur-md transition-all duration-300 ease-in-out">
      {/* Outside Navigation - Close */}
      <button onClick={onClose} className="absolute top-4 right-4 md:top-8 md:right-8 z-[60] p-4 text-white/70 hover:text-white transition-all duration-300 ease-in-out">
        <X size={32} />
      </button>

      {/* Main Card (Sharp Corners to match InvoiceDetailModal) */}
      <div className="bg-white rounded-none w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col relative border border-[#E0E0E0] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
            <div>
              <p className="font-bold text-gray-900 text-sm">{supplier.name}</p>
              <p className="text-[10px] font-mono text-gray-400">{supplier.gstin}</p>
            </div>
            <span className={`ml-2 inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${cfg.chip}`}>
              {t(cfg.labelKey)}
            </span>
          </div>
        </div>

        {/* Stats strip */}
        <div className="flex divide-x divide-gray-100 border-b border-gray-100 text-center bg-gray-50">
          <div className="flex-1 py-4">
            <p className="text-xl font-black text-gray-900">{invoices.length}</p>
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{t("sup_invoices")}</p>
          </div>
          <div className="flex-1 py-4">
            <p className="text-xl font-black text-gray-900">{supplier.health}</p>
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{t("sup_health_score")}</p>
          </div>
          <div className="flex-1 py-4">
            <p className={`text-xl font-black ${supplier.issues > 0 ? "text-red-600" : "text-gray-900"}`}>{supplier.issues}</p>
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{t("sup_open_issues")}</p>
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
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2 py-20">
              <FileText size={32} className="opacity-30" />
              <p className="text-sm">{t("sup_no_invoices")}</p>
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
                    onClick={() => navigate(idx)}
                    className={`w-full flex items-center justify-between px-6 py-4 border-b border-gray-100 text-left transition-colors ${rowBg} group`}
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[11px] font-bold text-gray-900">{inv.invoice_number || "NO_NUM"}</span>
                        <span className="text-[10px] text-gray-400">•</span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${inv.itc_status === "CONFIRMED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-gray-50 text-gray-600 border-gray-200"}`}>
                          {getStatusLabel(inv.itc_status)}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-400">
                        {new Date(inv.processed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <p className="text-sm font-bold text-gray-900">₹{Number(inv.total_amount || 0).toLocaleString("en-IN")}</p>
                      <ChevronRight size={14} className="text-gray-300 group-hover:text-gray-500" />
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
    </div>
  );
}

/* ─── Main SupplierHealth Component ────────────────────────────────────── */
export default function SupplierHealth({ traderId, apiBase, onSwitchTab }) {
  const { t } = useLanguage();
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
    authFetch(`${apiBase}/api/v1/dashboard/suppliers/${traderId}`)
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

  const counts = {
    GOOD:     suppliers.filter(s => s.status === "GOOD").length,
    RISK:     suppliers.filter(s => s.status === "RISK").length,
    CRITICAL: suppliers.filter(s => s.status === "CRITICAL").length,
  };

  const SortIcon = ({ field }) => sortField !== field ? null : sortDir === "asc"
    ? <ChevronUp size={13} className="inline ml-0.5" />
    : <ChevronDown size={13} className="inline ml-0.5" />;

  if (loading) return (
    <div className="flex flex-col h-[calc(100vh-80px)] w-full">
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[1,2,3,4].map(i => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
      </div>
      <div className="h-12 bg-gray-100 rounded-xl animate-pulse mb-6" />
      <div className="flex-1 space-y-3">
        {[1,2,3,4,5].map(i => <div key={i} className="h-14 bg-gray-50 rounded-lg animate-pulse" />)}
      </div>
    </div>
  );

  const dragItem = useRef(null);
  const dragOverItem = useRef(null);
  const [cardOrder, setCardOrder] = useState(["ALL", "GOOD", "RISK", "CRITICAL"]);

  const handleCardSort = () => {
    if (dragItem.current === null || dragOverItem.current === null) return;
    let _order = [...cardOrder];
    const draggedItemContent = _order.splice(dragItem.current, 1)[0];
    _order.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    setCardOrder(_order);
  };

    return (
      <>
        <div className="flex flex-col h-[calc(100vh-120px)] w-full overflow-hidden">
          <div className="z-10 bg-[#f8fafc] pt-2 pb-4 space-y-4 flex-none">
            {/* Summary stat cards */}
        <div className="grid grid-cols-4 gap-3">
          {cardOrder.map((f, idx) => (
            <button
              key={f}
              draggable
              onDragStart={() => { dragItem.current = idx; }}
              onDragEnter={(e) => { dragOverItem.current = idx; e.preventDefault(); }}
              onDragOver={(e) => e.preventDefault()}
              onDragEnd={handleCardSort}
              onClick={() => setFilterStatus(f)}
              className={`text-left bg-white rounded-xl border p-3 transition-all hover:shadow-sm cursor-grab active:cursor-grabbing ${
                filterStatus === f
                  ? "border-emerald-500 ring-1 ring-emerald-500"
                  : "border-gray-200"
              }`}
            >
              <p className="text-2xl font-bold text-gray-900">{f === "ALL" ? suppliers.length : counts[f]}</p>
              <p className="text-xs text-gray-500 mt-0.5 font-medium">{f === "ALL" ? t("sup_all_status") : t(STATUS_CONFIG[f].labelKey)}</p>
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
        </div>

        </div> {/* Close z-10 header container */}

        {/* Table */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col flex-1 min-h-0 mb-4">
          <div className="overflow-auto flex-1">
            <table className="w-full text-sm border-collapse relative">
              <thead className="sticky top-0 z-20 shadow-sm">
                <tr className="border-b border-gray-100">
                  <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer" onClick={() => handleSort("name")}>{t("sup_supplier")}<SortIcon field="name" /></th>
                  <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">{t("sup_gstin")}</th>
                  <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer" onClick={() => handleSort("health")}>{t("sup_health")}<SortIcon field="health" /></th>
                  <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer" onClick={() => handleSort("status")}>{t("sup_status")}<SortIcon field="status" /></th>
                  <th className="text-right px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer" onClick={() => handleSort("itcAmount")}>{t("sup_itc")}<SortIcon field="itcAmount" /></th>
                  <th className="text-right px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500 cursor-pointer" onClick={() => handleSort("issues")}>{t("sup_issues")}<SortIcon field="issues" /></th>
                  <th className="text-center px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {displayed.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="py-10 text-center text-sm text-gray-400">
                      {search || filterStatus !== "ALL" ? "No suppliers match your filter." : "No supplier data yet. Upload a GSTR-2B to start."}
                    </td>
                  </tr>
                ) : displayed.map((sup, idx) => {
                  const cfg = STATUS_CONFIG[sup.status];
                  return (
                    <tr
                      key={sup.id}
                      id={`supplier-table-row-${idx}`}
                      className="hover:bg-gray-50/80 transition-colors group cursor-pointer"
                      onClick={() => setActiveSupplier(sup)}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full flex-none ${cfg.dot}`} />
                          <span className="font-semibold text-gray-900 group-hover:text-[#10b981] transition-colors text-sm">{sup.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{sup.gstin}</span>
                      </td>
                      <td className="py-3 px-4">
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
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${cfg.chip}`}>
                          {t(cfg.labelKey)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-gray-900 text-sm">
                        {formatINR(sup.itcAmount)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {sup.issues > 0 ? (
                          <span className="inline-flex items-center justify-end gap-0.5 text-xs font-bold text-red-600 hover:underline cursor-pointer" onClick={e => { e.stopPropagation(); onSwitchTab?.("actions"); }}>
                            {sup.issues}<ArrowUpRight size={10} />
                          </span>
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
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
