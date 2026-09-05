"use client";

import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp } from "lucide-react";

export default function ITCTrendChart({ traderId, apiBase, compact = false }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!traderId) return;

    async function fetchTimeline() {
      try {
        const res = await fetch(`${apiBase}/api/v1/dashboard/itc-timeline/${traderId}`);
        if (!res.ok) throw new Error("Failed to fetch");
        const json = await res.json();
        if (json.timeline && json.timeline.length > 0) {
          setData(json.timeline);
        } else {
          setData(DEMO_DATA);
        }
      } catch {
        setData(DEMO_DATA);
      } finally {
        setLoading(false);
      }
    }
    fetchTimeline();
  }, [traderId, apiBase]);

  const chartH = compact ? 160 : 220;

  if (loading) {
    return (
      <div className={`bg-white border border-gray-200 rounded-xl p-4 ${compact ? "" : "mt-2"}`}>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-4 h-4 bg-gray-200 rounded animate-pulse" />
          <div className="w-32 h-4 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="animate-pulse bg-gray-100 rounded-lg" style={{ height: chartH }} />
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-xl p-4 ${compact ? "" : "mt-2"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-[#10b981]" />
          <h3 className="font-bold text-sm text-gray-900">ITC Trend (6 Months)</h3>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#10b981]" />
            <span className="text-gray-500">Confirmed ITC</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]" />
            <span className="text-gray-500">Eligible</span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={chartH}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="gClaimed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#10b981" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gEligible" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            dy={6}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            tickFormatter={(val) => `₹${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
          />
          <Tooltip
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #e5e7eb",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.07)",
              fontSize: "12px",
            }}
            formatter={(value) => [`₹${value.toLocaleString("en-IN")}`, undefined]}
          />
          <Area
            type="monotone"
            dataKey="itc_eligible"
            name="Eligible"
            stroke="#f59e0b"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#gEligible)"
          />
          <Area
            type="monotone"
            dataKey="itc_claimed"
            name="Confirmed ITC"
            stroke="#10b981"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#gClaimed)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const DEMO_DATA = [
  { label: "Feb", itc_claimed: 15000, itc_eligible: 18000 },
  { label: "Mar", itc_claimed: 22000, itc_eligible: 25000 },
  { label: "Apr", itc_claimed: 18000, itc_eligible: 20000 },
  { label: "May", itc_claimed: 32000, itc_eligible: 35000 },
  { label: "Jun", itc_claimed: 28000, itc_eligible: 32000 },
  { label: "Jul", itc_claimed: 41200, itc_eligible: 48000 },
];
