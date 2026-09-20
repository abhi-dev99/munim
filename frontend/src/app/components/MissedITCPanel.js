"use client";

import { useState, useEffect, useCallback } from "react";
import { TrendingDown, Info, RefreshCw, MessageCircle, Loader2 } from "lucide-react";
import { getMissedItc, askTraderForMissingBills, getRecoveryRequests } from "../utils/api";
import { useLanguage } from "../context/LanguageContext";
import PanelState, { describeError } from "./PanelState";

/**
 * Unclaimed input tax credit — the supplier told the portal they sold to this
 * trader, but no invoice was ever matched against that GSTR-2B row.
 *
 * This is the one number in the product a shopkeeper cares about without
 * needing any GST vocabulary explained: money already earned and not taken.
 * Everything else Munim computes is a compliance position; this is a refund
 * sitting unclaimed.
 *
 * The panel never calls /gstr2b/reconcile — that endpoint writes match state
 * and can email vendors when auto_warn_vendors is on, which is not something
 * a dashboard render should trigger.
 *
 * Detection alone changes nothing, though: somebody still has to find out
 * whether the trader has the bill. "Ask the trader" closes that loop -- it
 * WhatsApps them about their largest unclaimed bills, one at a time, and their
 * reply lands back here as a status. It sends a real message to a real person,
 * so it is a button, never a render, and it reports every reason nothing was
 * sent rather than implying success.
 */

const inr = (n) =>
  `₹${Math.round(Number(n) || 0).toLocaleString("en-IN")}`;

// Recovery-request states, as stored by services/itc_recovery.py. Kept as a
// map rather than inline so an unrecognised state renders as itself instead of
// disappearing -- a request in an unknown state is something a CA should see.
const REQUEST_LABELS = {
  asked: "mi_status_asked",
  has_bill: "mi_status_has_bill",
  no_bill: "mi_status_no_bill",
  resolved: "mi_status_resolved",
};

const REQUEST_TONES = {
  asked: "bg-amber-50 text-amber-800",
  has_bill: "bg-blue-50 text-blue-800",
  no_bill: "bg-gray-100 text-gray-600",
  resolved: "bg-emerald-50 text-emerald-700",
};

export default function MissedITCPanel({ traderId, apiBase, month, year }) {
  const { t } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requests, setRequests] = useState(null);
  const [asking, setAsking] = useState(false);
  const [askResult, setAskResult] = useState(null);

  const load = useCallback(async () => {
    if (!traderId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await getMissedItc(apiBase, traderId, month, year));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [traderId, apiBase, month, year]);

  // Loaded separately and allowed to fail quietly: the unclaimed figure is the
  // point of this panel, and a recovery history that will not load must not
  // take the number down with it.
  const loadRequests = useCallback(async () => {
    if (!traderId) return;
    try {
      setRequests(await getRecoveryRequests(apiBase, traderId));
    } catch {
      setRequests(null);
    }
  }, [traderId, apiBase]);

  const ask = async () => {
    setAsking(true);
    setAskResult(null);
    try {
      const res = await askTraderForMissingBills(apiBase, traderId, { month, year });
      // Only "sent" means a message went out. Every other status is a reason
      // it did not, and the backend words each one for a CA to act on.
      setAskResult({ ok: res.status === "sent", message: res.detail || res.status });
      await loadRequests();
    } catch (err) {
      setAskResult({ ok: false, message: describeError(err) });
    } finally {
      setAsking(false);
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  if (loading) return <PanelState state="loading" rows={3} />;
  if (error) {
    return (
      <PanelState
        state="error"
        error={error}
        message={describeError(error)}
        onRetry={load}
      />
    );
  }

  const records = data?.records || [];

  // No 2B uploaded at all is a different story from "everything is claimed",
  // and conflating them would tell a CA their books are clean when in fact
  // nothing has been checked.
  if (!data?.gstr2b_records) {
    return (
      <PanelState
        state="empty"
        title="No GSTR-2B for this period"
        message="Upload the GSTR-2B export from the GST portal to see credit your suppliers reported but you have not claimed."
      />
    );
  }

  if (!records.length) {
    return (
      <PanelState
        state="empty"
        title="Nothing unclaimed"
        message={`Every GSTR-2B row for ${data.period} is matched to an invoice. No credit is being left behind.`}
      />
    );
  }

  return (
    <section
      className="bg-white border border-[var(--border-subtle)] rounded-none"
      aria-labelledby="missed-itc-heading"
    >
      <header className="flex items-start justify-between gap-3 p-3 sm:p-4 border-b border-[var(--border-subtle)]">
        <div className="min-w-0">
          <h2
            id="missed-itc-heading"
            className="text-sm font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2"
          >
            <TrendingDown className="w-4 h-4" style={{ color: "var(--red-primary)" }} aria-hidden="true" />
            Unclaimed credit
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Reported by suppliers for {data.period}, never claimed
          </p>
        </div>
        <div className="shrink-0 flex items-center gap-1.5">
          <button
            onClick={ask}
            disabled={asking}
            title={t("mi_ask_hint")}
            className="text-[11px] font-bold px-2 py-1.5 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5 whitespace-nowrap"
          >
            {asking
              ? <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
              : <MessageCircle className="w-3 h-3" aria-hidden="true" />}
            {asking ? t("mi_asking") : t("mi_ask")}
          </button>
          <button
            onClick={load}
            aria-label="Refresh unclaimed credit"
            className="p-1.5 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[var(--text-muted)]" aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="p-3 sm:p-4 border-b border-[var(--border-subtle)]">
        <p className="text-2xl sm:text-3xl font-bold tracking-tight break-words" style={{ color: "var(--red-primary)" }}>
          {inr(data.unclaimed_tax)}
        </p>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          across {data.count} invoice{data.count === 1 ? "" : "s"} worth{" "}
          {inr(data.unclaimed_taxable)} in purchases
        </p>
      </div>

      {/* The figure is only meaningful once matching has been attempted. Before
          that every row is unmatched by definition, so the backend flags it
          rather than letting the panel quote a number the CA would have to
          disbelieve. */}
      {!data.reconciled && data.note && (
        <div
          role="note"
          className="flex gap-2 p-3 text-xs leading-relaxed"
          style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
        >
          <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
          <span>{data.note}</span>
        </div>
      )}

      <ul className="divide-y divide-[var(--border-subtle)] max-h-80 overflow-y-auto">
        {records.slice(0, 25).map((r) => (
          <li key={r.record_id} className="flex items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                {r.supplier_name}
              </p>
              <p className="text-xs text-[var(--text-muted)] truncate">
                {r.invoice_number || "no number"} · {r.invoice_date || "no date"}
              </p>
            </div>
            <p className="text-sm font-bold text-[var(--text-primary)] shrink-0 tabular-nums">
              {inr(r.tax)}
            </p>
          </li>
        ))}
      </ul>

      {records.length > 25 && (
        <p className="p-3 text-xs text-[var(--text-muted)] border-t border-[var(--border-subtle)]">
          Showing the 25 largest of {records.length}.
        </p>
      )}

      {askResult && (
        <p
          role="status"
          className="p-3 text-xs leading-relaxed border-t border-[var(--border-subtle)]"
          style={{ color: askResult.ok ? "var(--green-primary)" : "var(--red-primary)" }}
        >
          {askResult.message}
        </p>
      )}

      {!!requests?.requests?.length && (
        <div className="border-t border-[var(--border-subtle)]">
          <div className="flex items-baseline justify-between gap-3 p-3 pb-1.5">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
              {t("mi_requests")}
            </p>
            <p className="text-[11px] text-[var(--text-muted)] tabular-nums">
              {requests.recovered_tax > 0 && (
                <span style={{ color: "var(--green-primary)" }}>
                  {t("mi_recovered")} {inr(requests.recovered_tax)}
                </span>
              )}
              {requests.written_off_tax > 0 && (
                <span className="ml-2">
                  {t("mi_written_off")} {inr(requests.written_off_tax)}
                </span>
              )}
            </p>
          </div>
          <ul className="divide-y divide-[var(--border-subtle)] max-h-56 overflow-y-auto">
            {requests.requests.slice(0, 15).map((r) => (
              <li key={r.event_id} className="flex items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                    {r.supplier_name || "Unknown supplier"}
                  </p>
                  <p className="text-[11px] text-[var(--text-muted)] truncate">
                    {r.invoice_number || "no number"} · {inr(r.tax)}
                  </p>
                </div>
                <span
                  className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 ${
                    REQUEST_TONES[r.status] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {REQUEST_LABELS[r.status] ? t(REQUEST_LABELS[r.status]) : r.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
