"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect } from "react";
import {
  CheckCircle2, XCircle, Clock, AlertTriangle, ShieldAlert,
  ChevronDown, ChevronUp, Search, RotateCcw
} from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const ACTION_CONFIG = {
  accept:  { label: "Accept",  chip: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2 },
  pending: { label: "Pending", chip: "bg-amber-50 text-amber-700 border-amber-200",     icon: Clock         },
  reject:  { label: "Reject",  chip: "bg-red-50 text-red-700 border-red-200",           icon: XCircle       },
};

const ITC_STATUS_CONFIG = {
  CONFIRMED:       { dot: "bg-emerald-500", label: "Confirmed"  },
  FIXABLE_BLOCKED: { dot: "bg-amber-500",   label: "Fixable"    },
  AT_RISK:         { dot: "bg-amber-500",   label: "At Risk"    },
  FRAUD_FLAGGED:   { dot: "bg-red-600",     label: "Fraud"      },
  INELIGIBLE:      { dot: "bg-gray-400",    label: "Ineligible" },
};

function formatINR(n) {
  if (!n && n !== 0) return "—";
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000)   return `₹${(n / 1000).toFixed(0)}K`;
  return `₹${n.toFixed(0)}`;
}

export default function IMSPanel({ traderId, apiBase }) {
  const { t } = useLanguage();
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [actions, setActions] = useState({});  // invoice_id → "accept"|"pending"|"reject"
  const [search, setSearch]   = useState("");
  const [filter, setFilter]   = useState("ALL");
  const [month, setMonth]     = useState(new Date().getMonth() + 1);
  const [year, setYear]       = useState(new Date().getFullYear());

  useEffect(() => {
    if (!traderId || traderId === "demo") { setLoading(false); return; }
    load();
  }, [traderId, month, year]);

  async function load() {
    setLoading(true);
    try {
      const res = await authFetch(`${apiBase}/api/v1/dashboard/ims/${traderId}?month=${month}&year=${year}`);
      const json = await res.json();
      setData(json);
      // Seed local overrides from engine defaults
      const init = {};
      (json.invoices || []).forEach(inv => { init[inv.invoice_id] = inv.ims_action; });
      setActions(init);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  function setAction(invoice_id, action) {
    setActions(prev => ({ ...prev, [invoice_id]: action }));
  }

  function resetAll() {
    if (!data) return;
    const reset = {};
    data.invoices.forEach(inv => { reset[inv.invoice_id] = inv.ims_action; });
    setActions(reset);
  }

  const invoices = (data?.invoices || []).filter(inv => {
    const matchSearch = !search ||
      inv.invoice_number?.toLowerCase().includes(search.toLowerCase()) ||
      inv.supplier_name?.toLowerCase().includes(search.toLowerCase()) ||
      inv.supplier_gstin?.toLowerCase().includes(search.toLowerCase());
    const currentAction = actions[inv.invoice_id] || inv.ims_action;
    const matchFilter = filter === "ALL" || currentAction === filter;
    return matchSearch && matchFilter;
  });

  // Live tallies from local override state
  const liveAccept  = (data?.invoices || []).filter(inv => actions[inv.invoice_id] === "accept").length;
  const livePending = (data?.invoices || []).filter(inv => actions[inv.invoice_id] === "pending").length;
  const liveReject  = (data?.invoices || []).filter(inv => actions[inv.invoice_id] === "reject").length;
  const liveITC     = (data?.invoices || []).filter(inv => actions[inv.invoice_id] === "accept")
                       .reduce((sum, inv) => sum + (inv.total_tax || 0), 0);

  const periodOptions = [];
  for (let m = 1; m <= 12; m++) {
    periodOptions.push({ label: `${MONTHS[m]} ${year}`, month: m, year });
  }

  return (
    <div className="space-y-4 w-full">
      {/* Header + period picker */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-gray-900">Invoice Management System (IMS)</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Defaults are set by Munim.ai engine — override any decision before filing.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <select
            value={`${year}-${month}`}
            onChange={e => {
              const [y, m] = e.target.value.split("-");
              setYear(Number(y)); setMonth(Number(m));
            }}
            className="text-xs border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:border-[#10b981]"
          >
            {Array.from({ length: 6 }, (_, i) => {
              const d = new Date();
              d.setMonth(d.getMonth() - i);
              const m = d.getMonth() + 1;
              const y = d.getFullYear();
              return <option key={`${y}-${m}`} value={`${y}-${m}`}>{MONTHS[m]} {y}</option>;
            })}
          </select>
          <button onClick={resetAll} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-2 transition-colors bg-white">
            <RotateCcw size={13} /> Reset
          </button>
        </div>
      </div>

      {/* Summary stat strip */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Accepted", value: liveAccept,  color: "emerald", filter: "accept"  },
          { label: "Pending",  value: livePending, color: "amber",   filter: "pending" },
          { label: "Rejected", value: liveReject,  color: "red",     filter: "reject"  },
          { label: "ITC Accepted", value: formatINR(liveITC), color: "gray", filter: "ALL" },
        ].map(stat => (
          <button
            key={stat.filter}
            onClick={() => setFilter(f => f === stat.filter ? "ALL" : stat.filter)}
            className={`text-left bg-white rounded-xl border p-3 transition-all hover:shadow-sm ${
              filter === stat.filter ? "border-[#10b981] ring-1 ring-[#10b981]" : "border-gray-200"
            }`}
          >
            <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
            <p className="text-xs text-gray-500 mt-0.5 font-medium">{stat.label}</p>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search supplier, invoice #..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981]/20"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Supplier</th>
                <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Invoice #</th>
                <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Date</th>
                <th className="text-right px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Tax Amt</th>
                <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Engine Verdict</th>
                <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">2B Match</th>
                <th className="text-center px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">IMS Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                [...Array(6)].map((_, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    {[...Array(7)].map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 bg-gray-100 rounded animate-pulse" style={{ width: `${60 + j * 5}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : invoices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400 text-sm">
                    {data ? "No invoices match the selected filters." : "No invoice data available for this period."}
                  </td>
                </tr>
              ) : (
                invoices.map(inv => {
                  const currentAction = actions[inv.invoice_id] || "pending";
                  const isOverridden = currentAction !== inv.ims_action;
                  const itcCfg = ITC_STATUS_CONFIG[inv.itc_status] || { dot: "bg-gray-300", label: inv.itc_status };
                  const matchLabel = {
                    MATCHED: "✓ Matched",
                    PROBABLE_MATCH: "~ Probable",
                    POSSIBLE_MATCH: "? Possible",
                    ITC_AT_RISK: "✗ Not Found",
                    UNRECONCILED: "—",
                  }[inv.gstr2b_match] || "—";

                  return (
                    <tr key={inv.invoice_id} className="hover:bg-gray-50/60 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-gray-900 text-sm">{inv.supplier_name}</p>
                        <p className="text-[10px] font-mono text-gray-400">{inv.supplier_gstin}</p>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">{inv.invoice_number || "—"}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900 text-sm">
                        {formatINR(inv.total_tax)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <div className={`w-2 h-2 rounded-full flex-none ${itcCfg.dot}`} />
                          <span className="text-xs text-gray-700">{itcCfg.label}</span>
                        </div>
                        {inv.itc_reason && (
                          <p className="text-[10px] text-gray-400 mt-0.5 max-w-[160px] truncate" title={inv.itc_reason}>{inv.itc_reason}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-mono ${
                          inv.gstr2b_match === "MATCHED" ? "text-emerald-600" :
                          inv.gstr2b_match === "ITC_AT_RISK" ? "text-red-500" :
                          "text-amber-600"
                        }`}>{matchLabel}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          {["accept", "pending", "reject"].map(act => {
                            const cfg = ACTION_CONFIG[act];
                            const Icon = cfg.icon;
                            const isActive = currentAction === act;
                            return (
                              <button
                                key={act}
                                onClick={() => setAction(inv.invoice_id, act)}
                                title={cfg.label}
                                className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold border transition-all ${
                                  isActive ? cfg.chip : "bg-white text-gray-400 border-gray-100 hover:border-gray-300"
                                }`}
                              >
                                <Icon size={11} />
                                <span className="hidden sm:inline">{cfg.label}</span>
                              </button>
                            );
                          })}
                          {isOverridden && (
                            <span className="ml-1 text-[9px] text-amber-500 font-bold">CA</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
