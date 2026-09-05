import os
filepath = 'frontend/src/app/components/MoneyMeter.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will rewrite MoneyMeter.js entirely since it's only 143 lines and needs major refactoring.
new_content = """"use client";

import { ArrowUpRight, IndianRupee, ShieldAlert, CheckCircle2, TrendingUp, FileText, Users, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useRef } from "react";

export default function MoneyMeter({ summary, apiBase, isComposition = false, onSwitchTab, prefs, onSortTop, onSortBottom }) {
  const dragItem = useRef(null);
  const dragOverItem = useRef(null);

  if (!summary) return null;

  const { itc_buckets, total_recovery_possible } = summary;
  const mockTotalSales  = (summary.invoices_processed || 0) * 12500;
  const mockTaxPayable  = mockTotalSales * 0.01;
  const confirmed       = itc_buckets?.confirmed || 0;
  const atRisk          = (itc_buckets?.fixable_blocked || 0) + (itc_buckets?.at_risk || 0);
  const totalITC        = confirmed + atRisk;

  const v = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } };

  // --- Handlers ---
  const handleSortTop = () => {
    if (!onSortTop || dragItem.current === null || dragOverItem.current === null) return;
    const currentOrder = prefs?.money_meter_top || ["confirmed", "at_risk", "recovery"];
    let _order = [...currentOrder];
    const draggedItemContent = _order.splice(dragItem.current, 1)[0];
    _order.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    onSortTop(_order);
  };

  const handleSortBottom = () => {
    if (!onSortBottom || dragItem.current === null || dragOverItem.current === null) return;
    const currentOrder = prefs?.money_meter_bottom || ["invoices", "suppliers", "issues"];
    let _order = [...currentOrder];
    const draggedItemContent = _order.splice(dragItem.current, 1)[0];
    _order.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    onSortBottom(_order);
  };

  // --- Renderers ---
  const topOrder = prefs?.money_meter_top || ["confirmed", "at_risk", "recovery"];
  const bottomOrder = prefs?.money_meter_bottom || ["invoices", "suppliers", "issues"];

  const renderTopWidget = (id, index) => {
    let content = null;
    if (isComposition) {
       // Composition is static for now
       return null; 
    }
    
    switch (id) {
      case "confirmed":
        content = (
          <div className="bg-white border border-gray-200 rounded-xl p-4 h-full">
            <div className="flex items-center gap-1.5 mb-2">
              <CheckCircle2 size={13} className="text-emerald-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Confirmed ITC</span>
            </div>
            <p className="text-2xl font-black text-gray-900">₹{confirmed.toLocaleString("en-IN")}</p>
            <p className="text-xs text-emerald-600 font-medium mt-2 flex items-center gap-1">
              <ArrowUpRight size={11} />This month · live
            </p>
            {totalITC > 0 && (
              <div className="mt-2.5 bg-gray-100 rounded-full h-1 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.round((confirmed / totalITC) * 100)}%` }} />
              </div>
            )}
          </div>
        );
        break;
      case "at_risk":
        content = (
          <div className="bg-white border border-gray-200 rounded-xl p-4 h-full">
            <div className="flex items-center gap-1.5 mb-2">
              <ShieldAlert size={13} className="text-amber-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">At Risk / Blocked</span>
            </div>
            <p className="text-2xl font-black text-gray-900">₹{atRisk.toLocaleString("en-IN")}</p>
            <button
              onClick={() => onSwitchTab?.("actions")}
              className="text-xs text-amber-600 font-semibold mt-2 flex items-center gap-1 hover:underline"
            >
              <ArrowUpRight size={11} />Requires action by 18th →
            </button>
          </div>
        );
        break;
      case "recovery":
        content = (
          <div className="bg-white border border-gray-200 rounded-xl p-4 h-full">
            <div className="flex items-center gap-1.5 mb-2">
              <IndianRupee size={13} className="text-blue-500" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Potential Recovery</span>
            </div>
            <p className="text-2xl font-black text-blue-700">₹{(total_recovery_possible || 0).toLocaleString("en-IN")}</p>
            <p className="text-xs text-gray-400 font-medium mt-2">Fix supplier issues to unlock</p>
          </div>
        );
        break;
    }

    return (
      <motion.div 
        variants={v} 
        key={id}
        draggable
        onDragStart={() => { dragItem.current = index; }}
        onDragEnter={(e) => { dragOverItem.current = index; e.preventDefault(); }}
        onDragOver={(e) => e.preventDefault()}
        onDragEnd={handleSortTop}
        className="cursor-grab active:cursor-grabbing hover:ring-2 hover:ring-gray-200 transition-all rounded-xl relative"
        title="Drag to reorder"
      >
        <div className="absolute top-2 right-2 opacity-0 hover:opacity-100 z-10 p-1 bg-white/80 rounded backdrop-blur-sm pointer-events-none transition-opacity">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
        </div>
        {content}
      </motion.div>
    );
  };

  const renderBottomWidget = (id, index) => {
    let content = null;
    switch (id) {
      case "invoices":
        content = (
          <>
            <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
              <FileText size={13} className="text-gray-400" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Invoices Scanned</p>
              <p className="text-lg font-black text-gray-900">{summary.invoices_processed || 0}</p>
            </div>
          </>
        );
        break;
      case "suppliers":
        content = (
          <>
            <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-none">
              <Users size={13} className="text-gray-400" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Suppliers Tracked</p>
              <p className="text-lg font-black text-gray-900">{summary.suppliers_monitored || 0}</p>
            </div>
          </>
        );
        break;
      case "issues":
        content = (
          <>
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-none ${(summary.issues_open || 0) > 0 ? "bg-red-50" : "bg-gray-100"}`}>
              <AlertCircle size={13} className={(summary.issues_open || 0) > 0 ? "text-red-500" : "text-gray-400"} />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Open Issues</p>
              <p className={`text-lg font-black ${(summary.issues_open || 0) > 0 ? "text-red-600" : "text-gray-900"}`}>
                {summary.issues_open || 0}
              </p>
            </div>
          </>
        );
        break;
    }

    return (
      <motion.div 
        variants={v} 
        key={id}
        draggable
        onDragStart={() => { dragItem.current = index; }}
        onDragEnter={(e) => { dragOverItem.current = index; e.preventDefault(); }}
        onDragOver={(e) => e.preventDefault()}
        onDragEnd={handleSortBottom}
        className="flex items-center gap-3 px-5 py-3 flex-1 cursor-grab active:cursor-grabbing hover:bg-gray-50 transition-colors relative"
        title="Drag to reorder"
      >
        <div className="absolute top-1/2 -translate-y-1/2 right-2 opacity-0 hover:opacity-100 z-10 p-1 bg-white/80 rounded backdrop-blur-sm pointer-events-none transition-opacity">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
        </div>
        {content}
      </motion.div>
    );
  };

  return (
    <div className="space-y-3" id="money-meter-container">
      {/* ── Top 3 ITC cards ── */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }}
        className="grid grid-cols-3 gap-3"
        id="money-meter-top"
      >
        {isComposition ? (
          <>
            <motion.div variants={v} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp size={13} className="text-gray-400" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Total Sales</span>
              </div>
              <p className="text-2xl font-black text-gray-900">₹{mockTotalSales.toLocaleString("en-IN")}</p>
              <p className="text-xs text-gray-500 font-medium mt-2 flex items-center gap-1"><ArrowUpRight size={11} />Quarter-to-date</p>
            </motion.div>
            <motion.div variants={v} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <IndianRupee size={13} className="text-gray-400" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Est. Tax (1%)</span>
              </div>
              <p className="text-2xl font-black text-gray-900">₹{mockTaxPayable.toLocaleString("en-IN")}</p>
              <p className="text-xs text-gray-400 font-medium mt-2">On inward/outward proxy</p>
            </motion.div>
            <motion.div variants={v} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <FileText size={13} className="text-gray-400" />
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
            {topOrder.map((id, index) => renderTopWidget(id, index))}
          </>
        )}
      </motion.div>

      {/* ── Stats ribbon ── */}
      <motion.div
        initial="hidden" animate="show"
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07, delayChildren: 0.12 } } }}
        className="bg-white border border-gray-200 rounded-xl flex divide-x divide-gray-100 overflow-hidden"
        id="money-meter-bottom"
      >
        {bottomOrder.map((id, index) => renderBottomWidget(id, index))}
      </motion.div>
    </div>
  );
}
"""

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Refactored MoneyMeter.js")
