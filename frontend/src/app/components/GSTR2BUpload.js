"use client";

import { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, X } from "lucide-react";

export default function GSTR2BUpload({ traderId, apiBase, onUploadComplete }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

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

    const formData = new FormData();
    formData.append("file", file);
    formData.append("month", month);
    formData.append("year", year);

    try {
      const res = await fetch(`${apiBase}/api/v1/gstr2b/upload-file/${traderId}`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Upload failed");
      } else {
        setResult(data);
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
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-6">
        <FileText size={20} className="text-black" />
        <div>
          <h3 className="font-bold text-black text-sm uppercase tracking-wider">Upload GSTR-2B</h3>
          <p className="text-xs text-[var(--text-secondary)]">JSON export from GST Portal</p>
        </div>
      </div>

      {/* Period selector */}
      <div className="flex gap-2 mb-4">
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="flex-1 text-sm border border-[var(--border-subtle)] rounded px-3 py-1.5 bg-white text-black font-medium focus:outline-none focus:ring-1 focus:ring-black"
        >
          {months.map((m) => <option key={m.v} value={m.v}>{m.l}</option>)}
        </select>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="flex-1 text-sm border border-[var(--border-subtle)] rounded px-3 py-1.5 bg-white text-black font-medium focus:outline-none focus:ring-1 focus:ring-black"
        >
          {[2024, 2025, 2026].map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-all cursor-pointer ${
          dragOver ? "border-black bg-black/5" : "border-[var(--border-subtle)] hover:border-black/30"
        }`}
        onClick={() => document.getElementById("gstr2b-file-input").click()}
      >
        <input
          id="gstr2b-file-input"
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={handleFileChange}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-black" />
            <p className="text-sm font-medium text-black">Uploading & parsing...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload size={28} className="text-[var(--text-muted)]" />
            <p className="text-sm font-semibold text-black">Drop GSTR-2B JSON here</p>
            <p className="text-xs text-[var(--text-muted)]">Download from GST Portal → GSTR-2B → View/Download</p>
          </div>
        )}
      </div>

      {/* Success result */}
      {result && (
        <div className="mt-4 p-3 bg-white border border-[var(--border-subtle)] rounded-lg flex items-start gap-3">
          <CheckCircle2 size={16} className="text-black mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-black">Upload Complete</p>
            <p className="text-xs text-[var(--text-secondary)]">
              {result.inserted} records imported, {result.skipped} skipped · {months.find(m => m.v === result.month)?.l} {result.year}
            </p>
          </div>
          <button onClick={() => setResult(null)} className="ml-auto text-[var(--text-muted)] hover:text-black">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 bg-white border border-[var(--border-subtle)] rounded-lg flex items-start gap-3">
          <AlertCircle size={16} className="text-black mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-black">Upload Failed</p>
            <p className="text-xs text-[var(--text-secondary)]">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="ml-auto text-[var(--text-muted)] hover:text-black">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
