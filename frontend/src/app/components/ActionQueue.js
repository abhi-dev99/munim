"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Phone, CheckCircle2, ShieldAlert, MessageCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// WhatsApp SVG icon (official green)
function WhatsAppIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
    </svg>
  );
}

export default function ActionQueue({ traderId, apiBase, traderPhone }) {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(null);

  useEffect(() => {
    if (!traderId) return;
    fetchActions();
  }, [traderId, apiBase]);

  async function fetchActions() {
    try {
      const res = await fetch(`${apiBase}/api/v1/dashboard/actions/${traderId}`);
      if (!res.ok) throw new Error("Failed to fetch actions");
      const data = await res.json();
      
      if (data.actions && data.actions.length > 0) {
        const formatted = data.actions.map((a, i) => ({
          id: a.id || i,
          supplier: a.supplier_name,
          amount: a.impact_amount || 0,
          description: a.issue,
          fix_action: a.fix_action,
          urgency: a.impact_amount > 20000 ? "CRITICAL" : a.impact_amount > 10000 ? "HIGH" : "MEDIUM"
        }));
        setActions(formatted);
      } else {
        setActions([]);
      }
    } catch (err) {
      console.warn("Using demo action data:", err);
      setActions([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(actionId) {
    setResolving(actionId);
    try {
      const res = await fetch(`${apiBase}/api/v1/dashboard/actions/${actionId}/resolve`, {
        method: "PATCH",
      });
      if (res.ok) {
        setActions((prev) => prev.filter((a) => a.id !== actionId));
      }
    } catch (err) {
      console.error("Resolve failed:", err);
    } finally {
      setResolving(null);
    }
  }

  function buildWhatsAppMessage(action) {
    return encodeURIComponent(
      `📋 *Munim.ai Alert*\n\n` +
      `Supplier: *${action.supplier}*\n` +
      `Issue: ${action.description}\n` +
      `ITC at stake: ₹${action.amount.toLocaleString("en-IN")}\n\n` +
      `Advisory: ${action.fix_action || "Please check with your CA."}`
    );
  }

  if (loading) {
    return <div className="animate-pulse space-y-3">
      {[1, 2, 3].map(i => <div key={i} className="h-24 bg-[var(--bg-card)] rounded-xl opacity-50 border border-[var(--border-subtle)]"></div>)}
    </div>;
  }

  if (actions.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-black">Action Queue</h2>
        <div className="glass-card p-12 text-center">
          <div className="inline-flex p-4 rounded-full bg-[var(--green-glow)] text-[var(--green-primary)] mb-4">
            <ShieldAlert size={32} />
          </div>
          <h3 className="text-xl font-bold text-black mb-2">All Clear!</h3>
          <p className="text-[var(--text-secondary)]">No critical issues or blocked ITC requiring immediate attention.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-black">Action Queue</h2>
          <p className="text-[var(--text-secondary)] mt-0.5 text-sm">{actions.length} issues requiring attention</p>
        </div>
      </div>

      <motion.div
        className="grid gap-3"
        initial="hidden"
        animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }}
      >
        <AnimatePresence>
          {actions.map(action => (
            <motion.div
              key={action.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, height: 0, overflow: "hidden" }}
              transition={{ duration: 0.25 }}
              className="glass-card px-4 py-3 flex flex-col gap-2 relative overflow-hidden group"
            >
              {/* coloured left stripe */}
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                action.urgency === "CRITICAL" ? "bg-[var(--red-primary)]" :
                action.urgency === "HIGH" ? "bg-[var(--orange-primary)]" :
                "bg-[var(--blue-primary)]"
              }`} />

              {/* Row 1: badge + supplier + amount */}
              <div className="flex items-center gap-2 pl-3">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase border flex-shrink-0 ${
                  action.urgency === "CRITICAL" ? "bg-[var(--red-glow)] text-[var(--red-primary)] border-[var(--red-glow)]" :
                  action.urgency === "HIGH" ? "bg-[var(--orange-glow)] text-[var(--orange-primary)] border-[var(--orange-glow)]" :
                  "bg-[var(--blue-glow)] text-[var(--blue-primary)] border-[var(--blue-glow)]"
                }`}>
                  {action.urgency}
                </span>
                <span className="text-sm font-semibold text-[var(--text-secondary)] flex-1 truncate">{action.supplier}</span>
                <span className="text-sm font-bold text-black flex-shrink-0">₹{action.amount.toLocaleString("en-IN")}</span>
              </div>

              {/* Row 2: description */}
              <p className="text-sm font-medium text-black leading-snug pl-3">{action.description}</p>

              {/* Row 3: advisory + buttons */}
              <div className="flex items-center justify-between gap-3 pl-3">
                {action.fix_action ? (
                  <p className="text-xs text-[var(--text-muted)] flex items-center gap-1 min-w-0">
                    <span className="text-[10px] font-semibold bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded px-1.5 py-0.5 flex-shrink-0">
                      💬 Trader advisory
                    </span>
                    <span className="italic truncate">{action.fix_action}</span>
                  </p>
                ) : <span />}

                <div className="flex gap-2 flex-shrink-0">
                  {/* Call */}
                  {traderPhone ? (
                    <a
                      href={`tel:${traderPhone}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white border border-[var(--border-subtle)] text-black hover:bg-[var(--bg-secondary)] transition-colors text-xs font-medium"
                    >
                      <Phone size={13} /> Call
                    </a>
                  ) : (
                    <button
                      disabled
                      title="Phone number not on file"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white border border-[var(--border-subtle)] text-[var(--text-muted)] text-xs font-medium opacity-50 cursor-not-allowed"
                    >
                      <Phone size={13} /> Call
                    </button>
                  )}

                  {/* WhatsApp */}
                  {traderPhone ? (
                    <a
                      href={`https://wa.me/${traderPhone.replace(/\D/g, "")}?text=${buildWhatsAppMessage(action)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#25D366] text-white hover:bg-[#1ebe5d] transition-colors text-xs font-medium"
                    >
                      <WhatsAppIcon size={13} /> Send Text
                    </a>
                  ) : (
                    <button
                      disabled
                      title="Phone number not on file"
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#25D366]/40 text-white text-xs font-medium opacity-50 cursor-not-allowed"
                    >
                      <WhatsAppIcon size={13} /> Send Text
                    </button>
                  )}

                  {/* Resolve */}
                  <button
                    onClick={() => handleResolve(action.id)}
                    disabled={resolving === action.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-black text-white text-xs font-medium hover:bg-gray-800 transition-all disabled:opacity-50"
                  >
                    {resolving === action.id
                      ? <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white" />
                      : <CheckCircle2 size={13} />}
                    {resolving === action.id ? "..." : "Resolved"}
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

