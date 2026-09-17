"use client";

import { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, X, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function GSTR2BUpload({ traderId, apiBase, onUploadComplete }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());
  const [expanded, setExpanded] = useState(false);

  const months = [
    { v: 1, l: "January" }, { v: 2, l: "February" }, { v: 3, l: "March" },
    { v: 4, l: "April" }, { v: 5, l: "May" }, { v: 6, l: "June" },
    { v: 7, l: "July" }, { v: 8, l: "August" }, { v: 9, l: "September" },
    { v: 10, l: "October" }, { v: 11, l: "November" }, { v: 12, l: "December" },
  ];

  async function uploadFile(file) {
    if (!traderId || traderId === "demo") {
      setError("No active trader selected. Please check your trader setup.");
      return;
    }

    setUploading(true);
    setResult(null);
    setError(null);

    let m = month;
    let y = year;

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      let rtnprd = parsed?.data?.docdata?.rtnprd || parsed?.rtnprd;
      if (rtnprd && typeof rtnprd === "string" && rtnprd.length === 6) {
        const parsedM = parseInt(rtnprd.substring(0, 2), 10);
        const parsedY = parseInt(rtnprd.substring(2), 10);
        if (!isNaN(parsedM) && !isNaN(parsedY) && parsedM >= 1 && parsedM <= 12) {
          m = parsedM;
          y = parsedY;
          setMonth(m);
          setYear(y);
        }
      }
    } catch (e) {
      console.warn("Could not pre-parse JSON for date", e);
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("month", m);
    formData.append("year", y);

    try {
      const res = await fetch(`${apiBase}/api/v1/gstr2b/upload-file/${traderId}`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Upload failed");
      } else {
        setResult({ ...data, month: m, year: y });
        if (onUploadComplete) onUploadComplete();
      }
    } catch (err) {
      setError("Network error — check backend connection");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) uploadFile(file);
  }

  return (
    <div className="flex-none bg-white border border-[var(--border-subtle)]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--bg-secondary)] transition-colors"
      >
        <FileText size={14} className="text-black flex-none" />
        <span className="font-bold text-xs uppercase tracking-wider text-black flex-1 text-left">Upload GSTR-2B</span>
        <span className="text-[10px] text-[var(--text-muted)]">JSON from GST Portal</span>
        <ChevronDown size={14} className={`text-[var(--text-muted)] transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
      </button>
      {expanded && (
        <div className="border-t border-[var(--border-subtle)] p-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <motion.div
          animate={{
            scale: dragOver ? 1.02 : 1,
            backgroundColor: dragOver ? "rgba(59, 130, 246, 0.05)" : "transparent",
            borderColor: dragOver ? "var(--blue-primary)" : "var(--border-subtle)",
          }}
          transition={{ duration: 0.2 }}
          className="border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer relative overflow-hidden group hover:border-[var(--blue-primary)]"
          onClick={() => document.getElementById("gstr2b-file-input").click()}
        >
          {dragOver && (
            <motion.div 
              layoutId="glow"
              className="absolute inset-0 bg-gradient-to-tr from-[var(--blue-glow)] to-transparent opacity-50"
            />
          )}
          <input
            id="gstr2b-file-input"
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileChange}
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-3 relative z-10">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--blue-primary)]" />
              <p className="text-sm font-semibold text-black">Uploading & parsing JSON...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 relative z-10">
              <motion.div 
                whileHover={{ y: -5 }}
                className="p-4 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)] group-hover:bg-[var(--blue-glow)] group-hover:text-[var(--blue-primary)] transition-colors"
              >
                <Upload size={32} />
              </motion.div>
              <div>
                <p className="text-[15px] font-bold text-black mb-1">Drop GSTR-2B JSON here</p>
                <p className="text-xs text-[var(--text-muted)] font-medium">Or click to browse files</p>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Success result */}
      <AnimatePresence>
        {result && (
          <motion.div 
            initial={{ opacity: 0, y: 10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            className="mt-6 p-4 bg-[var(--green-glow)] border border-[rgba(16,185,129,0.2)] rounded-xl space-y-4"
          >
            <div className="flex items-start gap-3">
              <CheckCircle2 size={20} className="text-[var(--green-primary)] mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-bold text-[var(--green-primary)]">Upload Complete</p>
                <p className="text-xs text-[var(--text-secondary)] mt-1 font-medium">
                  <strong className="text-black">{result.inserted}</strong> records imported, {result.skipped} skipped <br/>
                  Period: {months.find(m => m.v === result.month)?.l} {result.year}
                </p>
              </div>
              <button onClick={() => setResult(null)} className="text-[var(--green-primary)] opacity-50 hover:opacity-100 transition-opacity">
                <X size={16} />
              </button>
            </div>
            {/* Re-run reconciliation button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={async () => {
                try {
                  const res = await fetch(`${apiBase}/api/v1/gstr2b/reconcile/${traderId}?month=${month}&year=${year}`, { method: "POST" });
                  const data = await res.json();
                  setResult(prev => ({ ...prev, reconciliation: data }));
                } catch (e) { /* ignore */ }
              }}
              className="w-full text-sm font-bold py-2.5 px-4 bg-white text-black border border-[rgba(16,185,129,0.2)] rounded-lg shadow-sm hover:shadow-md transition-all"
            >
              Re-run Reconciliation Engine
            </motion.button>
            {result.reconciliation && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`text-xs font-medium p-3 rounded-lg border ${
                  result.reconciliation.detail 
                    ? 'bg-red-50 border-red-200 text-red-600'
                    : result.reconciliation.newly_matched > 0
                      ? 'bg-white/50 border-white/50 text-[var(--text-secondary)]'
                      : 'bg-orange-50 border-orange-200 text-orange-700'
                }`}
              >
                {result.reconciliation.detail ? (
                  <>❌ Error: Reconciliation failed (backend error).</>
                ) : (
                  <>
                    {result.reconciliation.newly_matched > 0 ? '✅' : '⚠️'} <strong className="text-black">{result.reconciliation.newly_matched}</strong> invoices matched out of {result.reconciliation.invoices_checked} checked
                  </>
                )}
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-6 p-4 bg-[var(--red-glow)] border border-[rgba(239,68,68,0.2)] rounded-xl flex items-start gap-3"
          >
            <AlertCircle size={20} className="text-[var(--red-primary)] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold text-[var(--red-primary)]">Upload Failed</p>
              <p className="text-xs text-[var(--red-primary)] opacity-80 mt-1 font-medium">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="ml-auto text-[var(--red-primary)] opacity-50 hover:opacity-100 transition-opacity">
              <X size={16} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
        </div>
      )}
    </div>
  );
}
