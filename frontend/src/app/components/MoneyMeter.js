"use client";

import { ArrowUpRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp, FileText, Users, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export default function MoneyMeter({ summary, apiBase, isComposition = false }) {
  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;
  const mockTotalSales = (summary.invoices_processed || 0) * 12500;
  const mockTaxPayable = mockTotalSales * 0.01;

  const cardVariants = {
    hidden: { opacity: 0, y: 12 },
    show:   { opacity: 1,  y: 0  },
  };

  return (
    <div className="space-y-3">
      {/* Top row — main ITC metrics */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }}
        className="grid grid-cols-3 gap-3"
      >
        {isComposition ? (
          <>
            {/* Composition: Total Sales */}
            <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl p-4 relative overflow-hidden group">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp size={14} className="text-emerald-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">Total Sales</h3>
              </div>
              <p className="text-2xl font-black text-gray-900 tracking-tight">₹{mockTotalSales.toLocaleString("en-IN")}</p>
              <p className="text-xs text-emerald-600 font-medium mt-1.5 flex items-center gap-1"><ArrowUpRight size={12} />Quarter-to-date</p>
            </motion.div>

            {/* Composition: Est. Tax */}
            <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl p-4 relative overflow-hidden">
              <div className="flex items-center gap-1.5 mb-2">
                <IndianRupee size={14} className="text-amber-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">Est. Tax (1%)</h3>
              </div>
              <p className="text-2xl font-black text-gray-900 tracking-tight">₹{mockTaxPayable.toLocaleString("en-IN")}</p>
              <p className="text-xs text-gray-400 font-medium mt-1.5">On inward/outward proxy</p>
            </motion.div>

            {/* CMP-08 Status */}
            <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl p-4 relative overflow-hidden">
              <div className="flex items-center gap-1.5 mb-2">
                <FileText size={14} className="text-blue-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">CMP-08 Status</h3>
              </div>
              <p className={`text-2xl font-black tracking-tight ${new Date().getDate() > 18 ? "text-red-600" : "text-gray-900"}`}>
                {new Date().getDate() > 18 ? "OVERDUE" : "DUE SOON"}
              </p>
              <p className={`text-xs font-medium mt-1.5 ${new Date().getDate() > 18 ? "text-red-500" : "text-gray-400"}`}>Due by 18th of next month</p>
            </motion.div>
          </>
        ) : (
          <>
            {/* Confirmed ITC */}
            <motion.div variants={cardVariants} className="bg-white border border-emerald-200 rounded-xl p-4 relative overflow-hidden group">
              <div className="absolute -top-6 -left-6 w-20 h-20 bg-emerald-400 rounded-full blur-2xl opacity-10" />
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle2 size={14} className="text-emerald-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">Confirmed ITC</h3>
              </div>
              <p className="text-2xl font-black text-gray-900 tracking-tight">₹{(itc_buckets?.confirmed || 0).toLocaleString("en-IN")}</p>
              <p className="text-xs text-emerald-600 font-medium mt-1.5 flex items-center gap-1"><ArrowUpRight size={12} />This month (live)</p>
            </motion.div>

            {/* At Risk / Blocked */}
            <motion.div variants={cardVariants} className="bg-white border border-red-200 rounded-xl p-4 relative overflow-hidden group">
              <div className="absolute -top-6 -right-6 w-20 h-20 bg-red-400 rounded-full blur-2xl opacity-10" />
              <div className="flex items-center gap-1.5 mb-2">
                <ShieldAlert size={14} className="text-red-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">At Risk / Blocked</h3>
              </div>
              <p className="text-2xl font-black text-gray-900 tracking-tight">₹{((itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0)).toLocaleString("en-IN")}</p>
              <p className="text-xs text-red-500 font-medium mt-1.5 flex items-center gap-1"><ArrowUpRight size={12} />Requires action by 18th</p>
            </motion.div>

            {/* Potential Recovery */}
            <motion.div variants={cardVariants} className="bg-white border border-blue-200 rounded-xl p-4 relative overflow-hidden group">
              <div className="absolute -bottom-6 -right-6 w-20 h-20 bg-blue-400 rounded-full blur-2xl opacity-10" />
              <div className="flex items-center gap-1.5 mb-2">
                <IndianRupee size={14} className="text-blue-500" />
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-500">Potential Recovery</h3>
              </div>
              <p className="text-2xl font-black text-blue-700 tracking-tight">₹{(total_recovery_possible || 0).toLocaleString("en-IN")}</p>
              <p className="text-xs text-gray-400 font-medium mt-1.5">Fix supplier issues to unlock</p>
            </motion.div>
          </>
        )}
      </motion.div>

      {/* Bottom row — operational metrics */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } } }}
        className="grid grid-cols-3 gap-3"
      >
        <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
            <FileText size={14} className="text-gray-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Invoices Scanned</p>
            <p className="text-xl font-black text-gray-900">{summary.invoices_processed || 0}</p>
          </div>
        </motion.div>

        <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
            <Users size={14} className="text-gray-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Suppliers Tracked</p>
            <p className="text-xl font-black text-gray-900">{summary.suppliers_monitored || 0}</p>
          </div>
        </motion.div>

        <motion.div variants={cardVariants} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center gap-3">
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
