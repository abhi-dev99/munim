"use client";

import { useState, useEffect } from "react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { ArrowUpRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function MoneyMeter({ summary, apiBase }) {
  const [chartData, setChartData] = useState([]);
  const [chartLoading, setChartLoading] = useState(true);

  const base = apiBase || API_BASE;
  const traderId = summary?.trader_id;

  useEffect(() => {
    if (!traderId || traderId === "demo") {
      // Demo fallback data
      setChartData([
        { name: "Jan", recovered: 12000, blocked: 2000 },
        { name: "Feb", recovered: 15000, blocked: 3500 },
        { name: "Mar", recovered: 11000, blocked: 5000 },
        { name: "Apr", recovered: 28000, blocked: 1200 },
        { name: "May", recovered: 35000, blocked: 8000 },
        { name: "Jun", recovered: 41200, blocked: 8600 },
      ]);
      setChartLoading(false);
      return;
    }

    async function fetchTimeline() {
      try {
        const res = await fetch(`${base}/api/v1/dashboard/itc-timeline/${traderId}`);
        if (!res.ok) throw new Error("Timeline fetch failed");
        const data = await res.json();
        const formatted = (data.timeline || []).map((t) => ({
          name: t.label,
          recovered: t.itc_claimed,
          blocked: t.gap,
        }));
        setChartData(formatted);
      } catch (err) {
        console.warn("Timeline fetch failed, using demo data:", err);
        setChartData([
          { name: "Jan", recovered: 0, blocked: 0 },
          { name: "Feb", recovered: 0, blocked: 0 },
          { name: "Mar", recovered: 0, blocked: 0 },
          { name: "Apr", recovered: 0, blocked: 0 },
          { name: "May", recovered: 0, blocked: 0 },
          { name: "Jun", recovered: 0, blocked: 0 },
        ]);
      } finally {
        setChartLoading(false);
      }
    }

    fetchTimeline();
  }, [traderId, base]);

  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;

  return (
    <div className="space-y-6">
      {/* Top row metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Main Recovered Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-[0.03]">
            <TrendingUp size={100} color="#000" />
          </div>
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="text-black" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Confirmed ITC</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{(itc_buckets?.confirmed || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-black font-medium">
            <ArrowUpRight size={16} />
            <span>This month (live)</span>
          </div>
        </div>

        {/* At Risk Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="text-[var(--red-primary)]" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">At Risk / Blocked</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{((itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0)).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--red-primary)] font-medium">
            <ArrowUpRight size={16} />
            <span>Requires action by 18th</span>
          </div>
        </div>

        {/* Potential Recovery Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 mb-4">
            <IndianRupee className="text-[var(--green-primary)]" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Potential Recovery</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{(total_recovery_possible || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
            <span>Fix supplier issues to unlock</span>
          </div>
        </div>

      </div>

      {/* Chart Row */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-xl font-bold text-black">ITC Recovery Trends</h3>
            <p className="text-[var(--text-secondary)] text-sm">6-month comparison — recovered vs blocked ITC</p>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-black"></div>
              <span className="text-sm font-medium text-black">Recovered</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-[var(--text-muted)]"></div>
              <span className="text-sm font-medium text-black">Blocked</span>
            </div>
          </div>
        </div>

        <div className="h-[300px] w-full">
          {chartLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-black"></div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" axisLine={false} tickLine={false} dy={10} fontSize={12} fontWeight={600} />
                <YAxis stroke="var(--text-muted)" axisLine={false} tickLine={false} tickFormatter={(val) => `₹${val/1000}k`} dx={-10} fontSize={12} fontWeight={600} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: '#000', fontWeight: '600' }}
                  itemStyle={{ color: '#000' }}
                  formatter={(val) => [`₹${Number(val).toLocaleString('en-IN')}`, undefined]}
                />
                <Area type="monotone" dataKey="recovered" stroke="#000000" strokeWidth={3} fillOpacity={0.05} fill="#000000" />
                <Area type="monotone" dataKey="blocked" stroke="var(--text-muted)" strokeWidth={2} fillOpacity={0.05} fill="var(--text-muted)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;

  return (
    <div className="space-y-6">
      {/* Top row metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Main Recovered Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-[0.03]">
            <TrendingUp size={100} color="#000" />
          </div>
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="text-black" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Confirmed ITC</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{(itc_buckets?.confirmed || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-black font-medium">
            <ArrowUpRight size={16} />
            <span>+14.5% from last month</span>
          </div>
        </div>

        {/* At Risk Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="text-[var(--red-primary)]" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">At Risk / Blocked</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{((itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0)).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--red-primary)] font-medium">
            <ArrowUpRight size={16} />
            <span>Requires action by 18th</span>
          </div>
        </div>

        {/* Potential Recovery Card */}
        <div className="glass-card p-6 border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 mb-4">
            <IndianRupee className="text-[var(--green-primary)]" size={24} />
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Potential Recovery</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-black tracking-tight animate-count">
              ₹{(total_recovery_possible || 0).toLocaleString('en-IN')}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
            <span>Fix 3 supplier issues to unlock</span>
          </div>
        </div>

      </div>

      {/* Chart Row */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-xl font-bold text-black">ITC Recovery Trends</h3>
            <p className="text-[var(--text-secondary)] text-sm">Monthly comparison of recovered vs blocked ITC</p>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-black"></div>
              <span className="text-sm font-medium text-black">Recovered</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-[var(--text-muted)]"></div>
              <span className="text-sm font-medium text-black">Blocked</span>
            </div>
          </div>
        </div>

        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
              <XAxis dataKey="name" stroke="var(--text-muted)" axisLine={false} tickLine={false} dy={10} fontSize={12} fontWeight={600} />
              <YAxis stroke="var(--text-muted)" axisLine={false} tickLine={false} tickFormatter={(val) => `₹${val/1000}k`} dx={-10} fontSize={12} fontWeight={600} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#ffffff', border: '1px solid var(--border-subtle)', borderRadius: '4px', color: '#000', fontWeight: '600' }}
                itemStyle={{ color: '#000' }}
              />
              <Area type="monotone" dataKey="recovered" stroke="#000000" strokeWidth={3} fillOpacity={0.05} fill="#000000" />
              <Area type="monotone" dataKey="blocked" stroke="var(--text-muted)" strokeWidth={2} fillOpacity={0.05} fill="var(--text-muted)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
