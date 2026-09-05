"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  AlertCircle,
  FileText,
  MessageCircle,
  CalendarClock,
  TrendingUp,
  LogOut,
  User,
} from "lucide-react";

export default function Sidebar({ activeTab, onTabChange, actionCount = 0, portfolioStats = null }) {
  const router = useRouter();
  const [isWhatsappEnabled, setIsWhatsappEnabled] = useState(false);
  const [testAlertSent, setTestAlertSent] = useState(false);
  const [authName, setAuthName] = useState("N");

  useEffect(() => {
    const authUser = localStorage.getItem("munim_auth_trader");
    if (authUser) {
      const parsed = JSON.parse(authUser);
      const name = parsed.name || parsed.business_name || "N";
      setAuthName(name.charAt(0).toUpperCase());
    }
  }, []);

  const navItems = [
    { id: "money-meter", label: "Money Meter", icon: LayoutDashboard },
    { id: "suppliers", label: "Supplier Trust", icon: Users },
    { id: "actions", label: "Action Queue", icon: AlertCircle, badge: actionCount },
    { id: "reports", label: "Monthly Reports", icon: FileText },
  ];

  // Compute upcoming GST deadlines dynamically
  const today = new Date();
  const day = today.getDate();
  const monthName = today.toLocaleString("en-IN", { month: "long" });
  const year = today.getFullYear();

  const deadlines = [
    {
      label: "GSTR-1",
      day: 11,
      desc: "Outward supplies",
    },
    {
      label: "GSTR-3B",
      day: 20,
      desc: "Tax payment & filing",
    },
    {
      label: "GSTR-2B Auto-draft",
      day: 14,
      desc: "ITC reconciliation window",
    },
  ]
    .map((d) => {
      const daysLeft = d.day - day;
      const isOverdue = daysLeft < 0;
      const isToday = daysLeft === 0;
      const isUrgent = daysLeft > 0 && daysLeft <= 3;
      return { ...d, daysLeft, isOverdue, isToday, isUrgent };
    })
    .filter((d) => d.daysLeft >= -1) // show up to 1 day overdue
    .sort((a, b) => a.daysLeft - b.daysLeft)
    .slice(0, 3);

  const getDeadlineChip = (d) => {
    if (d.isOverdue)
      return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-600">OVERDUE</span>;
    if (d.isToday)
      return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-600 animate-pulse">TODAY</span>;
    if (d.isUrgent)
      return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">{d.daysLeft}d left</span>;
    return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">{d.daysLeft}d</span>;
  };

  // Portfolio snapshot — use passed props or defaults
  const stats = portfolioStats || {
    totalClients: "—",
    clientsWithIssues: "—",
    totalITCAtRisk: "—",
    avgScore: "—",
  };

  return (
    <aside className="w-64 fixed h-full bg-[#f8f9fa] border-r border-gray-200 z-10 flex flex-col overflow-y-auto">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-200">
        <span className="font-bold text-xl tracking-tight text-gray-900">Munim.ai</span>
      </div>

      {/* Main Nav */}
      <nav className="px-3 pt-4 pb-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-semibold ${
                isActive
                  ? "bg-[#10b981] text-white shadow-sm"
                  : "text-gray-600 hover:bg-white hover:text-gray-900"
              }`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge > 0 && (
                <span
                  className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isActive ? "bg-white text-[#10b981]" : "bg-red-500 text-white"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="mx-4 my-3 border-t border-gray-200" />

      {/* Upcoming Deadlines */}
      <div className="px-4 pb-3">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2 flex items-center gap-1.5">
          <CalendarClock size={11} />
          Upcoming Deadlines
        </p>
        <div className="space-y-2">
          {deadlines.length === 0 ? (
            <p className="text-xs text-gray-400">All deadlines passed for this month.</p>
          ) : (
            deadlines.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-gray-100"
              >
                <div>
                  <p className="text-xs font-bold text-gray-900">{d.label}</p>
                  <p className="text-[10px] text-gray-400">{d.day} {monthName}</p>
                </div>
                {getDeadlineChip(d)}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 my-1 border-t border-gray-200" />

      {/* Portfolio Snapshot */}
      <div className="px-4 py-3">
        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2 flex items-center gap-1.5">
          <TrendingUp size={11} />
          Portfolio Snapshot
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-white rounded-lg px-3 py-2 border border-gray-100">
            <p className="text-[10px] text-gray-400">Total Clients</p>
            <p className="text-base font-bold text-gray-900 mt-0.5">{stats.totalClients}</p>
          </div>
          <div className="bg-white rounded-lg px-3 py-2 border border-gray-100">
            <p className="text-[10px] text-gray-400">With Issues</p>
            <p className="text-base font-bold text-red-600 mt-0.5">{stats.clientsWithIssues}</p>
          </div>
          <div className="bg-white rounded-lg px-3 py-2 border border-gray-100">
            <p className="text-[10px] text-gray-400">ITC at Risk</p>
            <p className="text-base font-bold text-amber-600 mt-0.5 truncate">{stats.totalITCAtRisk}</p>
          </div>
          <div className="bg-white rounded-lg px-3 py-2 border border-gray-100">
            <p className="text-[10px] text-gray-400">Avg Score</p>
            <p className="text-base font-bold text-[#10b981] mt-0.5">{stats.avgScore}</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 my-1 border-t border-gray-200" />

      {/* WhatsApp Alerts */}
      <div className="px-4 py-3">
        <div className="bg-white rounded-lg border border-gray-100 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#25D366] text-white flex items-center justify-center">
                <MessageCircle size={13} />
              </div>
              <span className="text-xs font-bold text-gray-900">WhatsApp Alerts</span>
            </div>
            <button
              onClick={() => setIsWhatsappEnabled(!isWhatsappEnabled)}
              className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${
                isWhatsappEnabled ? "bg-[#25D366]" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  isWhatsappEnabled ? "translate-x-3.5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 leading-relaxed">
            {isWhatsappEnabled
              ? "You'll get deadline & mismatch alerts on WhatsApp."
              : "Turn on for instant compliance reminders."}
          </p>
          {isWhatsappEnabled && (
            <button
              onClick={() => {
                setTestAlertSent(true);
                setTimeout(() => setTestAlertSent(false), 3000);
              }}
              disabled={testAlertSent}
              className="w-full py-1.5 bg-white border border-[#25D366] text-[#25D366] rounded-lg text-[11px] font-bold hover:bg-green-50 transition-colors disabled:opacity-50"
            >
              {testAlertSent ? "Alert Sent ✅" : "Send Test Alert"}
            </button>
          )}
        </div>
      </div>

      {/* Sign Out — pinned to bottom */}
      <div className="mt-auto p-4 border-t border-gray-200">
        <button
          onClick={() => {
            localStorage.removeItem("munim_auth_trader");
            router.push("/");
          }}
          className="flex items-center gap-3 px-3 py-2 text-gray-500 hover:text-gray-900 hover:bg-white rounded-lg transition-colors w-full text-sm"
        >
          <div className="w-6 h-6 rounded-full bg-gray-900 text-white flex items-center justify-center font-bold text-[10px]">
            {authName}
          </div>
          <span className="font-medium">Sign Out</span>
          <LogOut size={14} className="ml-auto" />
        </button>
      </div>
    </aside>
  );
}
