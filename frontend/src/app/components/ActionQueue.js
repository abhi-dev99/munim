"use client";

import { useState, useEffect } from "react";
import { Phone, CheckCircle2, ShieldAlert, ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

function WhatsAppIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  );
}

const URGENCY = {
  CRITICAL: { dot: "bg-red-500",   chip: "bg-red-50 text-red-700 border-red-200",   label: "Critical" },
  HIGH:     { dot: "bg-amber-500", chip: "bg-amber-50 text-amber-700 border-amber-200", label: "High" },
  MEDIUM:   { dot: "bg-blue-400",  chip: "bg-blue-50 text-blue-700 border-blue-200",  label: "Medium" },
};

export default function ActionQueue({ traderId, apiBase, traderPhone }) {
  const [actions, setActions]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [resolving, setResolving] = useState(null);
  const [filter, setFilter]     = useState("ALL");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!traderId) return;
    fetchActions();
  }, [traderId, apiBase]);

  async function fetchActions() {
    try {
      const res = await fetch(`${apiBase}/api/v1/dashboard/actions/${traderId}`);
      const data = await res.json();
      const list = (data.actions || []).map((a, i) => ({
        id:          a.id || i,
        supplier:    a.supplier_name || "Unknown supplier",
        amount:      a.impact_amount || 0,
        description: a.issue || "No details available",
        advisory:    a.fix_action || null,
        urgency:     (a.impact_amount || 0) > 20000 ? "CRITICAL" : (a.impact_amount || 0) > 10000 ? "HIGH" : "MEDIUM",
      }));
      setActions(list);
    } catch {
      setActions([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(id) {
    setResolving(id);
    try {
      await fetch(`${apiBase}/api/v1/dashboard/actions/${id}/resolve`, { method: "PATCH" });
      setActions(prev => prev.filter(a => a.id !== id));
    } catch { /* ignore */ }
    finally { setResolving(null); }
  }

  function waMsg(a) {
    return encodeURIComponent(
      `📋 *Munim.ai Alert*\n\nSupplier: *${a.supplier}*\nIssue: ${a.description}\nITC at stake: ₹${a.amount.toLocaleString("en-IN")}\n\n${a.advisory || "Please check with your CA."}`
    );
  }

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-40 bg-gray-200 rounded animate-pulse" />
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b border-gray-100 last:border-0">
              <div className="w-2 h-2 rounded-full bg-gray-200 flex-none animate-pulse" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 bg-gray-200 rounded w-2/3 animate-pulse" />
                <div className="h-2.5 bg-gray-100 rounded w-1/2 animate-pulse" />
              </div>
              <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────
  if (actions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-14 h-14 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
          <ShieldAlert size={24} className="text-emerald-500" />
        </div>
        <h3 className="text-base font-bold text-gray-900">All Clear!</h3>
        <p className="text-sm text-gray-400 mt-1">No issues requiring attention right now.</p>
      </div>
    );
  }

  const displayed = filter === "ALL" ? actions : actions.filter(a => a.urgency === filter);
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0 };
  actions.forEach(a => counts[a.urgency]++);

  // ── Main view ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-gray-900">Action Queue</h2>
          <p className="text-xs text-gray-400 mt-0.5">{actions.length} issue{actions.length !== 1 ? "s" : ""} pending</p>
        </div>
        {/* Filter chips */}
        <div className="flex items-center gap-1.5">
          {(["ALL", "CRITICAL", "HIGH", "MEDIUM"]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-[11px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                filter === f
                  ? f === "ALL"
                    ? "bg-gray-900 text-white border-gray-900"
                    : f === "CRITICAL"
                    ? "bg-red-600 text-white border-red-600"
                    : f === "HIGH"
                    ? "bg-amber-500 text-white border-amber-500"
                    : "bg-blue-500 text-white border-blue-500"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-400"
              }`}
            >
              {f === "ALL" ? `All (${actions.length})` : `${f.charAt(0) + f.slice(1).toLowerCase()} (${counts[f]})`}
            </button>
          ))}
        </div>
      </div>

      {/* Action list */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <AnimatePresence initial={false}>
          {displayed.map((action, idx) => {
            const cfg = URGENCY[action.urgency];
            const isOpen = expanded === action.id;
            return (
              <motion.div
                key={action.id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
              >
                {/* Main row */}
                <div
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50/80 transition-colors ${idx < displayed.length - 1 && !isOpen ? "border-b border-gray-100" : ""}`}
                  onClick={() => setExpanded(isOpen ? null : action.id)}
                >
                  {/* Urgency dot */}
                  <div className={`w-2 h-2 rounded-full flex-none ${cfg.dot}`} />

                  {/* Supplier + issue */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900 truncate">{action.supplier}</span>
                      <span className={`hidden sm:inline text-[10px] font-bold px-1.5 py-0.5 rounded border ${cfg.chip}`}>
                        {cfg.label}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">{action.description}</p>
                  </div>

                  {/* ITC amount */}
                  <div className="text-right flex-none">
                    <p className="text-sm font-bold text-gray-900">
                      {action.amount > 0 ? `₹${action.amount.toLocaleString("en-IN")}` : "—"}
                    </p>
                    <p className="text-[10px] text-gray-400">ITC at stake</p>
                  </div>

                  {/* Expand chevron */}
                  <ArrowUpRight
                    size={14}
                    className={`text-gray-400 flex-none transition-transform ${isOpen ? "rotate-90" : ""}`}
                  />
                </div>

                {/* Expanded detail panel */}
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="border-t border-gray-100 bg-gray-50 px-4 py-3 space-y-3 overflow-hidden"
                  >
                    {/* Advisory */}
                    {action.advisory && (
                      <div className="flex items-start gap-2">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mt-0.5 flex-none">Advisory</span>
                        <p className="text-xs text-gray-700 italic">{action.advisory}</p>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex items-center gap-2">
                      {/* Call */}
                      {traderPhone ? (
                        <a
                          href={`tel:${traderPhone}`}
                          onClick={e => e.stopPropagation()}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          <Phone size={12} />Call Trader
                        </a>
                      ) : (
                        <button disabled className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-100 rounded-lg text-xs text-gray-300 cursor-not-allowed">
                          <Phone size={12} />No Number
                        </button>
                      )}

                      {/* WhatsApp */}
                      {traderPhone ? (
                        <a
                          href={`https://wa.me/${traderPhone.replace(/\D/g, "")}?text=${waMsg(action)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#25D366] text-white rounded-lg text-xs font-semibold hover:bg-[#1ebe5d] transition-colors"
                        >
                          <WhatsAppIcon size={12} />WhatsApp
                        </a>
                      ) : (
                        <button disabled className="flex items-center gap-1.5 px-3 py-1.5 bg-[#25D366]/30 text-white rounded-lg text-xs cursor-not-allowed">
                          <WhatsAppIcon size={12} />WhatsApp
                        </button>
                      )}

                      {/* Mark resolved */}
                      <button
                        onClick={e => { e.stopPropagation(); handleResolve(action.id); }}
                        disabled={resolving === action.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#10b981] text-white rounded-lg text-xs font-semibold hover:bg-emerald-600 transition-colors disabled:opacity-50 ml-auto"
                      >
                        {resolving === action.id ? (
                          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white" />
                        ) : (
                          <CheckCircle2 size={12} />
                        )}
                        {resolving === action.id ? "Resolving…" : "Mark Resolved"}
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* Separator after expanded panel */}
                {isOpen && idx < displayed.length - 1 && <div className="border-b border-gray-100" />}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
