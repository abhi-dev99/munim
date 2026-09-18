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

  const [reportsSortField, setReportsSortField] = useState('yearMonth');
  const [reportsSortDirection, setReportsSortDirection] = useState('desc');
  const [reportsSearch, setReportsSearch] = useState('');

  const handleReportsSort = (field) => {
    if (reportsSortField === field) {
      setReportsSortDirection(reportsSortDirection === "asc" ? "desc" : "asc");
    } else {
      setReportsSortField(field);
      setReportsSortDirection("desc");
    }
  };

  const filteredAndSortedReports = reports
    .filter(r => reportsSearch === "" || `${months[r.month]} ${r.year}`.toLowerCase().includes(reportsSearch.toLowerCase()))
    .sort((a, b) => {
      let aValue = a[reportsSortField];
      let bValue = b[reportsSortField];
      if (reportsSortField === 'yearMonth') {
        aValue = `${a.year}${String(a.month).padStart(2, '0')}`;
        bValue = `${b.year}${String(b.month).padStart(2, '0')}`;
      } else if (reportsSortField === 'total_itc_confirmed') {
        aValue = Number(a.total_itc_confirmed || 0);
        bValue = Number(b.total_itc_confirmed || 0);
      } else if (reportsSortField === 'total_invoices_processed') {
        aValue = Number(a.total_invoices_processed || 0);
        bValue = Number(b.total_invoices_processed || 0);
      } else if (reportsSortField === 'total_issues_count') {
        aValue = Number(a.total_issues_count || 0);
        bValue = Number(b.total_issues_count || 0);
      }
      
      if (aValue < bValue) return reportsSortDirection === "asc" ? -1 : 1;
      if (aValue > bValue) return reportsSortDirection === "asc" ? 1 : -1;
      return 0;
    });

  const [gstr2bSortField, setGstr2bSortField] = useState('invoice_date');
  const [gstr2bSortDirection, setGstr2bSortDirection] = useState('desc');
  const [gstr2bSearch, setGstr2bSearch] = useState('');
  const [gstr2bFilterItc, setGstr2bFilterItc] = useState('ALL'); // ALL, AVAILABLE, BLOCKED
  const [expandedGstr2bGroups, setExpandedGstr2bGroups] = useState({});

  const toggleGstr2bGroup = (key) => {
    setExpandedGstr2bGroups(prev => ({
      ...prev,
      [key]: prev[key] === undefined ? false : !prev[key]
    }));
  };

  const handleGstr2bSort = (field) => {
    if (gstr2bSortField === field) {
      setGstr2bSortDirection(gstr2bSortDirection === "asc" ? "desc" : "asc");
    } else {
      setGstr2bSortField(field);
      setGstr2bSortDirection("desc");
    }
  };

  const generateReportForPeriod = async (month, year) => {
    if (!traderId || traderId === "demo") return;
    setGenerating(true);
    setGenError(null);
    setGenSuccess(null);

    // Show toast "Generating PDF..."
    const toastId = setTimeout(() => {}, 10); // dummy timeout to trigger render if needed
    
    try {
      const res = await fetch(
        `${apiBase}/api/v1/reports/generate/${traderId}?month=${month}&year=${year}&send_whatsapp=false`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) {
        setGenError(data.detail || "Report generation failed");
      } else {
        setGenSuccess(data.pdf_url);
        fetchReports(); // Refresh list
        // Trigger download
        window.open(data.pdf_url, '_blank');
      }
    } catch (err) {
      setGenError("Network error — check backend connection");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 pb-1">
        <input
          type="text"
          placeholder="Search period..."
          value={reportsSearch}
          onChange={(e) => setReportsSearch(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-gray-400 w-48"
        />
      </div>

      {generating && (
        <div className="p-4 bg-black text-white rounded-lg flex items-center gap-3 shadow-lg fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5">
          <Loader2 size={20} className="animate-spin" />
          <div className="flex-1">
            <p className="font-bold text-sm">Generating PDF...</p>
            <p className="text-xs text-gray-300">This might take a few seconds.</p>
          </div>
        </div>
      )}

      {genSuccess && !generating && (
        <div className="p-4 bg-[var(--green-primary)] text-white rounded-lg flex items-center gap-3 shadow-lg fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5">
          <CheckCircle2 size={20} />
          <div className="flex-1">
            <p className="font-bold text-sm">Download Initiated!</p>
            <p className="text-xs text-green-100">Your PDF report is ready.</p>
          </div>
          <a href={genSuccess} target="_blank" rel="noopener noreferrer" className="px-3 py-1 bg-white text-[var(--green-primary)] rounded font-bold text-xs hover:bg-green-50 transition-colors">
            Download PDF
          </a>
          <button onClick={() => setGenSuccess(null)} className="ml-2 hover:bg-white/20 p-1 rounded">
            <XCircle size={16} />
          </button>
        </div>
      )}

      {genError && (
        <div className="p-4 bg-[var(--red-primary)] text-white rounded-lg flex items-center gap-3 shadow-lg fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5">
          <AlertCircle size={20} />
          <p className="text-sm">{genError}</p>
          <button onClick={() => setGenError(null)} className="ml-2 hover:bg-white/20 p-1 rounded">
            <XCircle size={16} />
          </button>
        </div>
      )}

      {/* Munim Reports table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-primary)]">
              <th onClick={() => handleReportsSort('yearMonth')} className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                Period {reportsSortField === 'yearMonth' && (reportsSortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleReportsSort('total_itc_confirmed')} className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                ITC Confirmed {reportsSortField === 'total_itc_confirmed' && (reportsSortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleReportsSort('total_invoices_processed')} className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                Invoices {reportsSortField === 'total_invoices_processed' && (reportsSortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleReportsSort('total_issues_count')} className="text-left px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                Issues {reportsSortField === 'total_issues_count' && (reportsSortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th className="text-right px-6 py-3 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">PDF</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-[var(--text-muted)] text-sm">Loading reports...</td></tr>
            ) : filteredAndSortedReports.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-[var(--text-muted)] text-sm">No reports match your criteria.</td></tr>
            ) : (
              filteredAndSortedReports.map((report) => (
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
                      <button 
                        onClick={() => generateReportForPeriod(report.month, report.year)}
                        disabled={generating}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-black text-white text-xs font-bold rounded hover:bg-gray-800 disabled:opacity-50"
                      >
                        <FileText size={12} /> Generate
                      </button>
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
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-3 gap-4">
          <div>
            <h3 className="text-lg font-bold text-black">GSTR-2B Reports</h3>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">Auto-drafted ITC records uploaded from GST portal</p>
          </div>
          <div className="flex items-center gap-3">
            <input 
              type="text" 
              placeholder="Search GSTIN or Invoice..." 
              value={gstr2bSearch}
              onChange={(e) => setGstr2bSearch(e.target.value)}
              className="px-3 py-2 border border-[var(--border-subtle)] rounded-lg text-xs focus:outline-none focus:border-black"
            />
            <select 
              value={gstr2bFilterItc} 
              onChange={(e) => setGstr2bFilterItc(e.target.value)}
              className="px-3 py-2 border border-[var(--border-subtle)] rounded-lg text-xs bg-white focus:outline-none"
            >
              <option value="ALL">All ITC</option>
              <option value="AVAILABLE">Available</option>
              <option value="BLOCKED">Blocked</option>
            </select>
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
            {gstr2bRecords.map(group => {
              const filteredAndSortedRecords = group.records
                .filter(r => gstr2bFilterItc === "ALL" || (gstr2bFilterItc === "AVAILABLE" ? r.itc_eligible : !r.itc_eligible))
                .filter(r => 
                  gstr2bSearch === "" || 
                  (r.supplier_gstin && r.supplier_gstin.toLowerCase().includes(gstr2bSearch.toLowerCase())) ||
                  (r.invoice_number && r.invoice_number.toLowerCase().includes(gstr2bSearch.toLowerCase()))
                )
                .sort((a, b) => {
                  let aValue = a[gstr2bSortField];
                  let bValue = b[gstr2bSortField];
                  
                  if (gstr2bSortField === 'tax_amount') {
                    aValue = (a.igst || 0) + (a.cgst || 0) + (a.sgst || 0);
                    bValue = (b.igst || 0) + (b.cgst || 0) + (b.sgst || 0);
                  }
                  
                  if (typeof aValue === 'string') aValue = aValue.toLowerCase();
                  if (typeof bValue === 'string') bValue = bValue.toLowerCase();
                  
                  if (aValue < bValue) return gstr2bSortDirection === "asc" ? -1 : 1;
                  if (aValue > bValue) return gstr2bSortDirection === "asc" ? 1 : -1;
                  return 0;
                });

              if (filteredAndSortedRecords.length === 0) return null;

              const groupKey = `${group.year}-${group.month}`;
              const isCollapsed = expandedGstr2bGroups[groupKey] === false;

              return (
              <div key={groupKey} className="glass-card overflow-hidden">
                {/* Period header */}
                <div 
                  onClick={() => toggleGstr2bGroup(groupKey)}
                  className="flex items-center justify-between px-5 py-3 bg-[var(--bg-primary)] border-b border-[var(--border-subtle)] cursor-pointer hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-black text-sm">{months[group.month]} {group.year}</span>
                    <span className="text-xs text-[var(--text-secondary)]">({filteredAndSortedRecords.length} invoice{filteredAndSortedRecords.length !== 1 ? "s" : ""})</span>
                  </div>
                  <div className="text-[var(--text-secondary)]">
                    {isCollapsed ? "▼" : "▲"}
                  </div>
                </div>
                {!isCollapsed && (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)]">
                      <th onClick={() => handleGstr2bSort('supplier_gstin')} className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        Supplier GSTIN {gstr2bSortField === 'supplier_gstin' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th onClick={() => handleGstr2bSort('invoice_number')} className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        Invoice # {gstr2bSortField === 'invoice_number' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th onClick={() => handleGstr2bSort('invoice_date')} className="text-left px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        Date {gstr2bSortField === 'invoice_date' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th onClick={() => handleGstr2bSort('taxable_value')} className="text-right px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        Taxable {gstr2bSortField === 'taxable_value' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th onClick={() => handleGstr2bSort('tax_amount')} className="text-right px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        Tax (I+C+S) {gstr2bSortField === 'tax_amount' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th onClick={() => handleGstr2bSort('itc_eligible')} className="text-center px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] cursor-pointer hover:bg-gray-100 transition-colors">
                        ITC {gstr2bSortField === 'itc_eligible' && (gstr2bSortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSortedRecords.map(r => {
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
                )}
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
