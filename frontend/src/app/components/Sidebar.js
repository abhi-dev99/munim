"use client";
import { authFetch } from "@/src/app/utils/api";


import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  AlertCircle,
  FileText,
  MessageCircle,
  CalendarClock,
  TrendingUp,
  LogOut,
  UserCircle,
} from "lucide-react";
import { useLanguage } from "../context/LanguageContext";
import { BarChart, Bar, ResponsiveContainer, Tooltip, Cell } from "recharts";

// Mini sparkline bar chart (no recharts dependency in sidebar)
function MiniSparkline({ data = [] }) {
  if (!data.length) return <div className="h-12 flex items-end gap-0.5 px-1">{[...Array(6)].map((_, i) => <div key={i} className="flex-1 bg-gray-200 rounded-sm animate-pulse" style={{ height: `${30 + Math.random() * 20}%` }} />)}</div>;
  
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-gray-200 rounded shadow-sm px-2 py-1 text-xs">
          <p className="font-semibold text-gray-800">{payload[0].payload.label}</p>
          <p className="text-emerald-600 font-bold">₹{payload[0].value.toLocaleString("en-IN")}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-14 px-1 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.slice(-6)}>
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
          <Bar dataKey="itc_claimed" radius={[2, 2, 2, 2]}>
            {data.slice(-6).map((entry, index) => (
              <Cell key={`cell-${index}`} fill="#10b981" fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Sidebar({ activeTab, onTabChange, actionCount = 0, traderId, apiBase }) {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useLanguage();
  const [isWhatsappEnabled, setIsWhatsappEnabled] = useState(false);
  const [testAlertSent, setTestAlertSent] = useState(false);
  const [testAlertLoading, setTestAlertLoading] = useState(false);
  const [testAlertError, setTestAlertError] = useState(null);

  const [prefs, setPrefs] = useState(null);

  useEffect(() => {
    if (!traderId || !apiBase) return;
    authFetch(`${apiBase}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.sidebar) setPrefs(d.sidebar);
      }).catch(console.error);
  }, [traderId, apiBase]);

  const navItems = [
    { id: "money-meter", label: t("nav_money_meter"),     icon: LayoutDashboard },
    { id: "suppliers",   label: t("nav_supplier_trust"),  icon: Users            },
    { id: "actions",     label: t("nav_action_queue"),    icon: AlertCircle, badge: actionCount },
    { id: "reports",     label: t("nav_monthly_reports"), icon: FileText         },
  ];

  // Default nav items are defined as navItems above. We filter and sort based on prefs.
  const visibleNavItems = prefs 
    ? prefs.map(id => navItems.find(i => i.id === id)).filter(Boolean)
    : navItems;

  const [authName, setAuthName] = useState("N");
  const [itcData, setItcData] = useState([]);

  useEffect(() => {
    const authUser = localStorage.getItem("munim_auth_trader");
    if (authUser) {
      const parsed = JSON.parse(authUser);
      const name = parsed.name || parsed.business_name || "N";
      setAuthName(name.charAt(0).toUpperCase());
    }
  }, []);

  // Fetch ITC trend for mini chart
  useEffect(() => {
    if (!traderId || !apiBase) return;
    authFetch(`${apiBase}/api/v1/dashboard/itc-timeline/${traderId}`)
      .then(r => r.json())
      .then(d => setItcData(d.timeline || []))
      .catch(() => setItcData([]));
  }, [traderId, apiBase]);


  // Upcoming GST deadlines
  const today = new Date();
  const day = today.getDate();
  const monthName = today.toLocaleString("en-IN", { month: "long" });

  const deadlines = [
    { label: "GSTR-1",           day: 11, desc: "Outward supplies"       },
    { label: "GSTR-2B Auto",     day: 14, desc: "ITC reconciliation"     },
    { label: "GSTR-3B",          day: 20, desc: "Tax payment & filing"   },
  ]
    .map(d => ({ ...d, daysLeft: d.day - day }))
    .filter(d => d.daysLeft >= -1)
    .sort((a, b) => a.daysLeft - b.daysLeft)
    .slice(0, 3);

  const getChip = (d) => {
    if (d.daysLeft < 0)  return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-600">OVERDUE</span>;
    if (d.daysLeft === 0) return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-600 animate-pulse">TODAY</span>;
    if (d.daysLeft <= 3)  return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">{d.daysLeft}d left</span>;
    return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">{d.daysLeft}d</span>;
  };

  const isDeadlineUrgent = deadlines.some(d => d.daysLeft <= 3);

  return (
    <aside className="w-64 fixed h-full bg-white border-r border-gray-200 z-10 flex flex-col overflow-y-auto">
      {/* Logo — same height as main header */}
      <div className="px-6 h-[65px] flex items-center border-b border-gray-200 flex-none">
        <span className="font-bold text-xl tracking-tight text-gray-900">Munim.ai</span>
      </div>

      {/* Main Nav */}
      <nav className="px-3 pt-4 pb-2 space-y-1 flex-none">
        {visibleNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-semibold ${
                isActive
                  ? "bg-[#10b981] text-white shadow-sm"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge > 0 && (
                <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${isActive ? "bg-white text-[#10b981]" : "bg-red-500 text-white"}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="mx-4 my-3 border-t border-gray-100 flex-none" />

      {/* Upcoming Deadlines */}
      <div className="px-4 pb-3 flex-none">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2 flex items-center gap-1.5">
          <CalendarClock size={11} />
          {t("sb_upcoming_deadlines")}
          {/* Pulsing indicator if any deadline is close */}
          {isDeadlineUrgent && (
            <span className="relative ml-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
            </span>
          )}
        </p>
        <div className="space-y-2">
          {deadlines.length === 0 ? (
            <p className="text-xs text-gray-400 py-1">No upcoming deadlines this month.</p>
          ) : deadlines.map((d, i) => (
            <div key={i} className={`flex items-center justify-between rounded-lg px-3 py-2 border ${d.daysLeft <= 3 ? "bg-red-50 border-red-100" : "bg-gray-50 border-gray-100"}`}>
              <div>
                <p className={`text-xs font-bold ${d.daysLeft <= 3 ? "text-red-800" : "text-gray-900"}`}>{d.label}</p>
                <p className={`text-[10px] ${d.daysLeft <= 3 ? "text-red-500" : "text-gray-400"}`}>{d.day} {monthName}</p>
              </div>
              {getChip(d)}
            </div>
          ))}
        </div>
      </div>

      <div className="mx-4 my-1 border-t border-gray-100 flex-none" />

      {/* ITC Mini Trend */}
      <div className="px-4 py-3 flex-none">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2 flex items-center gap-1.5">
          <TrendingUp size={11} />
          {t("sb_itc_trend")}
        </p>
        <div className="bg-gray-50 rounded-lg border border-gray-100 py-2">
          <MiniSparkline data={itcData} />
          <div className="flex justify-between px-2 mt-1">
            {(itcData.length ? itcData.slice(-6) : [...Array(6)].map((_, i) => ({ label: ["F","M","A","M","J","J"][i] }))).map((d, i) => (
              <span key={i} className="text-[9px] text-gray-400 font-medium">{d.label}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="mx-4 my-1 border-t border-gray-100 flex-none" />

      {/* WhatsApp Alerts */}
      <div className="px-4 py-3 flex-none">
        <div className="bg-gray-50 rounded-lg border border-gray-100 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#25D366] text-white flex items-center justify-center">
                <MessageCircle size={13} />
              </div>
              <span className="text-xs font-bold text-gray-900">{t("nav_whatsapp_alerts")}</span>
            </div>
            <button
              onClick={() => setIsWhatsappEnabled(!isWhatsappEnabled)}
              className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${isWhatsappEnabled ? "bg-[#25D366]" : "bg-gray-300"}`}
            >
              <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${isWhatsappEnabled ? "translate-x-3.5" : "translate-x-0.5"}`} />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 leading-relaxed">
            {isWhatsappEnabled ? t("sb_wa_active") : t("sb_wa_turn_on")}
          </p>
          {isWhatsappEnabled && (
            <div className="space-y-1.5">
              <button
                onClick={async () => {
                  if (!traderId) { setTestAlertError("No trader loaded"); return; }
                  setTestAlertLoading(true);
                  setTestAlertError(null);
                  try {
                    const res = await authFetch(`${apiBase}/api/v1/communicate/test-alert/${traderId}?lang=${lang}`, { method: "POST" });
                    if (res.ok) {
                      setTestAlertSent(true);
                      setTimeout(() => setTestAlertSent(false), 4000);
                    } else {
                      const d = await res.json().catch(() => ({}));
                      setTestAlertError(d.detail || "Failed");
                    }
                  } catch {
                    setTestAlertError("Network error");
                  } finally {
                    setTestAlertLoading(false);
                  }
                }}
                disabled={testAlertSent || testAlertLoading}
                className="w-full py-1.5 bg-white border border-[#25D366] text-[#25D366] rounded-lg text-[11px] font-bold hover:bg-green-50 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                {testAlertLoading ? (
                  <><div className="animate-spin rounded-full h-3 w-3 border-b-2 border-[#25D366]" />{t("nav_sending")}</>
                ) : testAlertSent ? "Sent ✅" : t("nav_send_test_alert")}
              </button>
              {testAlertError && <p className="text-[10px] text-red-500 text-center">{testAlertError}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* My Profile */}
      <div className="px-4 pb-2 flex-none">
        <button
          id="sidebar-my-profile"
            onClick={() => router.push("/dashboard/profile")}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full text-sm font-semibold ${pathname === "/dashboard/profile" ? "bg-emerald-50 text-emerald-600 font-bold" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"}`}
        >
          <div className="w-7 h-7 rounded-full bg-[#10b981] text-white flex items-center justify-center font-bold text-[11px]">
            {authName}
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-gray-900">{t("nav_my_profile")}</p>
            <p className="text-[10px] text-gray-400">{t("pro_view_edit")}</p>
          </div>
          <UserCircle size={15} className="ml-auto text-gray-400" />
        </button>
      </div>

      {/* Sign Out */}
      <div className="px-4 pb-4 flex-none border-t border-gray-100 pt-2">
        <button
          onClick={() => { localStorage.removeItem("munim_auth_trader"); router.push("/"); }}
          className="flex items-center gap-3 px-3 py-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full text-sm"
        >
          <LogOut size={15} />
          <span className="font-medium">{t("nav_sign_out")}</span>
        </button>
      </div>
    </aside>
  );
}
