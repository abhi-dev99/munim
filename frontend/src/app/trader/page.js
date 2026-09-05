"use client";

import { useState, useEffect } from "react";
import { Menu, Camera, FileText, CheckCircle2, ShieldAlert } from "lucide-react";
import MoneyMeter from "../components/MoneyMeter";
import ActionQueue from "../components/ActionQueue";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function TraderApp() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const tradersRes = await fetch(`${API_BASE}/api/v1/dashboard/traders`);
        if (!tradersRes.ok) throw new Error("Failed to fetch traders");
        const tradersData = await tradersRes.json();
        const activeTrader = tradersData.traders?.[0]?.id || "demo";

        const res = await fetch(`${API_BASE}/api/v1/dashboard/summary/${activeTrader}`);
        if (res.ok) {
          const data = await res.json();
          setSummary(data);
          setTraderId(data.trader_id);
        }
      } catch (err) {
        console.warn("Using demo data (backend unavailable)", err);
        setSummary({
          trader_id: "demo",
          month: new Date().getMonth() + 1,
          year: new Date().getFullYear(),
          itc_buckets: { confirmed: 41200, fixable_blocked: 8600, at_risk: 12400, missed: 3200, ineligible: 0 },
        });
        setTraderId("demo");
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, []);

  return (
    <div className="flex flex-col min-h-screen pb-20">
      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[var(--border-subtle)] bg-white sticky top-0 z-10">
        <div className="flex flex-col">
          <h1 className="text-xl font-bold tracking-tight text-black">Munim.ai</h1>
          <span className="text-[10px] uppercase font-bold text-[var(--green-primary)] tracking-widest">Active</span>
        </div>
        <button className="p-2 -mr-2 text-black">
          <Menu size={24} />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 overflow-y-auto space-y-6 bg-[var(--bg-primary)]">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-black"></div>
          </div>
        ) : (
          <>
            <div className="mb-2">
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Financial Snapshot</h2>
              {/* Reuse MoneyMeter, it's responsive */}
              <MoneyMeter summary={summary} apiBase={API_BASE} />
            </div>

            <div>
              <h2 className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Required Actions</h2>
              {/* Reuse ActionQueue, it's responsive */}
              <ActionQueue traderId={traderId} apiBase={API_BASE} />
            </div>
          </>
        )}
      </main>

      {/* Fixed Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white border-t border-[var(--border-subtle)] p-4 flex gap-4">
        <button className="flex-1 flex flex-col items-center justify-center gap-1 p-2 text-[var(--text-secondary)] hover:text-black transition-colors">
          <FileText size={20} />
          <span className="text-[10px] font-bold">Reports</span>
        </button>
        
        {/* Massive Scan Button (Uber-style call to action) */}
        <button className="flex-2 flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-black text-white shadow-xl hover:bg-gray-900 transition-all transform hover:scale-105 w-full">
          <Camera size={20} />
          <span className="font-bold text-sm">Scan Invoice</span>
        </button>
      </div>
    </div>
  );
}
