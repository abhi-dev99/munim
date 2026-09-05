"use client";

import { useState, useEffect } from "react";
import { FileText, Download, Loader2, AlertCircle } from "lucide-react";

export default function ReportsPanel({ traderId, apiBase }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);
  const [genSuccess, setGenSuccess] = useState(null);

  const months = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  useEffect(() => {
    if (!traderId || traderId === "demo") { setLoading(false); return; }
    fetchReports();
  }, [traderId]);

  async function fetchReports() {
    try {
      const res = await fetch(`${apiBase}/api/v1/dashboard/reports/${traderId}`);
      const data = await res.json();
      setReports(data.reports || []);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  }

  async function generateReport() {
    if (!traderId || traderId === "demo") return;
    setGenerating(true);
    setGenError(null);
    setGenSuccess(null);

    try {
      const now = new Date();
      const res = await fetch(
        `${apiBase}/api/v1/dashboard/reports/generate/${traderId}?month=${now.getMonth() + 1}&year=${now.getFullYear()}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) {
        setGenError(data.detail || "Report generation failed");
      } else {
        setGenSuccess(data.pdf_url);
        fetchReports(); // Refresh list
      }
    } catch (err) {
      setGenError("Network error — check backend connection");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-black">Monthly Reports</h2>
          <p className="text-[var(--text-secondary)] mt-1">Munim Report — full ITC, supplier health & CA handoff</p>
        </div>
        <button
          onClick={generateReport}
          disabled={generating || !traderId || traderId === "demo"}
          className="flex items-center gap-2 px-5 py-2.5 bg-black text-white font-bold text-sm rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          {generating ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
          <span>{generating ? "Generating..." : "Generate This Month"}</span>
        </button>
      </div>

      {genSuccess && (
        <div className="p-4 glass-card border border-[var(--border-subtle)] flex items-center gap-3">
          <FileText size={20} className="text-black" />
          <div className="flex-1">
            <p className="font-bold text-black text-sm">Report generated!</p>
            <p className="text-xs text-[var(--text-secondary)]">PDF ready. Click to download.</p>
          </div>
          <a href={genSuccess} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-1.5 bg-black text-white text-sm font-bold rounded hover:bg-gray-800">
            <Download size={14} /> Download
          </a>
        </div>
      )}

      {genError && (
        <div className="p-4 glass-card border border-[var(--border-subtle)] flex items-center gap-3">
          <AlertCircle size={20} className="text-[var(--red-primary)]" />
          <p className="text-sm text-[var(--text-secondary)]">{genError}</p>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-primary)]">
              <th className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">Period</th>
              <th className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">ITC Confirmed</th>
              <th className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">Invoices</th>
              <th className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">Issues</th>
              <th className="text-right px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">PDF</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-[var(--text-muted)] text-sm">Loading reports...</td></tr>
            ) : reports.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-[var(--text-muted)] text-sm">No reports generated yet. Click "Generate This Month" above.</td></tr>
            ) : (
              reports.map((report) => (
                <tr key={`${report.year}-${report.month}`} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-primary)] transition-colors">
                  <td className="px-6 py-4 font-bold text-black text-sm">{months[report.month]} {report.year}</td>
                  <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">₹{Number(report.total_itc_confirmed || 0).toLocaleString('en-IN')}</td>
                  <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">{report.total_invoices_processed || 0}</td>
                  <td className="px-6 py-4 text-sm text-[var(--text-secondary)]">{report.total_issues_count || 0}</td>
                  <td className="px-6 py-4 text-right">
                    {report.pdf_url ? (
                      <a href={report.pdf_url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-black text-white text-xs font-bold rounded hover:bg-gray-800">
                        <Download size={12} /> PDF
                      </a>
                    ) : (
                      <span className="text-xs text-[var(--text-muted)]">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
