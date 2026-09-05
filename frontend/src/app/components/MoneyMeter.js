"use client";

import { ArrowUpRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp, FileText, Users, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function MoneyMeter({ summary, apiBase, isComposition = false, onSwitchTab }) {
  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;
  const mockTotalSales  = (summary.invoices_processed || 0) * 12500;
  const mockTaxPayable  = mockTotalSales * 0.01;
  const confirmed       = itc_buckets?.confirmed || 0;
  const atRisk          = (itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0);
  const totalITC        = confirmed + atRisk;

  const v = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

  return (
    <div className="space-y-3">
      {/* ── Top 3 ITC cards ──────────────────────────────────────────── */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }}
        className="grid grid-cols-3 gap-3"
      >
        {isComposition ? (
          <>
            <motion.div variants={v} className="bg-white border border-emerald-200 rounded-xl p-4 border-l-4 border-l-emerald-500">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp size={13} className="text-emerald-500" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Total Sales</span>
              </div>
              <p className="text-2xl font-black text-gray-900">₹{mockTotalSales.toLocaleString("en-IN")}</p>
              <p className="text-xs text-emerald-600 font-medium mt-2 flex items-center gap-1"><ArrowUpRight size={11} />Quarter-to-date</p>
            </motion.div>
            <motion.div variants={v} className="bg-white border border-amber-200 rounded-xl p-4 border-l-4 border-l-amber-400">
              <div className="flex items-center gap-1.5 mb-2">
                <IndianRupee size={13} className="text-amber-500" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Est. Tax (1%)</span>
              </div>
              <p className="text-2xl font-black text-gray-900">₹{mockTaxPayable.toLocaleString("en-IN")}</p>
              <p className="text-xs text-gray-400 font-medium mt-2">On inward/outward proxy</p>
            </motion.div>
            <motion.div variants={v} className="bg-white border border-blue-200 rounded-xl p-4 border-l-4 border-l-blue-400">
              <div className="flex items-center gap-1.5 mb-2">
                <FileText size={13} className="text-blue-500" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">CMP-08 Status</span>
              </div>
              <p className={`text-2xl font-black ${new Date().getDate() > 18 ? "text-red-600" : "text-gray-900"}`}>
                {new Date().getDate() > 18 ? "OVERDUE" : "DUE SOON"}
              </p>
              <p className={`text-xs font-medium mt-2 ${new Date().getDate() > 18 ? "text-red-500" : "text-gray-400"}`}>Due by 18th</p>
            </motion.div>
          </>
        ) : (
          <>
            {/* Confirmed ITC — prominent green */}
            <motion.div variants={v} className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 border-l-4 border-l-emerald-500 relative overflow-hidden">
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle2 size={13} className="text-emerald-600" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-700">Confirmed ITC</span>
              </div>
              <p className="text-2xl font-black text-emerald-900">₹{confirmed.toLocaleString("en-IN")}</p>
              <p className="text-xs text-emerald-700 font-medium mt-2 flex items-center gap-1"><ArrowUpRight size={11} />This month · live</p>
              {totalITC > 0 && (
                <div className="mt-3 bg-emerald-200 rounded-full h-1.5 overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.round((confirmed / totalITC) * 100)}%` }} />
                </div>
              )}
            </motion.div>

            {/* At Risk / Blocked — red warning */}
            <motion.div variants={v} className="bg-red-50 border border-red-200 rounded-xl p-4 border-l-4 border-l-red-500 relative overflow-hidden">
              <div className="flex items-center gap-1.5 mb-2">
                <ShieldAlert size={13} className="text-red-600" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-red-700">At Risk / Blocked</span>
              </div>
              <p className="text-2xl font-black text-red-900">₹{atRisk.toLocaleString("en-IN")}</p>
              <button
                onClick={() => onSwitchTab?.("actions")}
                className="text-xs text-red-700 font-semibold mt-2 flex items-center gap-1 hover:underline"
              >
                <ArrowUpRight size={11} />Needs action by 18th →
              </button>
            </motion.div>

            {/* Potential Recovery — blue opportunity */}
            <motion.div variants={v} className="bg-blue-50 border border-blue-200 rounded-xl p-4 border-l-4 border-l-blue-500 relative overflow-hidden">
              <div className="flex items-center gap-1.5 mb-2">
                <IndianRupee size={13} className="text-blue-600" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-blue-700">Potential Recovery</span>
              </div>
              <p className="text-2xl font-black text-blue-900">₹{(total_recovery_possible || 0).toLocaleString("en-IN")}</p>
              <p className="text-xs text-blue-600 font-medium mt-2">Fix supplier issues to unlock</p>
            </motion.div>
          </>
        )}
      </motion.div>

      {/* ── Stats ribbon — additive info only ────────────────────────── */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07, delayChildren: 0.12 } } }}
        className="bg-white border border-gray-200 rounded-xl flex divide-x divide-gray-100 overflow-hidden"
      >
        {/* Invoices */}
        <motion.div variants={v} className="flex items-center gap-3 px-5 py-3 flex-1">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
            <FileText size={14} className="text-gray-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Invoices Scanned</p>
            <p className="text-xl font-black text-gray-900">{summary.invoices_processed || 0}</p>
          </div>
        </motion.div>

        {/* Suppliers */}
        <motion.div variants={v} className="flex items-center gap-3 px-5 py-3 flex-1">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
            <Users size={14} className="text-gray-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Suppliers Tracked</p>
            <p className="text-xl font-black text-gray-900">{summary.suppliers_monitored || 0}</p>
          </div>
        </motion.div>

        {/* Open Issues */}
        <motion.div variants={v} className="flex items-center gap-3 px-5 py-3 flex-1">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-none ${(summary.issues_open || 0) > 0 ? "bg-red-50" : "bg-emerald-50"}`}>
            <AlertCircle size={14} className={(summary.issues_open || 0) > 0 ? "text-red-500" : "text-emerald-500"} />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Open Issues</p>
            <p className={`text-xl font-black ${(summary.issues_open || 0) > 0 ? "text-red-600" : "text-emerald-600"}`}>
              {summary.issues_open || 0}
            </p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
