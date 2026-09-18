"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle2, XCircle, Search, ChevronUp, ChevronDown, ArrowUpRight } from "lucide-react";

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

export default function SupplierHealth({ traderId, apiBase, onSwitchTab }) {
  const [suppliers, setSuppliers]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [sortField, setSortField]     = useState("health");
  const [sortDir, setSortDir]         = useState("asc"); // ascending = worst first

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
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">Supplier Trust</h2>
        <p className="text-sm text-gray-500 mt-0.5">Compliance health of your vendor network</p>
      </div>

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

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              {[
                { label: "Supplier",          field: "name",       cls: "text-left pl-4 pr-3"  },
                { label: "GSTIN",             field: null,          cls: "text-left"            },
                { label: "Health Score",      field: "health",     cls: "text-left"            },
                { label: "Status",            field: "status",     cls: "text-left"            },
                { label: "ITC Amount",        field: "itcAmount",  cls: "text-right"           },
                { label: "Issues",            field: "issues",     cls: "text-center"          },
              ].map(({ label, field, cls }) => (
                <th
                  key={label}
                  onClick={() => field && handleSort(field)}
                  className={`py-2.5 px-3 text-[11px] font-bold uppercase tracking-wide text-gray-500 ${cls} ${field ? "cursor-pointer hover:text-gray-900 select-none" : ""}`}
                >
                  {label}<SortIcon field={field} />
                </th>
              ))}
              <th className="py-2.5 px-3 text-[11px] font-bold uppercase tracking-wide text-gray-500 text-center">Action</th>
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
                <tr key={sup.id} className="hover:bg-gray-50/80 transition-colors group">
                  {/* Supplier name */}
                  <td className="py-3 pl-4 pr-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full flex-none ${cfg.dot}`} />
                      <span className="font-semibold text-gray-900 group-hover:text-[#10b981] transition-colors">{sup.name}</span>
                    </div>
                  </td>
                  {/* GSTIN */}
                  <td className="py-3 px-3">
                    <span className="font-mono text-[11px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{sup.gstin}</span>
                  </td>
                  {/* Health bar + score */}
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
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
                    <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border ${cfg.chip}`}>
                      {sup.status === "GOOD"     && <CheckCircle2 size={10} />}
                      {sup.status === "RISK"     && <AlertTriangle size={10} />}
                      {sup.status === "CRITICAL" && <XCircle size={10} />}
                      {cfg.label}
                    </span>
                  </td>
                  {/* ITC Amount */}
                  <td className="py-3 px-3 text-right font-semibold text-gray-900">
                    {formatINR(sup.itcAmount)}
                  </td>
                  {/* Issues — links to action queue */}
                  <td className="py-3 px-3 text-center">
                    {sup.issues > 0 ? (
                      <button
                        onClick={() => onSwitchTab?.("actions")}
                        className="inline-flex items-center gap-1 text-xs font-bold text-red-600 hover:text-red-700 hover:underline"
                        title="Go to Action Queue"
                      >
                        {sup.issues} issue{sup.issues > 1 ? "s" : ""}
                        <ArrowUpRight size={11} />
                      </button>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                  {/* Action button */}
                  <td className="py-3 px-3 text-center">
                    {sup.status === "GOOD" ? (
                      <button className="text-[11px] text-gray-400 hover:text-gray-700 font-medium px-2 py-1 rounded hover:bg-gray-100 transition-colors">
                        View
                      </button>
                    ) : (
                      <button
                        onClick={() => onSwitchTab?.("actions")}
                        className="text-[11px] font-bold text-white bg-[#10b981] hover:bg-emerald-600 px-2.5 py-1 rounded-lg transition-colors"
                      >
                        Fix Now
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
  );
}
