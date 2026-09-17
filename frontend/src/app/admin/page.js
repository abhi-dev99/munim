"use client";

import { useState, useEffect } from "react";
import { Trash2, Loader2, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [traders, setTraders] = useState([]);
  const [selectedTrader, setSelectedTrader] = useState(null);

  useEffect(() => {
    async function fetchTraders() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/dashboard/traders`);
        if (!res.ok) throw new Error("Failed to fetch traders");
        const data = await res.json();
        setTraders(data.traders || []);
        if (data.traders?.length > 0) {
          setSelectedTrader(data.traders[0].id);
        } else {
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    }
    fetchTraders();
  }, []);

  useEffect(() => {
    if (!selectedTrader) return;
    
    async function fetchInvoices() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/v1/dashboard/invoices/${selectedTrader}`);
        if (!res.ok) throw new Error("Failed to fetch invoices");
        const data = await res.json();
        setInvoices(data.invoices || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchInvoices();
  }, [selectedTrader]);

  async function handleDelete(id) {
    if (!window.confirm("Are you sure you want to delete this invoice?")) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/invoices/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Delete failed");
      
      setInvoices((prev) => prev.filter((inv) => inv.id !== id));
    } catch (err) {
      alert("Failed to delete invoice.");
    }
  }

  return (
    <div className="min-h-screen p-8 bg-[var(--background)]">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-black text-black tracking-tighter uppercase mb-2">Admin Dashboard</h1>
            <p className="text-[var(--text-secondary)] font-medium">Manage and remove test transactions</p>
          </div>
          
          <select 
            value={selectedTrader || ""}
            onChange={(e) => setSelectedTrader(e.target.value)}
            className="p-2 border border-[var(--border-subtle)] bg-white font-bold"
          >
            {traders.map(t => (
              <option key={t.id} value={t.id}>{t.name || t.business_name} ({t.id.slice(0,8)})</option>
            ))}
          </select>
        </div>

        <div className="bg-white border border-[var(--border-subtle)]">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Date</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Supplier</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Amount</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Status</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" className="p-8 text-center"><Loader2 className="animate-spin mx-auto text-black" /></td>
                </tr>
              ) : invoices.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-[var(--text-secondary)] font-medium">No invoices found.</td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)]">
                    <td className="p-4 text-sm font-medium">{inv.invoice_date?.slice(0, 10) || "N/A"}</td>
                    <td className="p-4 text-sm font-bold text-black">{inv.supplier_name || inv.gstin_supplier || "Unknown"}</td>
                    <td className="p-4 text-sm font-medium">₹{Number(inv.total_amount || 0).toLocaleString('en-IN')}</td>
                    <td className="p-4 text-sm font-medium">{inv.itc_status}</td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => handleDelete(inv.id)}
                        className="p-2 text-[var(--red-primary)] hover:bg-red-50 transition-colors"
                        title="Delete Invoice"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
