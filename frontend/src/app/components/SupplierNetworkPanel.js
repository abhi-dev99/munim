"use client";

import { useCallback, useEffect, useState } from "react";
import { Network, RefreshCw, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { getSupplierNetwork } from "../utils/api";
import { useLanguage } from "../context/LanguageContext";
import PanelState, { describeError } from "./PanelState";

/**
 * What every other business Munim monitors has experienced of these suppliers.
 *
 * A CA sees one client's history with a supplier. Munim sees all of them, and
 * "this GSTIN has failed to report 4 of 11 invoices across 3 other businesses"
 * is a judgement no single set of books can support. It is the one signal in
 * this product that gets strictly better with scale.
 *
 * The honesty rules are enforced in the backend (`domain/network_intel.py`),
 * and this panel is built to render them rather than hide them:
 *
 *   - Counts leave; identities never do. Nothing here names another trader.
 *   - Below a minimum cohort, the answer is "not enough data" with the reason
 *     shown — a stated absence, not a silent zero. Most rows will look like
 *     this early on, and that is the correct appearance of a network effect
 *     that has not been earned yet.
 */

const VERDICTS = {
  RISKY: { key: "net_risky", Icon: ShieldAlert, color: "var(--red-primary)", chip: "bg-red-50 text-red-700" },
  MIXED: { key: "net_mixed", Icon: ShieldQuestion, color: "#B45309", chip: "bg-amber-50 text-amber-800" },
  CLEAN: { key: "net_clean", Icon: ShieldCheck, color: "var(--green-primary)", chip: "bg-emerald-50 text-emerald-700" },
  UNKNOWN: { key: "net_unknown", Icon: ShieldQuestion, color: "var(--text-muted)", chip: "bg-gray-100 text-gray-500" },
};

export default function SupplierNetworkPanel({ traderId, apiBase }) {
  const { t } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(async () => {
    if (!traderId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await getSupplierNetwork(apiBase, traderId));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [traderId, apiBase]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <PanelState state="loading" rows={3} />;
  if (error) {
    return <PanelState state="error" error={error} message={describeError(error)} onRetry={load} />;
  }

  const suppliers = data?.suppliers || [];
  if (!suppliers.length) {
    return (
      <PanelState
        state="empty"
        title={t("net_title")}
        message="No suppliers on file yet. Upload an invoice and this fills in."
      />
    );
  }

  // Reportable rows first by default. The rest are shown on request, because
  // a list where nineteen of twenty rows say "not enough data" buries the one
  // that does not.
  const reportable = suppliers.filter((s) => s.available);
  const rest = suppliers.filter((s) => !s.available);
  const visible = showAll ? [...reportable, ...rest] : reportable;

  return (
    <section className="bg-white border border-[var(--border-subtle)]" aria-labelledby="network-heading">
      <header className="flex items-start justify-between gap-3 p-3 sm:p-4 border-b border-[var(--border-subtle)]">
        <div className="min-w-0">
          <h2
            id="network-heading"
            className="text-sm font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2"
          >
            <Network className="w-4 h-4" aria-hidden="true" />
            {t("net_title")}
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">{t("net_subtitle")}</p>
        </div>
        <button
          onClick={load}
          aria-label="Refresh network data"
          className="shrink-0 p-1.5 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[var(--text-muted)]" aria-hidden="true" />
        </button>
      </header>

      <div className="px-3 sm:px-4 py-2.5 border-b border-[var(--border-subtle)]">
        <p className="text-xs text-[var(--text-secondary)]">
          <span className="font-bold tabular-nums">{data.reportable}</span> of{" "}
          <span className="tabular-nums">{suppliers.length}</span> {t("net_reportable")}
          {data.flagged > 0 && (
            <>
              {" · "}
              <span className="font-bold" style={{ color: "var(--red-primary)" }}>
                {data.flagged} {t("net_risky").toLowerCase()}
              </span>
            </>
          )}
        </p>
      </div>

      {!reportable.length && !showAll && (
        <div className="p-4">
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            None of these suppliers is shared with enough other businesses yet for Munim
            to report a pattern without effectively identifying one of them. This fills
            in as more traders join.
          </p>
        </div>
      )}

      {!!visible.length && (
        <ul className="divide-y divide-[var(--border-subtle)] max-h-96 overflow-y-auto">
          {visible.map((s) => {
            const v = VERDICTS[s.verdict] || VERDICTS.UNKNOWN;
            const { Icon } = v;
            return (
              <li key={s.gstin} className="flex items-start gap-3 p-3">
                <Icon className="w-4 h-4 mt-0.5 shrink-0" style={{ color: v.color }} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {s.supplier_name}
                    </p>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 ${v.chip}`}>
                      {t(v.key)}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">{s.gstin}</p>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                    {s.summary || s.reason}
                  </p>
                </div>
                {s.available && (
                  <p
                    className="shrink-0 text-sm font-bold tabular-nums"
                    style={{ color: v.color }}
                    title="Share of checked invoices this supplier failed to report"
                  >
                    {Math.round((s.default_rate || 0) * 100)}%
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {!!rest.length && (
        <button
          onClick={() => setShowAll((a) => !a)}
          className="w-full p-3 text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text-primary)] border-t border-[var(--border-subtle)] transition-colors"
        >
          {showAll
            ? "Hide suppliers without enough network data"
            : `Show ${rest.length} supplier${rest.length === 1 ? "" : "s"} without enough network data`}
        </button>
      )}

      <p className="px-3 sm:px-4 py-2.5 text-[11px] text-[var(--text-muted)] leading-relaxed border-t border-[var(--border-subtle)]">
        Aggregate only. Munim never shows one business anything about another business&apos;s
        invoices, amounts or identity — only how many were affected.
      </p>
    </section>
  );
}
