"use client";

import { useState } from "react";
import { Upload, FileJson, CheckCircle2, AlertCircle } from "lucide-react";

export default function GSTR2BUpload({ traderId, apiBase }) {
  const [file, setFile] = useState(null);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());
  const [status, setStatus] = useState("idle"); // idle, uploading, success, error
  const [message, setMessage] = useState("");

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    if (!traderId) {
      setStatus("error");
      setMessage("Please select a trader first.");
      return;
    }

    setStatus("uploading");
    
    const formData = new FormData();
    formData.append("month", month);
    formData.append("year", year);
    formData.append("file", file);

    try {
      const res = await fetch(`${apiBase}/api/v1/gstr2b/upload-file/${traderId}`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setStatus("success");
        setMessage(`Successfully uploaded ${data.inserted} records. Skipped ${data.skipped}.`);
        setFile(null);
      } else {
        setStatus("error");
        setMessage(data.detail || "Upload failed.");
      }
    } catch (err) {
      setStatus("error");
      setMessage("An error occurred during upload.");
    }
  };

  return (
    <div className="glass-card p-6 border-[var(--border-subtle)]">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-black flex items-center gap-2">
          <Upload size={24} />
          Upload GSTR-2B JSON
        </h2>
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          Upload the JSON file downloaded from the GST portal to reconcile against trader invoices.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-semibold text-black mb-2">Month</label>
          <select 
            value={month} 
            onChange={(e) => setMonth(parseInt(e.target.value))}
            className="w-full p-2 border border-[var(--border-subtle)] rounded bg-[var(--bg-secondary)]"
          >
            {Array.from({length: 12}, (_, i) => i + 1).map(m => (
              <option key={m} value={m}>{new Date(0, m - 1).toLocaleString('default', { month: 'long' })}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-black mb-2">Year</label>
          <input 
            type="number" 
            value={year} 
            onChange={(e) => setYear(parseInt(e.target.value))}
            className="w-full p-2 border border-[var(--border-subtle)] rounded bg-[var(--bg-secondary)]"
          />
        </div>
      </div>

      <div className="border-2 border-dashed border-[var(--border-subtle)] rounded-lg p-8 text-center mb-6 bg-[var(--bg-secondary)]">
        <input 
          type="file" 
          id="gstr2b-file" 
          className="hidden" 
          accept=".json,application/json"
          onChange={handleFileChange}
        />
        <label htmlFor="gstr2b-file" className="cursor-pointer flex flex-col items-center justify-center">
          <FileJson size={48} className="text-[var(--text-muted)] mb-4" />
          <span className="text-black font-semibold">
            {file ? file.name : "Click to select JSON file or drag and drop"}
          </span>
          <span className="text-[var(--text-secondary)] text-sm mt-1">
            Only standard GST portal JSON export is supported
          </span>
        </label>
      </div>

      {status === "success" && (
        <div className="mb-6 p-4 rounded bg-[#e8f5e9] text-[#2e7d32] flex items-center gap-2">
          <CheckCircle2 size={20} />
          <span className="font-semibold">{message}</span>
        </div>
      )}

      {status === "error" && (
        <div className="mb-6 p-4 rounded bg-[#fde0dc] text-[#c62828] flex items-center gap-2">
          <AlertCircle size={20} />
          <span className="font-semibold">{message}</span>
        </div>
      )}

      <button 
        onClick={handleUpload}
        disabled={!file || status === "uploading"}
        className="w-full bg-black text-white font-bold py-3 px-4 rounded-md hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex justify-center items-center gap-2"
      >
        {status === "uploading" ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            Uploading...
          </>
        ) : (
          "Upload & Reconcile"
        )}
      </button>
    </div>
  );
}
