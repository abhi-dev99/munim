"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Phone, ArrowRight, ShieldAlert } from "lucide-react";

export default function ActionQueue({ traderId, apiBase }) {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (traderId) {
      setTimeout(() => {
        setActions([
          { id: 1, type: "GSTR1_MISSING", supplier: "Balaji Hardware", amount: 12400, description: "Supplier has not filed GSTR-1 for May. Your ₹12,400 ITC is blocked.", urgency: "HIGH" },
          { id: 2, type: "HSN_MISMATCH", supplier: "Surat Textiles", amount: 8600, description: "HSN code on invoice (1234) does not match GSTR-2B. Rate mismatch likely.", urgency: "MEDIUM" },
          { id: 3, type: "FRAUD_RISK", supplier: "Unknown Trader", amount: 45000, description: "Velocity anomaly detected. 15 sequential invoices from new supplier.", urgency: "CRITICAL" },
        ]);
        setLoading(false);
      }, 600);
    }
  }, [traderId]);

  if (loading) {
    return <div className="animate-pulse space-y-4">
      {[1, 2, 3].map(i => <div key={i} className="h-32 bg-[var(--bg-card)] rounded-xl opacity-50"></div>)}
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Action Queue</h2>
          <p className="text-[var(--text-secondary)] mt-1">Issues requiring your immediate attention</p>
        </div>
      </div>

      <div className="grid gap-4">
        {actions.map(action => (
          <div key={action.id} className="glass-card p-6 flex flex-col md:flex-row gap-6 items-start md:items-center">
            
            <div className={`p-4 rounded-full flex-shrink-0 ${
              action.urgency === 'CRITICAL' ? 'bg-[var(--red-glow)] text-[var(--red-primary)]' :
              action.urgency === 'HIGH' ? 'bg-[var(--orange-glow)] text-[var(--orange-primary)]' :
              'bg-[var(--blue-glow)] text-[var(--blue-primary)]'
            }`}>
              {action.urgency === 'CRITICAL' ? <ShieldAlert size={24} /> : <AlertCircle size={24} />}
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                  action.urgency === 'CRITICAL' ? 'bg-[var(--red-primary)] text-white' :
                  action.urgency === 'HIGH' ? 'bg-[var(--orange-primary)] text-white' :
                  'bg-[var(--blue-primary)] text-white'
                }`}>
                  {action.urgency}
                </span>
                <span className="text-sm font-semibold text-[var(--text-secondary)]">{action.supplier}</span>
              </div>
              <h4 className="text-lg font-bold text-white mb-1">{action.description}</h4>
              <p className="text-sm text-[var(--text-muted)]">ITC at stake: <strong className="text-[var(--text-primary)]">₹{action.amount.toLocaleString('en-IN')}</strong></p>
            </div>

            <div className="flex gap-3 w-full md:w-auto mt-4 md:mt-0 flex-shrink-0">
              <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] text-white hover:bg-[var(--bg-card-hover)] transition-colors">
                <Phone size={16} />
                <span>Call Supplier</span>
              </button>
              <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[var(--blue-primary)] text-white font-medium hover:bg-blue-600 transition-colors shadow-[var(--shadow-glow-blue)]">
                <span>Resolve</span>
                <ArrowRight size={16} />
              </button>
            </div>

          </div>
        ))}
      </div>
    </div>
  );
}
