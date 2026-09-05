"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect, useRef } from "react";
import MoneyMeter from "../components/MoneyMeter";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import SupplierHealth from "../components/SupplierHealth";
import ActionQueue from "../components/ActionQueue";
import Sidebar from "../components/Sidebar";
import InvoiceFeed from "../components/InvoiceFeed";
import GSTR2BUpload from "../components/GSTR2BUpload";
import ReportsPanel from "../components/ReportsPanel";
import { useLanguage } from "../context/LanguageContext";
import {
  ChevronDown,
  Users,
  ToggleLeft,
  ToggleRight,
  Upload,
  AlertTriangle,
  CheckCircle2,
  PieChart,
  Globe,
  Lightbulb,
} from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatINR(amount) {
  if (!amount && amount !== 0) return "—";
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
  return `₹${amount}`;
}

// Right-rail: Quick Links Card
function QuickLinksCard({ traderId }) {
  const portalUrl = `/demo/index.html${traderId && traderId !== 'demo' ? `?traderId=${traderId}` : ''}`;
  
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 mt-3">
      <div className="flex items-center gap-2 mb-3">
        <Globe size={15} className="text-gray-400" />
        <h3 className="text-sm font-bold text-gray-900">Quick Links</h3>
      </div>
      
      <div className="space-y-2">
        <a 
          href={portalUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="group flex items-center justify-between p-2.5 rounded-lg border border-gray-100 hover:border-blue-200 hover:bg-blue-50 transition-colors"
        >
          <div className="flex flex-col">
            <span className="text-xs font-bold text-gray-800 group-hover:text-blue-700 transition-colors">GST Portal Dashboard</span>
            <span className="text-[10px] text-gray-500">IMS, GSTR-2B, GSTR-3B</span>
          </div>
          <span className="text-gray-400 group-hover:text-blue-600 transition-colors">→</span>
        </a>

        <button 
          className="w-full flex items-center justify-between p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-colors opacity-70 cursor-not-allowed"
          title="Coming soon"
        >
          <div className="flex flex-col text-left">
            <span className="text-xs font-bold text-gray-800">E-Way Bill System</span>
            <span className="text-[10px] text-gray-500">Generate & Manage EWB</span>
          </div>
          <span className="text-gray-400">→</span>
        </button>

        <button 
          className="w-full flex items-center justify-between p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-colors opacity-70 cursor-not-allowed"
          title="Coming soon"
        >
          <div className="flex flex-col text-left">
            <span className="text-xs font-bold text-gray-800">E-Invoice Portal</span>
            <span className="text-[10px] text-gray-500">IRN Generation</span>
          </div>
          <span className="text-gray-400">→</span>
        </button>
      </div>
    </div>
  );
}

// Right-rail: Supplier Risk Summary card
function SupplierRiskCard({ traderId, onSwitchTab }) {
  const { t } = useLanguage();
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!traderId) return;
    authFetch(`${API_BASE}/api/v1/dashboard/suppliers/${traderId}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null));
  }, [traderId]);

  // Derive status from health_score — mirrors SupplierHealth.js logic exactly
  const withStatus = (s) => ({
    ...s,
    _status: (s.health_score ?? 100) > 80 ? "GOOD" : (s.health_score ?? 100) > 40 ? "RISK" : "CRITICAL",
  });

  const suppliers = (data?.suppliers || []).map(withStatus);
  const good    = suppliers.filter((s) => s._status === "GOOD").length;
  const atRisk  = suppliers.filter((s) => s._status === "RISK").length;
  const blocked = suppliers.filter((s) => s._status === "CRITICAL").length;
  const total   = suppliers.length;

  const riskiest = [...suppliers]
    .filter((s) => s._status !== "GOOD")
    .sort((a, b) => (a.health_score ?? 100) - (b.health_score ?? 100)) // lowest score = worst
    .slice(0, 3);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <PieChart size={15} className="text-gray-400" />
        <h3 className="text-sm font-bold text-gray-900">{t("sup_risk_title") || "Supplier Risk"}</h3>
      </div>

      {/* Mini stat row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center bg-emerald-50 rounded-lg py-2">
          <p className="text-base font-bold text-emerald-700">{good}</p>
          <p className="text-[10px] text-emerald-600">{t("sup_good_short") || "Good"}</p>
        </div>
        <div className="text-center bg-amber-50 rounded-lg py-2">
          <p className="text-base font-bold text-amber-700">{atRisk}</p>
          <p className="text-[10px] text-amber-600">{t("sup_at_risk_short") || "At Risk"}</p>
        </div>
        <div className="text-center bg-red-50 rounded-lg py-2">
          <p className="text-base font-bold text-red-700">{blocked}</p>
          <p className="text-[10px] text-red-600">{t("sup_blocked_short") || "Blocked"}</p>
        </div>
      </div>

      {/* Riskiest suppliers */}
      {riskiest.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{t("sup_needs_attention") || "Needs Attention"}</p>
          {riskiest.map((s, i) => (
            <button
              key={i}
              onClick={() => onSwitchTab?.("suppliers")}
              className="w-full flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0 hover:bg-gray-50 rounded transition-colors text-left"
            >
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-2 h-2 rounded-full flex-none ${
                    s._status === "CRITICAL" ? "bg-red-500" : "bg-amber-500"
                  }`}
                />
                <span className="text-xs text-gray-700 truncate hover:text-[#10b981] transition-colors">
                  {s.legal_name || s.name || s.gstin || "Unknown"}
                </span>
              </div>
              <span className="text-xs font-semibold text-gray-400 ml-2 flex-none">
                {s.health_score ?? "—"}
              </span>
            </button>
          ))}
        </div>
      )}

      {total === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">{t("sup_no_data_short") || "No supplier data yet."}</p>
      )}
    </div>
  );
}

// Right-rail: Filing Readiness card
function FilingReadinessCard({ traderId, summary, onSwitchTab }) {
  const { t } = useLanguage();
  const invoicesProcessed = summary?.invoices_processed || 0;
  const issuesOpen = summary?.issues_open || 0;

  // Simple heuristic readiness: 100% if no issues, lower if there are issues or low invoice count
  let readiness = 100;
  if (issuesOpen > 0) readiness = Math.max(30, 100 - issuesOpen * 10);
  if (invoicesProcessed === 0) readiness = 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 size={14} className="text-gray-400" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-800">{t("fr_gstr3b_readiness") || "Filing Readiness"}</h3>
      </div>

      <div className="space-y-1 mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-500">GSTR-3B Readiness</span>
          <span className={`font-bold ${readiness >= 80 ? 'text-[#10b981]' : readiness >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
            {readiness}%
          </span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${readiness >= 80 ? 'bg-[#10b981]' : readiness >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${readiness}%` }}
          />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">{t("fr_invoices_processed") || "Invoices processed"}</span>
          <span className="font-semibold text-gray-900">{invoicesProcessed}</span>
        </div>
        {issuesOpen > 0 && (
          <button
            onClick={() => onSwitchTab?.("actions")}
            className="flex items-center gap-1.5 bg-amber-50 rounded-lg px-3 py-2 w-full hover:bg-amber-100 transition-colors group"
          >
            <AlertTriangle size={12} className="text-amber-600 flex-none" />
            <span className="text-[11px] text-amber-700 font-medium group-hover:underline">
              {issuesOpen} {t("fr_issues_need_attention") || "issues need attention →"}
            </span>
          </button>
        )}
        {readiness === 0 && (
          <div className="flex items-center gap-1.5 bg-red-50 rounded-lg px-3 py-2">
            <AlertTriangle size={12} className="text-red-600 flex-none" />
            <span className="text-[11px] text-red-700 font-medium">{t("fr_upload_start") || "Upload GSTR-2B to start"}</span>
          </div>
        )}
        {readiness >= 80 && issuesOpen === 0 && (
          <div className="flex items-center gap-1.5 bg-emerald-50 rounded-lg px-3 py-2">
            <CheckCircle2 size={12} className="text-emerald-600 flex-none" />
            <span className="text-[11px] text-emerald-700 font-medium">{t("fr_ready_to_file") || "Ready to file!"}</span>
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

// Right-rail: E-Way Bill Summary Card
function EWayBillCard() {
  const { t } = useLanguage();
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect><path d="M7 15h0M2 9.5h20"></path></svg>
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-800">E-Way Bills</h3>
      </div>
      
      <div className="space-y-3">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500">Active E-Way Bills</span>
          <span className="font-semibold text-gray-900 bg-gray-100 px-2 py-0.5 rounded-full">0</span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500">Expiring Today</span>
          <span className="font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">0</span>
        </div>
        <p className="text-[10px] text-gray-400 mt-2 leading-tight">
          Required for movement of goods worth &gt; ₹50,000. Connect E-Way Bill portal to track validity.
        </p>
      </div>
    </div>
  );
}

import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const { t, lang, changeLanguage } = useLanguage();
  const [activeTab, setActiveTab] = useState("money-meter");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [traderId, setTraderId] = useState(null);
  const [traders, setTraders] = useState([]);
  const [traderDropdown, setTraderDropdown] = useState(false);
  const [activeTraderName, setActiveTraderName] = useState("Loading...");
  const [activeBusinessName, setActiveBusinessName] = useState("");
  const [activeTraderGstin, setActiveTraderGstin] = useState("");
  const [actionCount, setActionCount] = useState(0);

  const [fullPrefs, setFullPrefs] = useState(null);
  const dragItem = useRef(null);
  const dragOverItem = useRef(null);

  useEffect(() => {
    if (!traderId) return;
    authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.dashboard) setFullPrefs(d);
      }).catch(console.error);
  }, [traderId]);

  const defaultRightRail = ["supplier_risk", "filing_readiness", "eway_bills", "quick_links"];
  const rightRailOrder = fullPrefs?.dashboard || defaultRightRail;

  
  const handleMoneyMeterSortTop = async (newOrder) => {
    const newPrefs = { ...fullPrefs, money_meter_top: newOrder };
    setFullPrefs(newPrefs);
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, { method: "POST", body: JSON.stringify(newPrefs) });
    } catch(e) { console.error(e); }
  };

  const handleMoneyMeterSortBottom = async (newOrder) => {
    const newPrefs = { ...fullPrefs, money_meter_bottom: newOrder };
    setFullPrefs(newPrefs);
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, { method: "POST", body: JSON.stringify(newPrefs) });
    } catch(e) { console.error(e); }
  };

  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        { 
          popover: { title: 'Welcome to the CA Dashboard', description: 'Let us show you around your new workspace.', side: "bottom", align: 'start' },
          onHighlightStarted: () => { setActiveTab("money-meter"); }
        },
        { 
          element: '#money-meter-top', 
          popover: { title: 'ITC Metrics', description: 'These are your core ITC metrics. You can drag and drop these cards to reorder them based on what you want to see first!', side: "bottom", align: 'start' } 
        },
        { 
          element: '#money-meter-bottom', 
          popover: { title: 'Quick Stats', description: 'Track your processed invoices and open issues. These are also fully drag-and-drop enabled.', side: "bottom", align: 'start' } 
        },
        { 
          element: '#right-panel', 
          popover: { title: 'Right Panel Widgets', description: 'All the widgets on the right panel of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' } 
        },
        { 
          element: '#sidebar-nav-suppliers', 
          popover: { title: 'Supplier Trust', description: 'Navigate to the Supplier Trust tab to view a detailed breakdown of all supplier invoices and pinpoint exactly which ones are causing blocked ITC.', side: "right", align: 'start' },
          onHighlightStarted: () => { setActiveTab("suppliers"); }
        },
        { 
          element: '#sidebar-nav-actions', 
          popover: { title: 'Action Queue', description: 'This is your triage center. Any discrepancies, mismatching invoices, or blocked ITC that require your immediate attention will be queued here.', side: "right", align: 'start' },
          onHighlightStarted: () => { setActiveTab("actions"); }
        },
        { 
          element: '#sidebar-my-profile', 
          popover: { title: 'My Profile', description: 'Manage your personal CA details and configure automated WhatsApp reminders for missing GSTINs right from this panel.', side: "right", align: 'start' },
          onHighlightStarted: () => { router.push('/dashboard/profile'); }
        }
      ]
    });
    driverObj.drive();
  };

  const handleSort = async () => {
    let _rightRailOrder = [...rightRailOrder];
    const draggedItemContent = _rightRailOrder.splice(dragItem.current, 1)[0];
    _rightRailOrder.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    
    const newPrefs = { ...fullPrefs, dashboard: _rightRailOrder };
    if (!newPrefs.sidebar) newPrefs.sidebar = ["money-meter", "suppliers", "actions", "reports"]; // fallback
    
    setFullPrefs(newPrefs);
    
    // Save to backend
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, {
        method: "POST",
        body: JSON.stringify(newPrefs)
      });
    } catch(e) {
      console.error("Failed to save new layout order:", e);
    }
  };

  const renderRightRailWidget = (id, index) => {
    let widget = null;
    switch (id) {
      case "supplier_risk": widget = <SupplierRiskCard traderId={traderId} onSwitchTab={setActiveTab} />; break;
      case "filing_readiness": widget = <FilingReadinessCard traderId={traderId} summary={summary} onSwitchTab={setActiveTab} />; break;
      case "eway_bills": widget = <EWayBillCard />; break;
      case "quick_links": widget = <QuickLinksCard traderId={traderId} />; break;
      default: return null;
    }
    
    return (
      <div 
        key={id}
        draggable
        onDragStart={(e) => { dragItem.current = index; }}
        onDragEnter={(e) => { dragOverItem.current = index; e.preventDefault(); }}
        onDragOver={(e) => e.preventDefault()}
        onDragEnd={handleSort}
        className="cursor-grab active:cursor-grabbing hover:ring-2 hover:ring-gray-200 transition-all rounded-xl relative"
        title="Drag to reorder"
      >
        <div className="absolute top-2 right-2 opacity-0 hover:opacity-100 z-10 p-1 bg-white/80 rounded backdrop-blur-sm pointer-events-none transition-opacity">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
        </div>
        {widget}
      </div>
    );
  };

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
      const res = await authFetch(`${API_BASE}/api/v1/dashboard/traders`);
      const data = await res.json();
      const list = data.traders || [];
      setTraders(list);
      if (list.length > 0) {
        const matched = defaultId ? list.find((t) => t.id === defaultId) : null;
        const selected = matched || list[0];
        setTraderId(selected.id);
        setActiveTraderName(selected.name || selected.business_name || "Trader 1");
        setActiveBusinessName(selected.business_name || selected.name || "");
        setActiveTraderGstin(selected.gstin || "");
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
      const res = await authFetch(`${API_BASE}/api/v1/dashboard/summary/${tid}`);
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
      const actRes = await authFetch(`${API_BASE}/api/v1/dashboard/actions/${tid}`);
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
    setActiveBusinessName(trader.business_name || trader.name || "");
    setActiveTraderGstin(trader.gstin || "");
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
    "money-meter": t("nav_money_meter"),
    "suppliers":   t("nav_supplier_trust"),
    "actions":     t("nav_action_queue"),
    "reports":     t("nav_monthly_reports"),
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8f9fa]">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        actionCount={actionCount}
        traderId={traderId}
        apiBase={API_BASE}
        onTourClick={startTour}
      />

      <main className="flex-1 ml-64 flex flex-col overflow-hidden">
        {/* Header — h-[65px] matches sidebar logo bar */}
        <header className="flex-none h-[65px] px-6 border-b border-gray-200 bg-white flex items-center">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <h1 className="text-base font-bold text-gray-900">{tabLabels[activeTab]}</h1>
              {activeBusinessName && (
                <span className="text-xs text-gray-500 font-medium bg-gray-100 px-2 py-0.5 rounded-full truncate max-w-[180px]">
                  {activeBusinessName}
                </span>
              )}
              {activeTraderGstin && (
                <span
                  onClick={() => { navigator.clipboard.writeText(activeTraderGstin); }}
                  title="Click to copy GSTIN"
                  className="text-[10px] font-mono font-bold text-gray-400 cursor-pointer hover:text-gray-600 transition-colors select-none"
                >
                  {activeTraderGstin}
                </span>
              )}
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
                        {t("hdr_switch_trader")}
                      </p>
                    </div>
                    {traders.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-gray-400">{t("hdr_no_traders")}</div>
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
                <span className="text-sm font-semibold text-gray-800">{t("hdr_composition")}</span>
              </button>

              {/* GST Portal button — opens the GST portal mockup for IMS + GSTR-3B filing */}
              <a
                href={`/demo/index.html${traderId && traderId !== 'demo' ? `?traderId=${traderId}` : ''}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 bg-[#1a3a6c] text-white border border-[#1a3a6c] rounded-lg px-3 py-2 hover:bg-[#15306e] transition-colors shadow-sm text-sm font-semibold"
                title="Open GST Portal — IMS, GSTR-2B & GSTR-3B filing"
              >
                <Globe size={15} />
                GST Portal
              </a>
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
            className="flex-1 grid gap-4 p-4 overflow-hidden"
            style={{ gridTemplateColumns: "minmax(0, 1fr) 280px" }}
          >
            {/* Left (2/3) — Main content + Invoice Feed */}
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08, duration: 0.3 }}
              className="flex flex-col gap-4 min-h-0 overflow-hidden pr-1"
            >
              {activeTab === "money-meter" && (
                <MoneyMeter summary={summary} apiBase={API_BASE} isComposition={isComposition} onSwitchTab={setActiveTab} prefs={fullPrefs} onSortTop={handleMoneyMeterSortTop} onSortBottom={handleMoneyMeterSortBottom} />
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
              id="right-panel"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.12, duration: 0.3 }}
              className="flex flex-col gap-3 min-h-0 overflow-y-auto pr-1"
            >
              {rightRailOrder.map((id, idx) => renderRightRailWidget(id, idx))}
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
