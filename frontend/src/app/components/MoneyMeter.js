"use client";

import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { ArrowUpRight, ArrowDownRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp } from "lucide-react";

const chartData = [
  { name: "Jan", recovered: 12000, blocked: 2000 },
  { name: "Feb", recovered: 15000, blocked: 3500 },
  { name: "Mar", recovered: 11000, blocked: 5000 },
  { name: "Apr", recovered: 28000, blocked: 1200 },
  { name: "May", recovered: 35000, blocked: 8000 },
  { name: "Jun", recovered: 41200, blocked: 8600 },
];

export default function MoneyMeter({ summary }) {
  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;

  return (
    <div className="space-y-6">
      {/* Top row metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Main Recovered Card */}
        <div className="glass-card p-6 border-[var(--border-accent)] shadow-[var(--shadow-glow-blue)] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <TrendingUp size={100} />
          </div>
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="text-[var(--blue-primary)]" size={24} />
            <h3 className="font-semibold text-lg text-[var(--text-secondary)]">Confirmed ITC</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-white tracking-tight animate-count">
              ₹{(itc_buckets?.confirmed || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--green-primary)] font-medium">
            <ArrowUpRight size={16} />
            <span>+14.5% from last month</span>
          </div>
        </div>

        {/* At Risk Card */}
        <div className="glass-card p-6 border border-[rgba(255,145,0,0.3)]">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="text-[var(--orange-primary)]" size={24} />
            <h3 className="font-semibold text-lg text-[var(--text-secondary)]">At Risk / Blocked</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-white tracking-tight animate-count">
              ₹{((itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0)).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--orange-primary)] font-medium">
            <ArrowUpRight size={16} />
            <span>Requires action by 18th</span>
          </div>
        </div>

        {/* Potential Recovery Card */}
        <div className="glass-card p-6 bg-[linear-gradient(145deg,rgba(0,230,118,0.05)_0%,rgba(0,230,118,0)_100%)]">
          <div className="flex items-center gap-2 mb-4">
            <IndianRupee className="text-[var(--green-primary)]" size={24} />
            <h3 className="font-semibold text-lg text-[var(--text-secondary)]">Potential Recovery</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-[var(--green-primary)] tracking-tight animate-count">
              ₹{(total_recovery_possible || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-muted)] font-medium">
            <span>Fix 3 supplier issues to unlock</span>
          </div>
        </div>

      </div>

      {/* Chart Row */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-xl font-bold">ITC Recovery Trends</h3>
            <p className="text-[var(--text-secondary)] text-sm">Monthly comparison of recovered vs blocked ITC</p>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[var(--blue-primary)] shadow-[var(--shadow-glow-blue)]"></div>
              <span className="text-sm text-[var(--text-secondary)]">Recovered</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[var(--orange-primary)] shadow-[rgba(255,145,0,0.2)]"></div>
              <span className="text-sm text-[var(--text-secondary)]">Blocked</span>
            </div>
          </div>
        </div>

        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--blue-primary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--blue-primary)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorBlocked" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--orange-primary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--orange-primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--text-muted)" axisLine={false} tickLine={false} dy={10} />
              <YAxis stroke="var(--text-muted)" axisLine={false} tickLine={false} tickFormatter={(val) => `₹${val/1000}k`} dx={-10} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Area type="monotone" dataKey="recovered" stroke="var(--blue-primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorRecovered)" />
              <Area type="monotone" dataKey="blocked" stroke="var(--orange-primary)" strokeWidth={2} fillOpacity={1} fill="url(#colorBlocked)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
