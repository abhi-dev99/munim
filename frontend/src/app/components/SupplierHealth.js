"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, Activity, CheckCircle2 } from "lucide-react";

export default function SupplierHealth({ traderId, apiBase }) {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (traderId) {
      // Mock data for hackathon UI
      setTimeout(() => {
        setSuppliers([
          { id: 1, name: "Reliance Retail Ltd", gstin: "27AABCR1234Q1Z5", health: 98, status: "GOOD", recentIssues: 0, total_amount: 450000 },
          { id: 2, name: "Balaji Hardware", gstin: "27XXBBR4321R1Z9", health: 45, status: "RISK", recentIssues: 3, total_amount: 125000 },
          { id: 3, name: "Surat Textiles", gstin: "24PPBBS9999S1Z1", health: 12, status: "CRITICAL", recentIssues: 5, total_amount: 85000 },
          { id: 4, name: "Metro Wholesale", gstin: "27ZZBBM7777M1Z3", health: 100, status: "GOOD", recentIssues: 0, total_amount: 890000 },
        ]);
        setLoading(false);
      }, 800);
    }
  }, [traderId]);

  if (loading) {
    return <div className="animate-pulse flex flex-col gap-4">
      {[1, 2, 3].map(i => <div key={i} className="h-24 bg-[var(--bg-card)] rounded-xl opacity-50"></div>)}
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Supplier Health Monitor</h2>
          <p className="text-[var(--text-secondary)] mt-1">Real-time compliance tracking for your vendors</p>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-[rgba(0,0,0,0.2)]">
              <th className="p-4 text-sm font-semibold text-[var(--text-secondary)]">Supplier</th>
              <th className="p-4 text-sm font-semibold text-[var(--text-secondary)]">Health Score</th>
              <th className="p-4 text-sm font-semibold text-[var(--text-secondary)]">Status</th>
              <th className="p-4 text-sm font-semibold text-[var(--text-secondary)]">Recent Issues</th>
              <th className="p-4 text-sm font-semibold text-[var(--text-secondary)] text-right">Volume (MTD)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {suppliers.map(sup => (
              <tr key={sup.id} className="hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                <td className="p-4">
                  <div className="font-medium text-white">{sup.name}</div>
                  <div className="text-sm text-[var(--text-muted)]">{sup.gstin}</div>
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-full bg-[var(--bg-secondary)] rounded-full h-2 max-w-[100px]">
                      <div 
                        className={`h-2 rounded-full ${sup.health > 80 ? 'bg-[var(--green-primary)]' : sup.health > 40 ? 'bg-[var(--orange-primary)]' : 'bg-[var(--red-primary)]'}`}
                        style={{ width: `${sup.health}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-bold">{sup.health}</span>
                  </div>
                </td>
                <td className="p-4">
                  {sup.status === "GOOD" && <span className="badge badge-confirmed"><CheckCircle2 size={12}/> Compliant</span>}
                  {sup.status === "RISK" && <span className="badge badge-blocked"><Activity size={12}/> Warning</span>}
                  {sup.status === "CRITICAL" && <span className="badge badge-risk"><AlertTriangle size={12}/> High Risk</span>}
                </td>
                <td className="p-4">
                  {sup.recentIssues === 0 ? (
                    <span className="text-[var(--text-muted)]">-</span>
                  ) : (
                    <span className="text-[var(--orange-primary)] font-medium">{sup.recentIssues} Open</span>
                  )}
                </td>
                <td className="p-4 text-right font-medium">
                  ₹{sup.total_amount.toLocaleString('en-IN')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
