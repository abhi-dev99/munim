"use client";

import { useState, useEffect } from "react";
import MoneyMeter from "./components/MoneyMeter";
import SupplierHealth from "./components/SupplierHealth";
import ActionQueue from "./components/ActionQueue";
import Sidebar from "./components/Sidebar";

// Demo trader ID — replace with dynamic after auth
const DEMO_TRADER_ID = null; // Will be fetched
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState("money-meter");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  async function fetchDashboardData() {
    try {
      // First, get the trader (dynamically fetch first trader from DB)
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
      console.error("Failed to fetch dashboard:", err);
      // Use demo data
      setSummary({
        trader_id: "demo",
        month: new Date().getMonth() + 1,
        year: new Date().getFullYear(),
        itc_buckets: {
          confirmed: 41200,
          fixable_blocked: 8600,
          at_risk: 12400,
          missed: 3200,
          ineligible: 0,
        },
        invoices_processed: 247,
        suppliers_monitored: 15,
        issues_open: 8,
        total_recovery_possible: 24200,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="flex-1 ml-64 p-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">
                <span className="gradient-text">Munim.ai</span>
              </h1>
              <p className="text-[var(--text-secondary)] mt-1">
                GST Compliance Dashboard — {new Date().toLocaleDateString("en-IN", { month: "long", year: "numeric" })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 glass-card px-4 py-2">
                <div className="pulse-dot pulse-dot-green"></div>
                <span className="text-sm text-[var(--text-secondary)]">Live</span>
              </div>
            </div>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--blue-primary)]"></div>
          </div>
        ) : (
          <>
            {activeTab === "money-meter" && <MoneyMeter summary={summary} apiBase={API_BASE} />}
            {activeTab === "suppliers" && <SupplierHealth traderId={summary?.trader_id} apiBase={API_BASE} />}
            {activeTab === "actions" && <ActionQueue traderId={summary?.trader_id} apiBase={API_BASE} />}
          </>
        )}
      </main>
    </div>
  );
}
