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
    <aside className="w-64 fixed h-full bg-[var(--bg-primary)] border-r border-[var(--border-subtle)] z-10 flex flex-col">
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-black text-white flex items-center justify-center font-bold text-xl">
            M
          </div>
          <span className="font-bold text-xl tracking-tight text-black">Munim.ai</span>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${
                isActive 
                  ? "bg-black text-white" 
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-black"
              }`}
            >
              <Icon size={20} className={isActive ? "text-white" : ""} />
              <span className="font-semibold text-sm">{item.label}</span>
              
              {item.id === "actions" && (
                <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded ${
                  isActive ? "bg-white text-black" : "bg-black text-white"
                }`}>
                  3
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--border-subtle)] space-y-1">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-black transition-all">
          <Settings size={20} />
          <span className="font-semibold text-sm">Settings</span>
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--red-primary)] transition-all">
          <LogOut size={20} />
          <span className="font-semibold text-sm">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
