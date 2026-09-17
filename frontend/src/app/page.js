"use client";

import { useState, useEffect } from "react";
import MoneyMeter from "./components/MoneyMeter";
import SupplierHealth from "./components/SupplierHealth";
import ActionQueue from "./components/ActionQueue";
import Sidebar from "./components/Sidebar";
import InvoiceFeed from "./components/InvoiceFeed";
import GSTR2BUpload from "./components/GSTR2BUpload";
import ReportsPanel from "./components/ReportsPanel";
import { ChevronDown, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState("money-meter");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);
  const [traders, setTraders] = useState([]);
  const [traderDropdown, setTraderDropdown] = useState(false);
  const [activeTraderName, setActiveTraderName] = useState("Loading...");

  useEffect(() => {
    fetchTraders();
  }, []);

  useEffect(() => {
    if (traderId) fetchSummary(traderId);
  }, [traderId]);

  async function fetchTraders() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/traders`);
      const data = await res.json();
      const list = data.traders || [];
      setTraders(list);
      if (list.length > 0) {
        setTraderId(list[0].id);
        setActiveTraderName(list[0].business_name || list[0].name || "Trader 1");
      } else {
        setTraderId("demo");
        setActiveTraderName("Demo Trader");
        setLoading(false);
      }
    } catch {
      setTraderId("demo");
      setActiveTraderName("Demo Trader");
      loadDemoSummary();
    }
  }

  async function fetchSummary(tid) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/summary/${tid}`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      } else {
        loadDemoSummary();
      }
    } catch {
      loadDemoSummary();
    } finally {
      setLoading(false);
    }
  }

  function loadDemoSummary() {
    setSummary({
      trader_id: "demo",
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear(),
      itc_buckets: { confirmed: 41200, fixable_blocked: 8600, at_risk: 12400, missed: 3200, ineligible: 0 },
      invoices_processed: 247,
      suppliers_monitored: 15,
      issues_open: 8,
      total_recovery_possible: 24200,
    });
  }

  function switchTrader(trader) {
    setTraderId(trader.id);
    setActiveTraderName(trader.business_name || trader.name || trader.id.slice(0, 8));
    setTraderDropdown(false);
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 ml-64 p-8">
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
              {/* Trader Selector */}
              <div className="relative">
                <button
                  onClick={() => setTraderDropdown((v) => !v)}
                  className="flex items-center gap-2 glass-card px-4 py-2 hover:bg-[var(--bg-secondary)] transition-colors"
                >
                  <Users size={16} className="text-[var(--text-secondary)]" />
                  <span className="text-sm font-semibold text-black max-w-[150px] truncate">{activeTraderName}</span>
                  <ChevronDown size={14} className="text-[var(--text-secondary)]" />
                </button>

                {traderDropdown && (
                  <div className="absolute right-0 top-full mt-1 w-64 bg-white border border-[var(--border-subtle)] rounded-xl shadow-xl z-50 overflow-hidden">
                    <div className="p-2 border-b border-[var(--border-subtle)]">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2">Switch Trader</p>
                    </div>
                    {traders.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-[var(--text-muted)]">No traders found</div>
                    ) : (
                      traders.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => switchTrader(t)}
                          className={`w-full text-left px-4 py-3 text-sm hover:bg-[var(--bg-primary)] transition-colors flex items-center justify-between ${
                            t.id === traderId ? "font-bold text-black" : "text-[var(--text-secondary)]"
                          }`}
                        >
                          <span>{t.business_name || t.name || t.id.slice(0, 8)}</span>
                          <span className="text-[10px] text-[var(--text-muted)] font-mono">{(t.gstin || "").slice(0, 10)}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 glass-card px-4 py-2">
                <div className="pulse-dot pulse-dot-green"></div>
                <span className="text-sm text-[var(--text-secondary)]">Live</span>
              </div>
            </div>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {activeTab === "money-meter" && <MoneyMeter summary={summary} apiBase={API_BASE} />}
              {activeTab === "suppliers" && <SupplierHealth traderId={traderId} apiBase={API_BASE} />}
              {activeTab === "actions" && <ActionQueue traderId={traderId} apiBase={API_BASE} />}
              {activeTab === "reports" && <ReportsPanel traderId={traderId} apiBase={API_BASE} />}
            </div>
            {/* Right Column - Upload + Live Feed */}
            <div className="lg:col-span-1 space-y-6">
              <GSTR2BUpload traderId={traderId} apiBase={API_BASE} />
              <InvoiceFeed traderId={traderId} apiBase={API_BASE} />
            </div>
          </div>
        )}
      </main>

      {/* Close dropdown on outside click */}
      {traderDropdown && (
        <div className="fixed inset-0 z-40" onClick={() => setTraderDropdown(false)} />
      )}
    </div>
  );
}
