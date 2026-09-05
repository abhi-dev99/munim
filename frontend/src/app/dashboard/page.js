"use client";

import { useState, useEffect } from "react";
import MoneyMeter from "../components/MoneyMeter";
import SupplierHealth from "../components/SupplierHealth";
import ActionQueue from "../components/ActionQueue";
import Sidebar from "../components/Sidebar";
import InvoiceFeed from "../components/InvoiceFeed";
import GSTR2BUpload from "../components/GSTR2BUpload";
import ReportsPanel from "../components/ReportsPanel";
import GSTTimeline from "../components/GSTTimeline";
import { ChevronDown, Users, ToggleLeft, ToggleRight } from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState("money-meter");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);
  const [traders, setTraders] = useState([]);
  const [traderDropdown, setTraderDropdown] = useState(false);
  const [activeTraderName, setActiveTraderName] = useState("Loading...");
  const [actionCount, setActionCount] = useState(0);
  const [isComposition, setIsComposition] = useState(false);
  const [traderPhone, setTraderPhone] = useState(null);

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
        setActiveTraderName(list[0].name || list[0].business_name || "Trader 1");
        setTraderPhone(list[0].whatsapp_number || null);
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
    // Also fetch action count
    try {
      const actRes = await fetch(`${API_BASE}/api/v1/dashboard/actions/${tid}`);
      if (actRes.ok) {
        const actData = await actRes.json();
        setActionCount(actData.total || 0);
      }
    } catch {
      // ignore
    }
  }

  function loadDemoSummary() {
    // If no trader or backend is empty, return zeroed state, not fake demo data
    setSummary({
      trader_id: traderId || "demo",
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear(),
      itc_buckets: { confirmed: 0, fixable_blocked: 0, at_risk: 0, missed: 0, ineligible: 0 },
      invoices_processed: 0,
      suppliers_monitored: 0,
      issues_open: 0,
      total_recovery_possible: 0,
    });
  }

  function switchTrader(trader) {
    setTraderId(trader.id);
    setActiveTraderName(trader.name || trader.business_name || trader.id.slice(0, 8));
    setTraderPhone(trader.whatsapp_number || null);
    setTraderDropdown(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} actionCount={actionCount} />

      <main className="flex-1 ml-64 flex flex-col overflow-hidden">
        <header className="flex-none px-6 pt-4 pb-3 border-b border-[var(--border-subtle)] bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                <span className="gradient-text"></span>
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
                          <span>{t.name || t.business_name || t.id.slice(0, 8)}</span>
                          <span className="text-[10px] text-[var(--text-muted)] font-mono">{t.gstin ? t.gstin.slice(0, 10) : "Setup Incomplete"}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 glass-card px-4 py-2 border-[var(--border-subtle)]">
                <button 
                  onClick={() => setIsComposition(!isComposition)}
                  className="flex items-center gap-2"
                >
                  {isComposition ? <ToggleRight size={20} className="text-[var(--green-primary)]" /> : <ToggleLeft size={20} className="text-[var(--text-muted)]" />}
                  <span className="text-sm font-semibold text-black">Composition Scheme</span>
                </button>
              </div>

              <div className="flex items-center gap-2 glass-card px-4 py-2">
                <div className="pulse-dot pulse-dot-green"></div>
                <span className="text-sm text-[var(--text-secondary)]">Live</span>
              </div>
            </div>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center flex-1">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-1 grid grid-cols-3 gap-4 p-4 pt-3 overflow-hidden"
          >
            {/* Left Column — Content + InvoiceFeed */}
            <motion.div 
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1, duration: 0.3 }}
              className="col-span-2 flex flex-col gap-4 min-h-0"
            >
              <div className="flex-none max-h-[400px] overflow-y-auto pr-2">
                {activeTab === "money-meter" && <MoneyMeter summary={summary} apiBase={API_BASE} isComposition={isComposition} />}
                {activeTab === "suppliers" && <SupplierHealth traderId={traderId} apiBase={API_BASE} />}
                {activeTab === "actions" && <ActionQueue traderId={traderId} apiBase={API_BASE} traderPhone={traderPhone} />}
                {activeTab === "reports" && <ReportsPanel traderId={traderId} apiBase={API_BASE} />}
              </div>
              <div className="flex-1 min-h-0 overflow-hidden flex flex-col border border-[var(--border-subtle)] bg-white rounded-xl">
                <InvoiceFeed traderId={traderId} apiBase={API_BASE} />
              </div>
            </motion.div>
            
            {/* Right Column — Timeline + GSTR-2B */}
            <motion.div 
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15, duration: 0.3 }}
              className="col-span-1 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1"
            >
              <GSTTimeline isComposition={isComposition} />
              <GSTR2BUpload traderId={traderId} apiBase={API_BASE} />
            </motion.div>
          </motion.div>
        )}
      </main>

      {/* Close dropdown on outside click */}
      {traderDropdown && (
        <div className="fixed inset-0 z-40" onClick={() => setTraderDropdown(false)} />
      )}
    </div>
  );
}
