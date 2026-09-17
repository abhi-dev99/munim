"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Phone, CheckCircle2, ShieldAlert } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function ActionQueue({ traderId, apiBase }) {
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
      setActions([
        { id: 1, supplier: "Balaji Hardware", amount: 12400, description: "Supplier has not filed GSTR-1 for May. ₹12,400 ITC at risk.", fix_action: "Contact supplier", urgency: "HIGH" },
        { id: 2, supplier: "Surat Textiles", amount: 8600, description: "HSN code mismatch — rate applied differs from official rate.", fix_action: "Ask CA to correct HSN before filing", urgency: "MEDIUM" },
        { id: 3, supplier: "Unknown Trader", amount: 45000, description: "Velocity anomaly: 15 sequential invoices from new supplier.", fix_action: "Verify invoice authenticity with CA", urgency: "CRITICAL" },
      ]);
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
        // Remove from list on success
        setActions((prev) => prev.filter((a) => a.id !== actionId));
      }
    } catch (err) {
      console.error("Resolve failed:", err);
    } finally {
      setResolving(null);
    }
  }

  if (loading) {
    return <div className="animate-pulse space-y-4">
      {[1, 2, 3].map(i => <div key={i} className="h-32 bg-[var(--bg-card)] rounded-xl opacity-50 border border-[var(--border-subtle)]"></div>)}
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
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-black">Action Queue</h2>
          <p className="text-[var(--text-secondary)] mt-1">{actions.length} issues requiring attention</p>
        </div>
      </div>

      <motion.div 
        className="grid gap-4"
        initial="hidden"
        animate="show"
        variants={{
          hidden: { opacity: 0 },
          show: { opacity: 1, transition: { staggerChildren: 0.1 } }
        }}
      >
        <AnimatePresence>
          {actions.map(action => (
            <motion.div 
              key={action.id} 
              layout
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, height: 0, overflow: 'hidden' }}
              transition={{ duration: 0.3 }}
              className="glass-card p-6 flex flex-col md:flex-row gap-6 items-start md:items-center relative overflow-hidden group"
            >
              <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-[60px] opacity-10 group-hover:opacity-20 transition-opacity ${
                action.urgency === 'CRITICAL' ? 'bg-[var(--red-primary)]' :
                action.urgency === 'HIGH' ? 'bg-[var(--orange-primary)]' :
                'bg-[var(--blue-primary)]'
              }`}></div>
              <div className={`p-4 rounded flex-shrink-0 border relative z-10 ${
                action.urgency === 'CRITICAL' ? 'bg-[var(--red-glow)] border-[var(--red-glow)] text-[var(--red-primary)]' :
                action.urgency === 'HIGH' ? 'bg-[var(--orange-glow)] border-[var(--orange-glow)] text-[var(--orange-primary)]' :
                'bg-[var(--blue-glow)] border-[var(--blue-glow)] text-[var(--blue-primary)]'
              }`}>
                {action.urgency === 'CRITICAL' ? <ShieldAlert size={24} /> : <AlertCircle size={24} />}
              </div>

              <div className="flex-1 relative z-10">
                <div className="flex items-center gap-3 mb-1">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${
                    action.urgency === 'CRITICAL' ? 'bg-[var(--red-glow)] text-[var(--red-primary)] border-[var(--red-glow)]' :
                    action.urgency === 'HIGH' ? 'bg-[var(--orange-glow)] text-[var(--orange-primary)] border-[var(--orange-glow)]' :
                    'bg-[var(--blue-glow)] text-[var(--blue-primary)] border-[var(--blue-glow)]'
                  }`}>
                    {action.urgency}
                  </span>
                  <span className="text-sm font-semibold text-[var(--text-secondary)]">{action.supplier}</span>
                </div>
                <h4 className="text-lg font-bold text-black mb-1">{action.description}</h4>
                <p className="text-sm text-[var(--text-muted)]">
                  ITC at stake: <strong className="text-[var(--text-primary)]">₹{action.amount.toLocaleString('en-IN')}</strong>
                  {action.fix_action && <span className="ml-2">· Fix: {action.fix_action}</span>}
                </p>
              </div>

              <div className="flex gap-3 w-full md:w-auto mt-4 md:mt-0 flex-shrink-0 relative z-10">
                <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded bg-white border border-[var(--border-subtle)] text-black hover:bg-[var(--bg-secondary)] transition-colors font-medium">
                  <Phone size={16} />
                  <span>Call</span>
                </button>
                <button
                  onClick={() => handleResolve(action.id)}
                  disabled={resolving === action.id}
                  className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded bg-black border border-black text-white font-medium hover:bg-gray-800 hover:shadow-lg transition-all disabled:opacity-50"
                >
                  {resolving === action.id ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  ) : (
                    <CheckCircle2 size={16} />
                  )}
                  <span>{resolving === action.id ? "..." : "Resolved"}</span>
                </button>
              </div>

            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
