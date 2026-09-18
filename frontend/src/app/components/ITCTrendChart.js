"use client";

import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function ITCTrendChart({ traderId, apiBase }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!traderId) return;

    async function fetchTimeline() {
      try {
        const res = await fetch(`${apiBase}/api/v1/dashboard/itc-timeline/${traderId}`);
        if (!res.ok) throw new Error("Failed to fetch");
        const json = await res.json();
        if (json.timeline) {
          setData(json.timeline);
        }
      } catch (err) {
        console.warn("Using demo timeline data", err);
        // Fallback empty/demo data
        setData([
          { label: "Feb", itc_claimed: 15000, itc_eligible: 18000, gap: 3000 },
          { label: "Mar", itc_claimed: 22000, itc_eligible: 25000, gap: 3000 },
          { label: "Apr", itc_claimed: 18000, itc_eligible: 20000, gap: 2000 },
          { label: "May", itc_claimed: 32000, itc_eligible: 35000, gap: 3000 },
          { label: "Jun", itc_claimed: 28000, itc_eligible: 32000, gap: 4000 },
          { label: "Jul", itc_claimed: 41200, itc_eligible: 48000, gap: 6800 },
        ]);
      } finally {
        setLoading(false);
      }
    }
    fetchTimeline();
  }, [traderId, apiBase]);

  if (loading) {
    return (
      <div className="h-64 glass-card p-6 flex items-center justify-center border-[var(--border-subtle)] mt-6">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gray-200"></div>
          <div className="w-32 h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden mt-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <TrendingUp className="text-[var(--blue-primary)]" size={24} />
          <h3 className="font-bold text-lg text-black">ITC Trend (6 Months)</h3>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[var(--green-primary)]"></div>
            <span className="text-[var(--text-secondary)]">Confirmed ITC</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[var(--orange-primary)]"></div>
            <span className="text-[var(--text-secondary)]">Eligible</span>
          </div>
        </div>
      </div>
      
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorClaimed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--green-primary)" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="var(--green-primary)" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorEligible" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--orange-primary)" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="var(--orange-primary)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} dy={10} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} tickFormatter={(val) => `₹${val/1000}k`} />
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
              formatter={(value) => [`₹${value.toLocaleString('en-IN')}`, undefined]}
            />
            <Area type="monotone" dataKey="itc_eligible" name="Eligible" stroke="var(--orange-primary)" fillOpacity={1} fill="url(#colorEligible)" strokeWidth={2} />
            <Area type="monotone" dataKey="itc_claimed" name="Confirmed ITC" stroke="var(--green-primary)" fillOpacity={1} fill="url(#colorClaimed)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
