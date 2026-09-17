"use client";

import { useState, useEffect } from "react";
import { FileText, Download, Loader2, AlertCircle, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

export default function ReportsPanel({ traderId, apiBase }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);
  const [genSuccess, setGenSuccess] = useState(null);
  const [gstr2bRecords, setGstr2bRecords] = useState([]);
  const [gstr2bLoading, setGstr2bLoading] = useState(true);

  const months = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  useEffect(() => {
    if (!traderId || traderId === "demo") { setLoading(false); setGstr2bLoading(false); return; }
    fetchReports();
    fetchGSTR2B();
  }, [traderId]);

  async function fetchGSTR2B() {
    try {
      const res = await fetch(`${apiBase}/api/v1/gstr2b/records/${traderId}`);
      const data = await res.json();
      // Group by month+year
      const records = data.records || [];
      const grouped = {};
      records.forEach(r => {
        const key = `${r.year}-${String(r.month).padStart(2, "0")}`;
        if (!grouped[key]) grouped[key] = { month: r.month, year: r.year, records: [] };
        grouped[key].records.push(r);
      });
      setGstr2bRecords(Object.values(grouped).sort((a, b) => b.year - a.year || b.month - a.month));
    } catch {
      setGstr2bRecords([]);
    } finally {
      setGstr2bLoading(false);
    }
  }

  async function fetchReports() {
    try {
      const res = await fetch(`${apiBase}/api/v1/reports/list/${traderId}`);
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
        `${apiBase}/api/v1/reports/generate/${traderId}?month=${now.getMonth() + 1}&year=${now.getFullYear()}&send_whatsapp=false`,
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

      {/* Munim Reports table */}
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

      {/* ── GSTR-2B Records ─────────────────────────── */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-bold text-black">GSTR-2B Reports</h3>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">Auto-drafted ITC records uploaded from GST portal</p>
          </div>
        </div>

        {gstr2bLoading ? (
          <div className="glass-card p-8 text-center text-[var(--text-muted)] text-sm">Loading GSTR-2B data...</div>
        ) : gstr2bRecords.length === 0 ? (
          <div className="glass-card p-8 text-center text-[var(--text-muted)] text-sm">
            No GSTR-2B records uploaded yet. Use the Upload panel to import your GSTR-2B JSON from the GST portal.
          </div>
        ) : (
          <div className="space-y-4">
            {gstr2bRecords.map(group => (
              <div key={`${group.year}-${group.month}`} className="glass-card overflow-hidden">
                {/* Period header */}
                <div className="flex items-center justify-between px-5 py-3 bg-[var(--bg-primary)] border-b border-[var(--border-subtle)]">
                  <span className="font-bold text-black text-sm">{months[group.month]} {group.year}</span>
                  <span className="text-xs text-[var(--text-secondary)]">{group.records.length} invoice{group.records.length !== 1 ? "s" : ""}</span>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)]">
                      <th className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Supplier GSTIN</th>
                      <th className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Invoice #</th>
                      <th className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Date</th>
                      <th className="text-right px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Taxable</th>
                      <th className="text-right px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">Tax (I+C+S)</th>
                      <th className="text-center px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">ITC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.records.map(r => {
                      const tax = (r.igst || 0) + (r.cgst || 0) + (r.sgst || 0);
                      return (
                        <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-primary)] transition-colors">
                          <td className="px-5 py-2.5 text-xs font-mono text-[var(--text-secondary)]">{r.supplier_gstin}</td>
                          <td className="px-5 py-2.5 text-xs text-black font-medium">{r.invoice_number}</td>
                          <td className="px-5 py-2.5 text-xs text-[var(--text-secondary)]">
                            {r.invoice_date ? new Date(r.invoice_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—"}
                          </td>
                          <td className="px-5 py-2.5 text-xs text-right text-black">₹{Number(r.taxable_value || 0).toLocaleString("en-IN")}</td>
                          <td className="px-5 py-2.5 text-xs text-right text-[var(--text-secondary)]">₹{Number(tax).toLocaleString("en-IN")}</td>
                          <td className="px-5 py-2.5 text-center">
                            {r.itc_eligible
                              ? <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[var(--green-primary)]"><CheckCircle2 size={11} /> Available</span>
                              : <span className="inline-flex items-center gap-1 text-[10px] font-bold text-[var(--red-primary)]"><XCircle size={11} /> Blocked</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
