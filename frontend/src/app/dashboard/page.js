"use client";

import { useState, useEffect } from "react";
import MoneyMeter from "../components/MoneyMeter";
import SupplierHealth from "../components/SupplierHealth";
import ActionQueue from "../components/ActionQueue";
import Sidebar from "../components/Sidebar";
import InvoiceFeed from "../components/InvoiceFeed";
import GSTR2BUpload from "../components/GSTR2BUpload";
import ReportsPanel from "../components/ReportsPanel";
import {
  ChevronDown,
  Users,
  ToggleLeft,
  ToggleRight,
  Upload,
  AlertTriangle,
  CheckCircle2,
  PieChart,
} from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatINR(amount) {
  if (!amount && amount !== 0) return "—";
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
  return `₹${amount}`;
}

// Right-rail: Supplier Risk Summary card
function SupplierRiskCard({ traderId, onSwitchTab }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!traderId) return;
    fetch(`${API_BASE}/api/v1/dashboard/suppliers/${traderId}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null));
  }, [traderId]);

  const suppliers = data?.suppliers || [];
  const good = suppliers.filter((s) => s.health_status === "GOOD").length;
  const atRisk = suppliers.filter((s) => s.health_status === "AT_RISK").length;
  const blocked = suppliers.filter((s) => s.health_status === "BLOCKED").length;
  const total = suppliers.length;

  const riskiest = [...suppliers]
    .filter((s) => s.health_status !== "GOOD")
    .sort((a, b) => (b.itc_at_risk || 0) - (a.itc_at_risk || 0))
    .slice(0, 3);

  const hasIssues = atRisk + blocked > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <PieChart size={15} className="text-gray-400" />
        <h3 className="text-sm font-bold text-gray-900">Supplier Risk</h3>
      </div>

      {/* Mini stat row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center bg-emerald-50 rounded-lg py-2">
          <p className="text-base font-bold text-emerald-700">{good}</p>
          <p className="text-[10px] text-emerald-600">Good</p>
        </div>
        <div className="text-center bg-amber-50 rounded-lg py-2">
          <p className="text-base font-bold text-amber-700">{atRisk}</p>
          <p className="text-[10px] text-amber-600">At Risk</p>
        </div>
        <div className="text-center bg-red-50 rounded-lg py-2">
          <p className="text-base font-bold text-red-700">{blocked}</p>
          <p className="text-[10px] text-red-600">Blocked</p>
        </div>
      </div>

      {/* Riskiest suppliers */}
      {riskiest.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Needs Attention</p>
          {riskiest.map((s, i) => (
            <button
              key={i}
              onClick={() => onSwitchTab?.("actions")}
              className="w-full flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0 hover:bg-gray-50 rounded transition-colors text-left"
            >
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-2 h-2 rounded-full flex-none ${
                    s.health_status === "BLOCKED" ? "bg-red-500" : "bg-amber-500"
                  }`}
                />
                <span className="text-xs text-gray-700 truncate hover:text-[#10b981] transition-colors">{s.name || s.legal_name}</span>
              </div>
              <span className="text-xs font-bold text-gray-900 ml-2 flex-none">
                {formatINR(s.itc_at_risk)}
              </span>
            </button>
          ))}
        </div>
      )}

      {total === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">No supplier data yet.</p>
      )}
    </div>
  );
}

// Right-rail: Filing Readiness card
function FilingReadinessCard({ traderId, summary, onSwitchTab }) {
  const invoicesProcessed = summary?.invoices_processed || 0;
  const issuesOpen = summary?.issues_open || 0;

  // Simple heuristic readiness: 100% if no issues, lower if there are issues or low invoice count
  let readiness = 100;
  if (issuesOpen > 0) readiness = Math.max(30, 100 - issuesOpen * 10);
  if (invoicesProcessed === 0) readiness = 0;

  const barColor =
    readiness >= 80
      ? "bg-emerald-500"
      : readiness >= 50
      ? "bg-amber-500"
      : "bg-red-500";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 size={15} className="text-gray-400" />
        <h3 className="text-sm font-bold text-gray-900">Filing Readiness</h3>
      </div>

      <div className="mb-3">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[11px] text-gray-500">GSTR-3B Readiness</span>
          <span className={`text-sm font-bold ${readiness >= 80 ? "text-emerald-600" : readiness >= 50 ? "text-amber-600" : "text-red-600"}`}>
            {readiness}%
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${readiness}%` }}
          />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Invoices processed</span>
          <span className="font-semibold text-gray-900">{invoicesProcessed}</span>
        </div>
        {issuesOpen > 0 && (
          <button
            onClick={() => onSwitchTab?.("actions")}
            className="flex items-center gap-1.5 bg-amber-50 rounded-lg px-3 py-2 w-full hover:bg-amber-100 transition-colors group"
          >
            <AlertTriangle size={12} className="text-amber-600 flex-none" />
            <span className="text-[11px] text-amber-700 font-medium group-hover:underline">
              {issuesOpen} issue{issuesOpen > 1 ? "s" : ""} need attention →
            </span>
          </button>
        )}
        {readiness === 0 && (
          <div className="flex items-center gap-1.5 bg-red-50 rounded-lg px-3 py-2">
            <AlertTriangle size={12} className="text-red-600 flex-none" />
            <span className="text-[11px] text-red-700 font-medium">Upload GSTR-2B to start</span>
          </div>
        )}
        {readiness >= 80 && issuesOpen === 0 && (
          <div className="flex items-center gap-1.5 bg-emerald-50 rounded-lg px-3 py-2">
            <CheckCircle2 size={12} className="text-emerald-600 flex-none" />
            <span className="text-[11px] text-emerald-700 font-medium">Ready to file!</span>
          </div>
        )}
      </div>

      {/* GSTR-2B upload shortcut */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <GSTR2BUpload traderId={traderId} apiBase={API_BASE} compact />
      </div>
    </div>
  );
}

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
    const authUser = localStorage.getItem("munim_auth_trader");
    if (!authUser) {
      window.location.href = "/";
      return;
    }
    const authTrader = JSON.parse(authUser);
    fetchTraders(authTrader.id);
  }, []);

  useEffect(() => {
    if (traderId) fetchSummary(traderId);
  }, [traderId]);

  async function fetchTraders(defaultId = null) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/traders`);
      const data = await res.json();
      const list = data.traders || [];
      setTraders(list);
      if (list.length > 0) {
        const matched = defaultId ? list.find((t) => t.id === defaultId) : null;
        const selected = matched || list[0];
        setTraderId(selected.id);
        setActiveTraderName(selected.name || selected.business_name || "Trader 1");
        setTraderPhone(selected.whatsapp_number || null);
        setIsComposition(selected.is_composition || false);
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
    setIsComposition(trader.is_composition || false);
    setTraderDropdown(false);
  }

  // Portfolio stats for sidebar — derived from current trader summary
  // A CA would see aggregate stats; for now reflect current trader's data
  const portfolioStats = {
    totalClients: traders.length || "—",
    clientsWithIssues: summary?.issues_open > 0 ? 1 : 0,
    totalITCAtRisk: formatINR(summary?.itc_buckets?.at_risk),
    avgScore:
      summary?.itc_buckets?.confirmed && summary?.itc_buckets?.confirmed > 0
        ? `${Math.round(
            (summary.itc_buckets.confirmed /
              Math.max(
                1,
                summary.itc_buckets.confirmed +
                  summary.itc_buckets.at_risk +
                  summary.itc_buckets.missed
              )) *
              100
          )}%`
        : "—",
  };

  const tabLabels = {
    "money-meter": "Money Meter",
    "suppliers": "Supplier Trust",
    "actions": "Action Queue",
    "reports": "Monthly Reports",
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8f9fa]">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        actionCount={actionCount}
        traderId={traderId}
        apiBase={API_BASE}
      />

      <main className="flex-1 ml-64 flex flex-col overflow-hidden">
        {/* Header — h-[65px] matches sidebar logo bar */}
        <header className="flex-none h-[65px] px-6 border-b border-gray-200 bg-white flex items-center">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <h1 className="text-base font-bold text-gray-900">{tabLabels[activeTab]}</h1>
              <span className="text-xs text-gray-400 font-medium bg-gray-100 px-2 py-0.5 rounded-full">{activeTraderName}</span>
            </div>

            <div className="flex items-center gap-3">
              {/* Trader Selector */}
              <div className="relative">
                <button
                  onClick={() => setTraderDropdown((v) => !v)}
                  className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors shadow-sm"
                >
                  <Users size={15} className="text-gray-400" />
                  <span className="text-sm font-semibold text-gray-800 max-w-[140px] truncate">
                    {activeTraderName}
                  </span>
                  <ChevronDown size={13} className="text-gray-400" />
                </button>

                {traderDropdown && (
                  <div className="absolute right-0 top-full mt-1 w-64 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
                    <div className="p-2 border-b border-gray-100">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 px-2">
                        Switch Trader
                      </p>
                    </div>
                    {traders.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-gray-400">No traders found</div>
                    ) : (
                      traders.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => switchTrader(t)}
                          className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 transition-colors flex items-center justify-between ${
                            t.id === traderId ? "font-bold text-gray-900" : "text-gray-600"
                          }`}
                        >
                          <span>{t.name || t.business_name || t.id.slice(0, 8)}</span>
                          <span className="text-[10px] text-gray-400 font-mono">
                            {t.gstin ? t.gstin.slice(0, 10) : "Setup Incomplete"}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Composition toggle */}
              <button
                onClick={() => setIsComposition(!isComposition)}
                className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors shadow-sm"
              >
                {isComposition ? (
                  <ToggleRight size={18} className="text-[#10b981]" />
                ) : (
                  <ToggleLeft size={18} className="text-gray-400" />
                )}
                <span className="text-sm font-semibold text-gray-800">Composition</span>
              </button>

              {/* Live indicator */}
              <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-sm text-gray-600">Live</span>
              </div>
            </div>
          </div>
        </header>

        {loading ? (
          <div className="flex-1 grid grid-cols-3 gap-4 p-4">
            {/* Skeleton wireframe */}
            <div className="col-span-2 flex flex-col gap-4">
              <div className="grid grid-cols-3 gap-3">
                {[1,2,3].map(i => <div key={i} className="h-32 bg-white border border-gray-200 rounded-xl animate-pulse" />)}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[1,2,3].map(i => <div key={i} className="h-24 bg-white border border-gray-200 rounded-xl animate-pulse" />)}
              </div>
              <div className="h-48 bg-white border border-gray-200 rounded-xl animate-pulse" />
              <div className="flex-1 min-h-[160px] bg-white border border-gray-200 rounded-xl animate-pulse" />
            </div>
            <div className="col-span-1 flex flex-col gap-3">
              <div className="h-44 bg-white border border-gray-200 rounded-xl animate-pulse" />
              <div className="h-52 bg-white border border-gray-200 rounded-xl animate-pulse" />
            </div>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-1 grid grid-cols-3 gap-4 p-4 overflow-hidden"
          >
            {/* Left (2/3) — Main content + Invoice Feed */}
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08, duration: 0.3 }}
              className="col-span-2 flex flex-col gap-4 min-h-0 overflow-y-auto pr-1"
            >
              {activeTab === "money-meter" && (
                <MoneyMeter summary={summary} apiBase={API_BASE} isComposition={isComposition} />
              )}
              {activeTab === "suppliers" && (
                <SupplierHealth traderId={traderId} apiBase={API_BASE} onSwitchTab={setActiveTab} />
              )}
              {activeTab === "actions" && (
                <ActionQueue traderId={traderId} apiBase={API_BASE} traderPhone={traderPhone} />
              )}
              {activeTab === "reports" && (
                <ReportsPanel traderId={traderId} apiBase={API_BASE} />
              )}

              {/* Invoice feed — always visible on money-meter tab */}
              {activeTab === "money-meter" && (
                <div className="flex-1 min-h-0 overflow-hidden flex flex-col border border-gray-200 bg-white rounded-xl" style={{ minHeight: 280 }}>
                  <InvoiceFeed traderId={traderId} apiBase={API_BASE} />
                </div>
              )}
            </motion.div>

            {/* Right (1/3) — Supplier Risk + Filing Readiness */}
            <motion.div
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.12, duration: 0.3 }}
              className="col-span-1 flex flex-col gap-3 min-h-0 overflow-y-auto pr-1"
            >
              <SupplierRiskCard traderId={traderId} onSwitchTab={setActiveTab} />
              <FilingReadinessCard traderId={traderId} summary={summary} onSwitchTab={setActiveTab} />
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
