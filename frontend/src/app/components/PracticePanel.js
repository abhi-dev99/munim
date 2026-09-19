"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  ChevronRight,
  Clock,
  Link2,
  RefreshCw,
  Users,
} from "lucide-react";
import { getPracticeOverview, getClientBrief, createVendorFixLink } from "../utils/api";
import { useLanguage } from "../context/LanguageContext";
import PanelState, { describeError } from "./PanelState";

/**
 * The CA's Monday morning.
 *
 * Every other panel in this dashboard answers "how is this client doing?".
 * A CA carrying twenty to sixty clients has the inverse question, and until
 * now had to answer it by opening each client in turn. This is that question:
 * who needs me this week, ranked by rupees at risk, with the reason.
 *
 * Two deliberate choices about what this screen does NOT do:
 *
 *   - It never shows a client a number it cannot stand behind. A client whose
 *     GSTR-2B has never been reconciled shows "never reconciled", not ₹0
 *     unclaimed — because before matching runs, every 2B row is unmatched by
 *     definition and ₹0 is the one answer that is certainly wrong.
 *   - It separates "still fixable" from "window closed". A CA cannot un-miss
 *     a supplier's GSTR-1 deadline, so putting an expired item at the top of a
 *     list headed "what to do" wastes the only attention this screen has.
 */

const inr = (n) => `₹${Math.round(Number(n) || 0).toLocaleString("en-IN")}`;

const shortDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
};

function Stat({ label, value, tone = "default" }) {
  const color =
    tone === "risk" ? "var(--red-primary)"
      : tone === "good" ? "var(--green-primary)"
        : "var(--text-primary)";
  return (
    <div className="px-3 py-2.5 sm:px-4">
      <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
        {label}
      </p>
      <p className="text-lg sm:text-xl font-bold tabular-nums mt-0.5 break-words" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

/** Days remaining, rendered as a chip a CA can read without doing arithmetic. */
function DaysChip({ days, t }) {
  if (days === null || days === undefined) return null;
  if (days < 0) {
    return (
      <span className="text-[10px] font-bold px-1.5 py-0.5 bg-gray-100 text-gray-500 whitespace-nowrap">
        {Math.abs(days)} {t("pr_days_ago")}
      </span>
    );
  }
  const urgent = days <= 3;
  return (
    <span
      className={`text-[10px] font-bold px-1.5 py-0.5 whitespace-nowrap ${
        urgent ? "bg-red-100 text-red-700" : days <= 7 ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-700"
      }`}
    >
      {days} {t("pr_days_left")}
    </span>
  );
}

function ClientRow({ client, onOpen, onBrief, t }) {
  return (
    <li className="border-b border-[var(--border-subtle)] last:border-b-0">
      <div className="flex items-start gap-3 p-3 sm:p-4">
        <span
          className={`shrink-0 w-7 h-7 flex items-center justify-center text-xs font-bold ${
            client.needs_attention ? "bg-[var(--red-primary)] text-white" : "bg-gray-100 text-gray-500"
          }`}
          aria-hidden="true"
        >
          {client.rank}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold text-[var(--text-primary)] truncate">
              {client.business_name || client.name}
            </p>
            {client.is_composition && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-gray-100 text-gray-600">
                {t("pr_composition")}
              </span>
            )}
            {!client.reconciled && !client.is_composition && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-amber-50 text-amber-800">
                {t("pr_never_reconciled")}
              </span>
            )}
            <DaysChip days={client.days_to_chase} t={t} />
          </div>

          <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
            {client.why}
          </p>

          {client.citation && (
            <p className="text-[11px] text-[var(--text-muted)] mt-1 truncate">
              {client.top_reason} · {client.citation.section}
            </p>
          )}

          <div className="flex items-center gap-4 mt-2 flex-wrap">
            <span className="text-xs">
              <span className="text-[var(--text-muted)]">{t("pr_at_risk")} </span>
              <span className="font-bold tabular-nums" style={{ color: "var(--red-primary)" }}>
                {inr(client.rupees_at_risk)}
              </span>
            </span>
            {client.unclaimed_credit > 0 && (
              <span className="text-xs">
                <span className="text-[var(--text-muted)]">{t("pr_unclaimed")} </span>
                <span className="font-bold tabular-nums">{inr(client.unclaimed_credit)}</span>
              </span>
            )}
            <span className="text-xs text-[var(--text-muted)] tabular-nums">
              {client.open_items} {t("pr_open_items").toLowerCase()}
            </span>
          </div>
        </div>

        <div className="shrink-0 flex flex-col gap-1.5">
          <button
            onClick={() => onBrief(client)}
            className="text-[11px] font-bold px-2 py-1 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors whitespace-nowrap"
          >
            {t("pr_view_brief")}
          </button>
          <button
            onClick={() => onOpen(client)}
            className="text-[11px] font-medium px-2 py-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors whitespace-nowrap flex items-center gap-1"
          >
            {t("pr_open_client")}
            <ChevronRight className="w-3 h-3" aria-hidden="true" />
          </button>
        </div>
      </div>
    </li>
  );
}

function ClientBrief({ client, apiBase, onBack, t }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [linkState, setLinkState] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getClientBrief(apiBase, client.trader_id));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [apiBase, client.trader_id]);

  useEffect(() => { load(); }, [load]);

  // Copies rather than navigates: the CA is going to paste this into
  // WhatsApp or an email to the supplier, and opening it here would just show
  // the CA a page written for somebody else.
  const makeLink = async (item) => {
    setLinkState((s) => ({ ...s, [item.invoice_id]: { busy: true } }));
    try {
      const res = await createVendorFixLink(apiBase, item.invoice_id);
      try {
        await navigator.clipboard.writeText(res.url);
        setLinkState((s) => ({ ...s, [item.invoice_id]: { url: res.url, copied: true } }));
      } catch {
        // Clipboard is blocked outside a secure context. Show the URL so it
        // can still be copied by hand rather than failing silently.
        setLinkState((s) => ({ ...s, [item.invoice_id]: { url: res.url, copied: false } }));
      }
    } catch (err) {
      setLinkState((s) => ({ ...s, [item.invoice_id]: { error: describeError(err) } }));
    }
  };

  return (
    <section className="bg-white border border-[var(--border-subtle)]">
      <header className="flex items-start gap-3 p-3 sm:p-4 border-b border-[var(--border-subtle)]">
        <button
          onClick={onBack}
          aria-label={t("pr_back_to_practice")}
          className="shrink-0 p-1.5 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
        </button>
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-[var(--text-primary)] tracking-tight truncate">
            {t("pr_brief_title")} — {client.business_name || client.name}
          </h2>
          {data && (
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              {data.actionable} {t("pr_actionable").toLowerCase()} · {data.expired}{" "}
              {t("pr_expired").toLowerCase()} · {inr(data.total_amount)}
            </p>
          )}
        </div>
      </header>

      {loading && <PanelState state="loading" rows={4} />}
      {!loading && error && (
        <PanelState state="error" error={error} message={describeError(error)} onRetry={load} />
      )}
      {!loading && !error && !data?.items?.length && (
        <PanelState
          state="empty"
          title={t("pr_all_clear")}
          message="No open items for this client."
        />
      )}

      {!loading && !error && !!data?.items?.length && (
        <ul className="divide-y divide-[var(--border-subtle)] max-h-[32rem] overflow-y-auto">
          {data.items.map((item) => {
            const expired = item.days_to_chase !== null && item.days_to_chase < 0;
            const link = linkState[item.invoice_id] || {};
            return (
              <li key={item.invoice_id} className={`p-3 ${expired ? "opacity-60" : ""}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {item.supplier_name}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] truncate">
                      {item.invoice_number || "no number"} · {item.invoice_date || "no date"}
                    </p>
                    {item.reason && (
                      <p className="text-xs text-[var(--text-secondary)] mt-1">{item.reason}</p>
                    )}
                    {item.section && (
                      <p className="text-[11px] text-[var(--text-muted)] mt-0.5">{item.section}</p>
                    )}
                    {item.fix && !expired && (
                      <p className="text-[11px] text-[var(--text-secondary)] mt-1 italic">{item.fix}</p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-sm font-bold tabular-nums">{inr(item.amount)}</p>
                    <div className="mt-1 flex justify-end">
                      <DaysChip days={item.days_to_chase} t={t} />
                    </div>
                  </div>
                </div>

                {/* Only for items where a supplier is the blocker and there is
                    still time — a link chasing a supplier about a window that
                    closed in February helps nobody. */}
                {item.status === "AT_RISK" && !expired && (
                  <div className="mt-2">
                    {!link.url && (
                      <button
                        onClick={() => makeLink(item)}
                        disabled={link.busy}
                        className="text-[11px] font-bold px-2 py-1 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                      >
                        <Link2 className="w-3 h-3" aria-hidden="true" />
                        {link.busy ? "…" : t("pr_send_fix_link")}
                      </button>
                    )}
                    {link.url && (
                      <p className="text-[11px] text-[var(--text-secondary)] break-all">
                        {link.copied ? `✓ ${t("pr_link_copied")}` : link.url}
                      </p>
                    )}
                    {link.error && (
                      <p className="text-[11px]" style={{ color: "var(--red-primary)" }}>{link.error}</p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default function PracticePanel({ apiBase, onOpenClient }) {
  const { t } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [briefFor, setBriefFor] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getPracticeOverview(apiBase));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => { load(); }, [load]);

  if (briefFor) {
    return (
      <ClientBrief
        client={briefFor}
        apiBase={apiBase}
        onBack={() => setBriefFor(null)}
        t={t}
      />
    );
  }

  if (loading) return <PanelState state="loading" rows={5} />;
  if (error) {
    return <PanelState state="error" error={error} message={describeError(error)} onRetry={load} />;
  }

  const clients = data?.clients || [];
  if (!clients.length) {
    return (
      <PanelState
        state="empty"
        title={t("pr_no_clients")}
        message={t("pr_no_clients_body")}
      />
    );
  }

  const totals = data.totals || {};

  return (
    <div className="space-y-4">
      <section className="bg-white border border-[var(--border-subtle)]" aria-labelledby="practice-heading">
        <header className="flex items-start justify-between gap-3 p-3 sm:p-4 border-b border-[var(--border-subtle)]">
          <div className="min-w-0">
            <h2
              id="practice-heading"
              className="text-sm font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2"
            >
              <Users className="w-4 h-4" aria-hidden="true" />
              {t("pr_title")}
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">{t("pr_subtitle")}</p>
          </div>
          <button
            onClick={load}
            aria-label="Refresh practice"
            className="shrink-0 p-1.5 border border-[var(--border-subtle)] hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[var(--text-muted)]" aria-hidden="true" />
          </button>
        </header>

        {/* The backend tells us when a client's data could not be read. Saying
            so is the difference between an incomplete total and a wrong one. */}
        {data.partial && (
          <div
            role="alert"
            className="flex gap-2 p-3 text-xs leading-relaxed"
            style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
          >
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
            <span>{t("pr_partial")}</span>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-[var(--border-subtle)]">
          <Stat label={t("pr_clients")} value={totals.clients ?? 0} />
          <Stat label={t("pr_needs_you")} value={totals.needs_attention ?? 0} tone="risk" />
          <Stat label={t("pr_at_risk")} value={inr(totals.rupees_at_risk)} tone="risk" />
          <Stat label={t("pr_unclaimed")} value={inr(totals.unclaimed_credit)} />
        </div>

        {!!data.deadlines?.length && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 sm:px-4 py-2 border-t border-[var(--border-subtle)]">
            {data.deadlines.map((d) => (
              <span key={d.label} className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
                <CalendarClock className="w-3 h-3" aria-hidden="true" />
                <span className="font-bold text-[var(--text-secondary)]">{d.label}</span>
                <span>· {d.days_left}d</span>
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="bg-white border border-[var(--border-subtle)]">
        <ul>
          {clients.map((c) => (
            <ClientRow
              key={c.trader_id}
              client={c}
              t={t}
              onBrief={setBriefFor}
              onOpen={onOpenClient}
            />
          ))}
        </ul>
      </section>

      <p className="text-[11px] text-[var(--text-muted)] flex items-center gap-1.5 px-1">
        <Clock className="w-3 h-3" aria-hidden="true" />
        Computed {shortDate(data.generated_at) || "today"} from every invoice and GSTR-2B row in your practice.
      </p>
    </div>
  );
}
