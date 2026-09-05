"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, Activity, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function SupplierHealth({ traderId, apiBase }) {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!traderId) return;

    async function fetchSuppliers() {
      try {
        const res = await fetch(`${apiBase}/api/v1/dashboard/suppliers/${traderId}`);
        if (!res.ok) throw new Error("Failed to fetch suppliers");
        const data = await res.json();
        
        if (data.suppliers && data.suppliers.length > 0) {
          const formatted = data.suppliers.map(s => {
            const openIssues = s.flags ? s.flags.length : 0;
            return {
              id: s.id,
              name: s.name,
              gstin: s.gstin,
              health: s.health_score || 100,
              status: s.health_score > 80 ? "GOOD" : s.health_score > 40 ? "RISK" : "CRITICAL",
              recentIssues: openIssues,
              flags: s.flags || [],
              total_invoices: s.total_invoices || 0,
              total_amount: s.total_amount || 0,
            };
          });
          setSuppliers(formatted);
        } else {
          setSuppliers([]);
        }
      } catch (err) {
        console.warn("Using demo supplier data", err);
        setSuppliers([
          { id: 1, name: "Reliance Retail Ltd", gstin: "27AABCR1234Q1Z5", health: 98, status: "GOOD", recentIssues: 0, total_amount: 450000 },
          { id: 2, name: "Balaji Hardware", gstin: "27XXBBR4321R1Z9", health: 45, status: "RISK", recentIssues: 3, total_amount: 125000 },
          { id: 3, name: "Surat Textiles", gstin: "24PPBBS9999S1Z1", health: 12, status: "CRITICAL", recentIssues: 5, total_amount: 85000 },
          { id: 4, name: "Metro Wholesale", gstin: "27ZZBBM7777M1Z3", health: 100, status: "GOOD", recentIssues: 0, total_amount: 890000 },
        ]);
      } finally {
        setLoading(false);
      }
    }

    fetchSuppliers();
  }, [traderId, apiBase]);

  if (loading) {
    return <div className="animate-pulse flex flex-col gap-4">
      {[1, 2, 3].map(i => <div key={i} className="h-24 bg-[var(--bg-card)] rounded-xl opacity-50 border border-[var(--border-subtle)]"></div>)}
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-black">Supplier Health Monitor</h2>
          <p className="text-[var(--text-secondary)] mt-1">Real-time compliance tracking for your vendors</p>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
              <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Supplier</th>
              <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Health Score</th>
              <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Status</th>
              <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Flags</th>
              <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider text-right">Invoices</th>
            </tr>
          </thead>
          <motion.tbody 
            initial="hidden"
            animate="show"
            variants={{
              hidden: { opacity: 0 },
              show: { opacity: 1, transition: { staggerChildren: 0.05 } }
            }}
            className="divide-y divide-[var(--border-subtle)]"
          >
            <AnimatePresence>
              {suppliers.map(sup => (
                <motion.tr 
                  key={sup.id} 
                  layout
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="hover:bg-[var(--bg-card-hover)] transition-colors group"
                >
                  <td className="p-4">
                    <div className="font-semibold text-black group-hover:text-[var(--blue-primary)] transition-colors">{sup.name}</div>
                    <div className="text-sm text-[var(--text-muted)] font-medium">{sup.gstin}</div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-full bg-[var(--border-subtle)] rounded-full h-2 max-w-[100px] overflow-hidden">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${sup.health}%` }}
                          transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                          className={`h-2 rounded-full ${sup.health > 80 ? 'bg-[var(--green-primary)]' : sup.health > 40 ? 'bg-[var(--orange-primary)]' : 'bg-[var(--red-primary)]'}`}
                        ></motion.div>
                      </div>
                      <span className="text-sm font-bold text-black">{sup.health}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    {sup.status === "GOOD" && <span className="badge badge-confirmed"><CheckCircle2 size={12}/> Compliant</span>}
                    {sup.status === "RISK" && <span className="badge badge-blocked"><Activity size={12}/> Warning</span>}
                    {sup.status === "CRITICAL" && <span className="badge badge-risk"><AlertTriangle size={12}/> High Risk</span>}
                  </td>
                  <td className="p-4">
                    {sup.recentIssues === 0 ? (
                      <span className="text-[var(--text-muted)]">—</span>
                    ) : (
                      <div>
                        <span className="text-[var(--red-primary)] font-semibold">{sup.recentIssues} Open</span>
                        {sup.flags && sup.flags.slice(0, 2).map((f, i) => (
                          <div key={i} className="text-[10px] text-[var(--text-muted)] mt-0.5">{f.flag_type || f}</div>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="p-4 text-right font-semibold text-black">
                    {sup.total_amount > 0 ? (
                      <span>₹{sup.total_amount.toLocaleString('en-IN')}</span>
                    ) : (
                      <span className="text-[var(--text-muted)]">{sup.total_invoices} inv</span>
                    )}
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {suppliers.length === 0 && (
              <tr>
                <td colSpan="5" className="p-8 text-center text-[var(--text-secondary)]">
                  No suppliers found for this trader.
                </td>
              </tr>
            )}
          </motion.tbody>
        </table>
      </div>
    </div>
  );
}
