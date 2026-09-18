"use client";

import { useState, useEffect } from "react";
import { ArrowUpRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp, FileText, Users, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function MoneyMeter({ summary, apiBase, isComposition = false }) {
  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;

  // Mock calculation for composition dealer based on scanned invoices
  // In reality, this would be total outward supplies. For demo, we just use a metric based on processed.
  const mockTotalSales = (summary.invoices_processed || 0) * 12500;
  const mockTaxPayable = mockTotalSales * 0.01;

  return (
    <div className="space-y-6">
      {/* Top row metrics */}
      <motion.div 
        initial="hidden"
        animate="show"
        variants={{
          hidden: { opacity: 0 },
          show: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
          }
        }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        
        {isComposition ? (
          <>
            {/* Total Sales Card */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:scale-110 group-hover:opacity-[0.08] transition-all duration-500">
                <TrendingUp size={100} color="var(--green-primary)" />
              </div>
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="text-[var(--green-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Total Sales Scanned</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10">
                <span className="text-4xl font-bold tracking-tight animate-count text-gradient">
                  ₹{mockTotalSales.toLocaleString('en-IN')}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--green-primary)] font-medium">
                <ArrowUpRight size={16} />
                <span>Quarter-to-date</span>
              </div>
            </motion.div>

            {/* Estimated Tax Payable */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="flex items-center gap-2 mb-4">
                <IndianRupee className="text-[var(--orange-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Est. Tax Payable (1%)</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10">
                <span className="text-4xl font-bold tracking-tight animate-count text-gradient">
                  ₹{mockTaxPayable.toLocaleString('en-IN')}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
                <span>Calculated on inward/outward proxy</span>
              </div>
            </motion.div>

            {/* Compliance Status */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="text-[var(--blue-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">CMP-08 Status</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10 mt-2">
                <span className={`text-3xl font-bold tracking-tight ${new Date().getDate() > 18 ? 'text-red-600' : 'text-black'}`}>
                  {new Date().getDate() > 18 ? 'OVERDUE' : 'DUE SOON'}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
                <span className={new Date().getDate() > 18 ? 'text-red-500 font-bold' : ''}>Due by 18th of next month</span>
              </div>
            </motion.div>
          </>
        ) : (
          <>
            {/* Main Recovered Card */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:scale-110 group-hover:opacity-[0.08] transition-all duration-500">
                <TrendingUp size={100} color="var(--green-primary)" />
              </div>
              <div className="absolute -top-24 -left-24 w-48 h-48 bg-[var(--green-primary)] rounded-none blur-[80px] opacity-10"></div>
              
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="text-[var(--green-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Confirmed ITC</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10">
                <span className="text-4xl font-bold tracking-tight animate-count text-gradient">
                  ₹{(itc_buckets?.confirmed || 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--green-primary)] font-medium">
                <ArrowUpRight size={16} />
                <span>This month (live)</span>
              </div>
            </motion.div>

            {/* At Risk Card */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-[var(--red-primary)] rounded-none blur-[80px] opacity-10 group-hover:opacity-20 transition-opacity"></div>
              <div className="flex items-center gap-2 mb-4">
                <ShieldAlert className="text-[var(--red-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">At Risk / Blocked</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10">
                <span className="text-4xl font-bold tracking-tight animate-count text-gradient">
                  ₹{((itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0)).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--red-primary)] font-medium">
                <ArrowUpRight size={16} />
                <span>Requires action by 18th</span>
              </div>
            </motion.div>

            {/* Potential Recovery Card */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-6 border-[var(--border-subtle)] relative overflow-hidden group">
              <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-[var(--blue-primary)] rounded-none blur-[80px] opacity-10 group-hover:opacity-20 transition-opacity"></div>
              <div className="flex items-center gap-2 mb-4">
                <IndianRupee className="text-[var(--blue-primary)]" size={24} />
                <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--text-secondary)]">Potential Recovery</h3>
              </div>
              <div className="flex items-baseline gap-2 relative z-10">
                <span className="text-4xl font-bold tracking-tight animate-count text-gradient-primary">
                  ₹{(total_recovery_possible || 0).toLocaleString('en-IN')}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] font-medium">
                <span>Fix supplier issues to unlock</span>
              </div>
            </motion.div>
          </>
        )}

      </motion.div>

      {/* Operational Metrics Row */}
      <motion.div 
        initial="hidden"
        animate="show"
        variants={{
          hidden: { opacity: 0 },
          show: {
            opacity: 1,
            transition: { staggerChildren: 0.1, delayChildren: 0.3 }
          }
        }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        {/* Invoices Processed */}
        <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-5 flex flex-col justify-between border-[var(--border-subtle)] h-full">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="text-[var(--text-muted)]" size={18} />
            <h4 className="text-[11px] font-bold uppercase tracking-widest text-[var(--text-secondary)]">Invoices Scanned</h4>
          </div>
          <span className="text-4xl font-black text-black tracking-tight">{summary.invoices_processed || 0}</span>
        </motion.div>

        {/* Suppliers Monitored */}
        <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-5 flex flex-col justify-between border-[var(--border-subtle)] h-full">
          <div className="flex items-center gap-2 mb-3">
            <Users className="text-[var(--text-muted)]" size={18} />
            <h4 className="text-[11px] font-bold uppercase tracking-widest text-[var(--text-secondary)]">Suppliers Tracked</h4>
          </div>
          <span className="text-4xl font-black text-black tracking-tight">{summary.suppliers_monitored || 0}</span>
        </motion.div>

        {/* Action Items */}
        <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="glass-card p-5 flex flex-col justify-between border-[var(--border-subtle)] h-full">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className={(summary.issues_open || 0) > 0 ? "text-[var(--red-primary)]" : "text-[var(--green-primary)]"} size={18} />
            <h4 className="text-[11px] font-bold uppercase tracking-widest text-[var(--text-secondary)]">Open Issues</h4>
          </div>
          <span className={`text-4xl font-black tracking-tight ${(summary.issues_open || 0) > 0 ? "text-[var(--red-primary)]" : "text-[var(--green-primary)]"}`}>
            {summary.issues_open || 0}
          </span>
        </motion.div>
      </motion.div>
    </div>
  );
}
