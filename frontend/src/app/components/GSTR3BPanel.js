"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect } from "react";
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert, FileText, RefreshCw } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

const MONTHS = ["", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

function fmt(n) {
  if (!n && n !== 0) return "—";
  return `₹${Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
function pct(part, total) {
  if (!total) return "—";
  return `${((part / total) * 100).toFixed(1)}%`;
}

export default function GSTR3BPanel({ traderId, apiBase }) {
  const { t } = useLanguage();
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth]     = useState(new Date().getMonth() + 1);
  const [year, setYear]       = useState(new Date().getFullYear());

  useEffect(() => {
    if (!traderId || traderId === "demo") { setLoading(false); return; }
    load();
  }, [traderId, month, year]);

  async function load() {
    setLoading(true);
    try {
      const res = await authFetch(`${apiBase}/api/v1/dashboard/gstr3b/${traderId}?month=${month}&year=${year}`);
      const json = await res.json();
      setData(json);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const t4 = data?.table4;
  const g2b = data?.gstr2b_summary;
  const inv = data?.invoice_summary;

  return (
    <div className="space-y-5 w-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-gray-900">GSTR-3B Auto-Draft</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            ITC computed from reconciled invoices · Output liability requires GSTR-1 data
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
          <button onClick={load} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-2 transition-colors bg-white">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-36 bg-white border border-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : !data ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center text-gray-400">
          <FileText size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No invoice data for this period. Upload invoices to generate GSTR-3B draft.</p>
        </div>
      ) : (
        <>
          {/* Invoice Summary Strip */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Confirmed ITC", value: inv?.confirmed || 0, color: "emerald", icon: CheckCircle2 },
              { label: "At Risk",       value: inv?.at_risk   || 0, color: "amber",   icon: AlertTriangle },
              { label: "Blocked",       value: inv?.blocked   || 0, color: "red",     icon: XCircle },
            ].map(stat => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} className="bg-white border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon size={14} className={`text-${stat.color}-500`} />
                    <p className="text-xs text-gray-500 font-medium">{stat.label}</p>
                  </div>
                  <p className={`text-2xl font-bold text-${stat.color}-600`}>{stat.value}</p>
                  <p className="text-xs text-gray-400">invoices</p>
                </div>
              );
            })}
          </div>

          {/* Table 4: ITC */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Table 4 — ITC Availability</h3>
                <p className="text-[10px] text-gray-400">As per Section 16 — computed from Munim.ai engine</p>
              </div>
              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">REAL DATA</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left px-5 py-2.5 text-xs font-bold text-gray-500 uppercase tracking-wide">Head</th>
                  <th className="text-right px-5 py-2.5 text-xs font-bold text-gray-500 uppercase tracking-wide">IGST</th>
                  <th className="text-right px-5 py-2.5 text-xs font-bold text-gray-500 uppercase tracking-wide">CGST</th>
                  <th className="text-right px-5 py-2.5 text-xs font-bold text-gray-500 uppercase tracking-wide">SGST</th>
                  <th className="text-right px-5 py-2.5 text-xs font-bold text-gray-500 uppercase tracking-wide">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                <tr className="hover:bg-emerald-50/30">
                  <td className="px-5 py-3 text-sm text-gray-700 font-medium">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      4(A) ITC Available — Eligible
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.igst_available)}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.cgst_available)}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.sgst_available)}</td>
                  <td className="px-5 py-3 text-right font-bold text-emerald-700">{fmt(t4?.total_available)}</td>
                </tr>
                <tr className="hover:bg-amber-50/30">
                  <td className="px-5 py-3 text-sm text-gray-700 font-medium">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-amber-500" />
                      4(B) ITC Reversed — Blocked/Ineligible
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.igst_blocked)}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.cgst_blocked)}</td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">{fmt(t4?.sgst_blocked)}</td>
                  <td className="px-5 py-3 text-right font-bold text-amber-600">{fmt(t4?.total_blocked)}</td>
                </tr>
                <tr className="hover:bg-red-50/30">
                  <td className="px-5 py-3 text-sm text-gray-700 font-medium">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-red-500" />
                      4(C) ITC At Risk — Supplier not filed
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right text-gray-500" colSpan={3}>Across all heads</td>
                  <td className="px-5 py-3 text-right font-bold text-red-600">{fmt(t4?.at_risk)}</td>
                </tr>
                <tr className="bg-gray-50">
                  <td className="px-5 py-3 text-sm font-bold text-gray-900">Net ITC Claimable (4A - 4B)</td>
                  <td className="px-5 py-3 text-right font-bold text-gray-900" colSpan={3}></td>
                  <td className="px-5 py-3 text-right font-bold text-gray-900 text-base">
                    {fmt((t4?.total_available || 0) - (t4?.total_blocked || 0))}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* GSTR-2B Summary */}
          {g2b && g2b.total_records > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
                <h3 className="text-sm font-bold text-gray-900">GSTR-2B Auto-Population Summary</h3>
                <p className="text-[10px] text-gray-400">{g2b.total_records} records from portal</p>
              </div>
              <div className="grid grid-cols-4 divide-x divide-gray-100">
                {[
                  { label: "IGST in 2B", value: fmt(g2b.total_igst) },
                  { label: "CGST in 2B", value: fmt(g2b.total_cgst) },
                  { label: "SGST in 2B", value: fmt(g2b.total_sgst) },
                  { label: "Total Tax in 2B", value: fmt(g2b.total_tax) },
                ].map(item => (
                  <div key={item.label} className="px-5 py-4 text-center">
                    <p className="text-lg font-bold text-gray-900">{item.value}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Table 3.1 Placeholder — honest, not fake */}
          <div className="bg-white border border-dashed border-gray-300 rounded-xl p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle size={18} className="text-amber-500 flex-none mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-gray-900">Table 3.1 — Output Tax Liability</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Output liability (what you owe on your own sales) requires outward supply data from GSTR-1.
                  Munim.ai currently processes your <strong>purchase-side ITC</strong> — the sharper compliance risk for most traders.
                  Output-side filing is managed by your CA using your sales register.
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">GSTR-1 Required</span>
                  <span className="text-[10px] text-gray-400">Available in v2 when outward supply data is added</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
