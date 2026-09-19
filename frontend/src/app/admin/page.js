"use client";
import { authFetch, adminHeaders, ensureAdminKey } from "@/src/app/utils/api";


import { useState, useEffect } from "react";
import { Trash2, Loader2, AlertCircle } from "lucide-react";
import { PanelStateRow } from "../components/PanelState";
import ToastStack, { useToasts } from "../components/Toast";
import ConfirmDialog from "../components/ConfirmDialog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [traders, setTraders] = useState([]);
  const [selectedTrader, setSelectedTrader] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  // Deletion is irreversible, so it stays gated -- the gate is just no longer
  // an OS confirm() box. `pending` is the request; null means no dialog.
  const [pending, setPending] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const { toasts, toast, dismissToast } = useToasts();

  // Ops surface: the delete endpoints below are gated on X-Admin-Key, which
  // is no longer baked into the bundle -- prompt for it once per session.
  useEffect(() => {
    ensureAdminKey();
  }, []);

  useEffect(() => {
    async function fetchTraders() {
      try {
        const res = await authFetch(`${API_BASE}/api/v1/dashboard/traders`);
        if (!res.ok) throw new Error("Failed to fetch traders");
        const data = await res.json();
        setTraders(data.traders || []);
        if (data.traders?.length > 0) {
          setSelectedTrader(data.traders[0].id);
        } else {
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        setError(err);
        setLoading(false);
      }
    }
    fetchTraders();
  }, [reloadKey]);

  useEffect(() => {
    if (!selectedTrader) return;

    async function fetchInvoices() {
      setLoading(true);
      setError(null);
      // Switching traders invalidates whatever was selected for the last one --
      // the IDs wouldn't even belong to this trader's list any more.
      setSelectedIds(new Set());
      try {
        const res = await authFetch(`${API_BASE}/api/v1/dashboard/invoices/${selectedTrader}`);
        if (!res.ok) throw new Error("Failed to fetch invoices");
        const data = await res.json();
        setInvoices(data.invoices || []);
      } catch (err) {
        console.error(err);
        // Swallowing this left an empty table reading "No invoices found",
        // which is indistinguishable from a trader who genuinely has none.
        setError(err);
        setInvoices([]);
      } finally {
        setLoading(false);
      }
    }
    fetchInvoices();
  }, [selectedTrader, reloadKey]);

  async function deleteOne(id) {
    try {
      const res = await authFetch(`${API_BASE}/api/v1/admin/invoices/${id}`, {
        method: "DELETE",
        headers: adminHeaders(),
      });
      if (!res.ok) throw new Error("Delete failed");

      setInvoices((prev) => prev.filter((inv) => inv.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      toast("Invoice deleted.", { variant: "success" });
    } catch (err) {
      toast("The invoice was not deleted — the server rejected the request. It is still in the list.", {
        variant: "error",
        title: "Delete failed",
      });
    }
  }

  function toggleOne(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelectedIds((prev) =>
      prev.size === invoices.length ? new Set() : new Set(invoices.map((inv) => inv.id))
    );
  }

  async function bulkDelete(ids) {
    if (ids.length === 0) return;

    setBulkDeleting(true);
    // Fired in parallel and settled individually rather than aborting the
    // whole batch on the first failure -- a partial cleanup (delete
    // everything that actually succeeds, report exactly what didn't) is more
    // useful here than an all-or-nothing bulk op, especially for a demo
    // cleanup tool where "most of it worked" beats "none of it did."
    const results = await Promise.allSettled(
      ids.map((id) =>
        authFetch(`${API_BASE}/api/v1/admin/invoices/${id}`, {
          method: "DELETE",
          headers: adminHeaders(),
        }).then((res) => {
          if (!res.ok) throw new Error(`Delete failed for ${id}`);
          return id;
        })
      )
    );

    const succeededIds = new Set(
      results.filter((r) => r.status === "fulfilled").map((r) => r.value)
    );
    const failedCount = results.length - succeededIds.size;

    setInvoices((prev) => prev.filter((inv) => !succeededIds.has(inv.id)));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      succeededIds.forEach((id) => next.delete(id));
      return next;
    });
    setBulkDeleting(false);

    if (failedCount > 0) {
      toast(
        `Deleted ${succeededIds.size} invoice${succeededIds.size === 1 ? "" : "s"}. ${failedCount} failed and ${failedCount === 1 ? "is" : "are"} still selected — try again.`,
        { variant: "error", title: "Partly deleted", duration: 9000 }
      );
    } else {
      toast(`Deleted ${succeededIds.size} invoice${succeededIds.size === 1 ? "" : "s"}.`, { variant: "success" });
    }
  }

  // Both destructive paths funnel through the same dialog; nothing is deleted
  // until onConfirm fires.
  async function runPending() {
    if (!pending) return;
    setDeleting(true);
    try {
      if (pending.kind === "one") await deleteOne(pending.id);
      else await bulkDelete(pending.ids);
    } finally {
      setDeleting(false);
      setPending(null);
    }
  }

  const allSelected = invoices.length > 0 && selectedIds.size === invoices.length;

  return (
    <div className="min-h-screen p-8 bg-[#f4f4f5]">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-black text-black tracking-tighter uppercase mb-2">Admin Dashboard</h1>
            <p className="text-[var(--text-secondary)] font-medium">Manage and remove test transactions</p>
          </div>

          <select
            value={selectedTrader || ""}
            onChange={(e) => setSelectedTrader(e.target.value)}
            aria-label="Select trader"
            className="p-2 border border-[var(--border-subtle)] bg-white font-bold"
          >
            {traders.map(t => (
              <option key={t.id} value={t.id}>{t.name || t.business_name} ({t.id.slice(0,8)})</option>
            ))}
          </select>
        </div>

        {selectedIds.size > 0 && (
          <div className="flex items-center justify-between bg-black text-white px-5 py-3 rounded">
            <span className="text-sm font-bold">{selectedIds.size} selected</span>
            <button
              onClick={() => setPending({ kind: "bulk", ids: Array.from(selectedIds) })}
              disabled={bulkDeleting}
              aria-label={`Delete ${selectedIds.size} selected invoice${selectedIds.size === 1 ? "" : "s"}`}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--red-primary)] hover:bg-red-600 disabled:opacity-50 text-white text-sm font-bold rounded transition-colors"
            >
              {bulkDeleting ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <Trash2 size={16} aria-hidden="true" />}
              <span>{bulkDeleting ? "Deleting..." : "Delete selected"}</span>
            </button>
          </div>
        )}

        <div className="bg-white border border-[var(--border-subtle)]">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
                <th className="p-4 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    disabled={invoices.length === 0}
                    aria-label="Select all invoices"
                  />
                </th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Date</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Supplier</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Amount</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider">Status</th>
                <th className="p-4 text-sm font-semibold text-black uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <PanelStateRow colSpan={6} state="loading" rows={4} />
              ) : error ? (
                <PanelStateRow
                  colSpan={6}
                  state="error"
                  error={error}
                  title="Couldn't load invoices"
                  onRetry={() => setReloadKey((k) => k + 1)}
                />
              ) : invoices.length === 0 ? (
                <PanelStateRow
                  colSpan={6}
                  state="empty"
                  icon={AlertCircle}
                  title="No invoices found"
                  message="This trader has no invoices stored."
                />
              ) : (
                invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    className={`border-b border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)] ${selectedIds.has(inv.id) ? "bg-red-50/40" : ""}`}
                  >
                    <td className="p-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(inv.id)}
                        onChange={() => toggleOne(inv.id)}
                        aria-label={`Select invoice from ${inv.supplier_name || "unknown supplier"}`}
                      />
                    </td>
                    <td className="p-4 text-sm font-medium">{inv.invoice_date?.slice(0, 10) || "N/A"}</td>
                    <td className="p-4 text-sm font-bold text-black">{inv.supplier_name || inv.gstin_supplier || "Unknown"}</td>
                    <td className="p-4 text-sm font-medium">₹{Number(inv.total_amount || 0).toLocaleString('en-IN')}</td>
                    <td className="p-4 text-sm font-medium">{inv.itc_status}</td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() =>
                          setPending({
                            kind: "one",
                            id: inv.id,
                            label: `${inv.supplier_name || inv.gstin_supplier || "Unknown supplier"} · ₹${Number(inv.total_amount || 0).toLocaleString("en-IN")}${inv.invoice_date ? ` · ${inv.invoice_date.slice(0, 10)}` : ""}`,
                          })
                        }
                        className="p-2 text-[var(--red-primary)] hover:bg-red-50 transition-colors"
                        aria-label={`Delete invoice from ${inv.supplier_name || inv.gstin_supplier || "unknown supplier"}`}
                        title="Delete Invoice"
                      >
                        <Trash2 size={18} aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={!!pending}
        title={pending?.kind === "bulk" ? "Delete selected invoices?" : "Delete this invoice?"}
        message={
          pending?.kind === "bulk"
            ? `This permanently removes ${pending.ids.length} invoice${pending.ids.length === 1 ? "" : "s"} and ${pending.ids.length === 1 ? "its" : "their"} ITC verdicts. It cannot be undone.`
            : "This permanently removes the invoice and its ITC verdict. It cannot be undone."
        }
        detail={pending?.kind === "one" ? pending.label : undefined}
        confirmLabel={pending?.kind === "bulk" ? `Delete ${pending.ids.length}` : "Delete"}
        busy={deleting || bulkDeleting}
        onConfirm={runPending}
        onCancel={() => setPending(null)}
      />

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
