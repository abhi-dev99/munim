"use client";

import { LayoutDashboard, Users, AlertCircle, FileText, Settings, LogOut } from "lucide-react";

export default function Sidebar({ activeTab, onTabChange }) {
  const navItems = [
    { id: "money-meter", label: "Money Meter", icon: LayoutDashboard },
    { id: "suppliers", label: "Supplier Health", icon: Users },
    { id: "actions", label: "Action Queue", icon: AlertCircle },
    { id: "reports", label: "Monthly Reports", icon: FileText },
  ];

  return (
    <aside className="w-64 fixed h-full glass-card rounded-none border-t-0 border-b-0 border-l-0 z-10 flex flex-col">
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-subtle)] flex items-center justify-center font-bold text-xl gradient-text">
            M
          </div>
          <span className="font-bold text-xl tracking-tight">Munim.ai</span>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive 
                  ? "bg-[var(--bg-secondary)] border border-[var(--border-accent)] text-[var(--blue-primary)] shadow-[var(--shadow-glow-blue)]" 
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Icon size={20} className={isActive ? "text-[var(--blue-primary)]" : ""} />
              <span className="font-medium text-sm">{item.label}</span>
              
              {item.id === "actions" && (
                <span className="ml-auto bg-[var(--red-primary)] text-white text-[10px] font-bold px-2 py-0.5 rounded-full animate-pulse">
                  3
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--border-subtle)] space-y-2">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)] transition-all">
          <Settings size={20} />
          <span className="font-medium text-sm">Settings</span>
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--red-primary)] transition-all">
          <LogOut size={20} />
          <span className="font-medium text-sm">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
