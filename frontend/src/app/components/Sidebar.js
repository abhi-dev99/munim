"use client";

import { LayoutDashboard, Users, AlertCircle, FileText, Settings, LogOut } from "lucide-react";

export default function Sidebar({ activeTab, onTabChange, actionCount = 0 }) {
  const navItems = [
    { id: "money-meter", label: "Money Meter", icon: LayoutDashboard },
    { id: "suppliers", label: "Supplier Trust", icon: Users },
    { id: "actions", label: "Action Queue", icon: AlertCircle, badge: actionCount },
    { id: "reports", label: "Monthly Reports", icon: FileText },
  ];

  return (
    <aside className="w-64 fixed h-full bg-[var(--bg-primary)] border-r border-[var(--border-subtle)] z-10 flex flex-col">
      <div className="p-6">
        <div className="flex items-center gap-3">
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
              
              {item.badge > 0 && (
                <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded ${
                  isActive ? "bg-white text-black" : "bg-black text-white"
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="px-6 mb-6">
        <div className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-subtle)] space-y-3">
          <div className="w-8 h-8 rounded-full bg-black text-white flex items-center justify-center">
            <AlertCircle size={16} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-black">Need Help?</h4>
            <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
              Having trouble with ITC claims? Contact your CA or our support team.
            </p>
          </div>
          <button className="w-full py-2 bg-white border border-[var(--border-subtle)] rounded-lg text-xs font-bold text-black hover:bg-gray-50 transition-colors shadow-sm">
            Contact Support
          </button>
        </div>
      </div>

      <div className="p-4 border-t border-[var(--border-subtle)] space-y-1">
        <button className="flex items-center gap-3 px-3 py-2 text-[var(--text-secondary)] hover:text-black hover:bg-[var(--bg-secondary)] rounded-lg transition-colors w-full">
          <div className="w-6 h-6 rounded-full bg-black text-white flex items-center justify-center font-bold text-[10px]">
            N
          </div>
          <span className="font-medium text-sm">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
