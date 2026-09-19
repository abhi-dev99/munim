"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CalendarClock, CheckCircle2, FileText, Loader2 } from "lucide-react";
import { openVendorFix, submitVendorFix } from "../../utils/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * What a supplier sees when their customer's CA sends them a fix link.
 *
 * This is the only surface in Munim built for somebody who is not a user. The
 * design constraints that follow from that shaped every decision here:
 *
 *   - **No jargon in the first screen.** A supplier who does not know what
 *     GSTR-2B is still has to understand what is being asked. The GST terms
 *     appear once, below the ask, for the accountant they will forward this to.
 *   - **One question, four answers.** Every extra field is a supplier who
 *     closes the tab. "I have filed it", "I will", "that is not mine", "I
 *     disagree" covers the real answers; the note box is optional.
 *   - **It never accuses.** A supplier who genuinely filed late, or whose
 *     accountant did, is a business relationship the trader wants to keep. The
 *     copy states the position and asks; it does not threaten.
 *   - **Nothing is claimed as done that was not stored.** The backend returns
 *     503 rather than 200 if it cannot record the answer, and this page shows
 *     the failure so the supplier tries again instead of walking away believing
 *     they have dealt with it.
 */

const inr = (n) => `₹${Math.round(Number(n) || 0).toLocaleString("en-IN")}`;

const prettyDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
};

const ACTIONS = [
  {
    id: "filed",
    label: "I have already reported it",
    hint: "It is in a GSTR-1 I have filed.",
  },
  {
    id: "will_file",
    label: "I will report it",
    hint: "It will be in my next GSTR-1.",
    asksDate: true,
  },
  {
    id: "not_mine",
    label: "This is not my invoice",
    hint: "I did not issue this bill.",
  },
  {
    id: "disputed",
    label: "I disagree with this bill",
    hint: "The amount or the supply is wrong.",
  },
];

function Shell({ children }) {
  return (
    <main className="min-h-screen bg-[var(--bg-secondary)] px-4 py-8">
      <div className="max-w-md mx-auto">{children}</div>
      <p className="max-w-md mx-auto mt-6 text-center text-[11px] text-[var(--text-muted)]">
        Sent by Munim.ai on behalf of your customer. This link expires.
      </p>
    </main>
  );
}

function Card({ children, className = "" }) {
  return (
    <div className={`bg-white border border-[var(--border-subtle)] ${className}`}>{children}</div>
  );
}

export default function VendorFix({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [choice, setChoice] = useState(null);
  const [expectedDate, setExpectedDate] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [done, setDone] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await openVendorFix(API_BASE, token);
      setData(res);
      if (res.already_answered?.action) setDone(null);
    } catch (err) {
      setError(err.message || "This link is not valid.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!choice) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await submitVendorFix(API_BASE, token, {
        action: choice,
        expected_date: choice === "will_file" && expectedDate ? expectedDate : null,
        note: note.trim() || null,
      });
      setDone(res.message);
    } catch (err) {
      setSubmitError(err.message || "Could not record your answer. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Shell>
        <Card className="p-6 flex items-center gap-3">
          <Loader2 className="w-4 h-4 animate-spin text-[var(--text-muted)]" aria-hidden="true" />
          <p className="text-sm text-[var(--text-secondary)]">Loading…</p>
        </Card>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell>
        <Card className="p-6">
          <AlertCircle className="w-5 h-5 mb-2" style={{ color: "var(--red-primary)" }} aria-hidden="true" />
          <h1 className="text-base font-bold text-[var(--text-primary)]">This link does not work</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1.5 leading-relaxed">{error}</p>
          <p className="text-xs text-[var(--text-muted)] mt-3">
            Links expire after two weeks. Ask your customer to send a fresh one.
          </p>
        </Card>
      </Shell>
    );
  }

  if (done) {
    return (
      <Shell>
        <Card className="p-6">
          <CheckCircle2 className="w-6 h-6 mb-2" style={{ color: "var(--green-primary)" }} aria-hidden="true" />
          <h1 className="text-base font-bold text-[var(--text-primary)]">Thank you</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1.5 leading-relaxed">{done}</p>
          <p className="text-xs text-[var(--text-muted)] mt-4">
            You can close this page. Nothing else is needed from you.
          </p>
        </Card>
      </Shell>
    );
  }

  const answered = data?.already_answered;
  const overdue = data?.days_left !== null && data?.days_left < 0;

  return (
    <Shell>
      <Card className="p-5">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
          A message from {data.buyer_name}
        </p>
        <h1 className="text-lg font-bold text-[var(--text-primary)] mt-1.5 leading-snug">
          They cannot claim the tax on one of your bills.
        </h1>
        <p className="text-sm text-[var(--text-secondary)] mt-2 leading-relaxed">
          {data.buyer_name} paid {inr(data.tax_amount)} of GST on this purchase. Until the
          invoice is reported in your GSTR-1, that money stays with the
          government instead of coming back to them.
        </p>
      </Card>

      <Card className="mt-3">
        <div className="p-4 border-b border-[var(--border-subtle)]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] flex items-center gap-1.5">
            <FileText className="w-3 h-3" aria-hidden="true" />
            The invoice
          </p>
        </div>
        <dl className="divide-y divide-[var(--border-subtle)]">
          {/* Many invoices carry no extracted trade name, in which case the
              backend falls back to the GSTIN -- and printing it twice under two
              labels just looks like a bug to the supplier reading it. */}
          {data.supplier_name && data.supplier_name !== data.supplier_gstin && (
            <div className="flex justify-between gap-3 px-4 py-2.5">
              <dt className="text-xs text-[var(--text-muted)]">Issued by</dt>
              <dd className="text-xs font-medium text-right">{data.supplier_name}</dd>
            </div>
          )}
          {data.supplier_gstin && (
            <div className="flex justify-between gap-3 px-4 py-2.5">
              <dt className="text-xs text-[var(--text-muted)]">Your GSTIN</dt>
              <dd className="text-xs font-mono text-right">{data.supplier_gstin}</dd>
            </div>
          )}
          <div className="flex justify-between gap-3 px-4 py-2.5">
            <dt className="text-xs text-[var(--text-muted)]">Invoice number</dt>
            <dd className="text-xs font-medium text-right">{data.invoice_number || "—"}</dd>
          </div>
          <div className="flex justify-between gap-3 px-4 py-2.5">
            <dt className="text-xs text-[var(--text-muted)]">Date</dt>
            <dd className="text-xs font-medium text-right">{prettyDate(data.invoice_date) || "—"}</dd>
          </div>
          <div className="flex justify-between gap-3 px-4 py-2.5">
            <dt className="text-xs text-[var(--text-muted)]">Invoice value</dt>
            <dd className="text-xs font-bold text-right tabular-nums">{inr(data.total_amount)}</dd>
          </div>
          <div className="flex justify-between gap-3 px-4 py-2.5">
            <dt className="text-xs text-[var(--text-muted)]">GST on it</dt>
            <dd className="text-xs font-bold text-right tabular-nums">{inr(data.tax_amount)}</dd>
          </div>
        </dl>

        {data.gstr1_due && (
          <div
            className="flex items-start gap-2 px-4 py-3 text-xs leading-relaxed border-t border-[var(--border-subtle)]"
            style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
          >
            <CalendarClock className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              The GSTR-1 for this invoice&apos;s period was due on {prettyDate(data.gstr1_due)}
              {overdue
                ? ". That date has passed, so it would go into an amendment rather than the original return."
                : `, ${data.days_left} day${data.days_left === 1 ? "" : "s"} from now.`}
            </span>
          </div>
        )}
      </Card>

      {answered && (
        <Card className="mt-3 p-4">
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            You already answered this on{" "}
            {prettyDate(answered.created_at) || "an earlier date"}:{" "}
            <span className="font-bold">
              {ACTIONS.find((a) => a.id === answered.action)?.label || answered.action}
            </span>
            . You can answer again below if something has changed.
          </p>
        </Card>
      )}

      <Card className="mt-3">
        <div className="p-4 border-b border-[var(--border-subtle)]">
          <h2 className="text-sm font-bold text-[var(--text-primary)]">What would you like to say?</h2>
        </div>

        <div role="radiogroup" aria-label="Your answer" className="divide-y divide-[var(--border-subtle)]">
          {ACTIONS.map((a) => (
            <label
              key={a.id}
              className={`flex items-start gap-3 p-4 cursor-pointer transition-colors ${
                choice === a.id ? "bg-gray-50" : "hover:bg-gray-50"
              }`}
            >
              <input
                type="radio"
                name="vendor-action"
                value={a.id}
                checked={choice === a.id}
                onChange={() => setChoice(a.id)}
                className="mt-0.5 shrink-0"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-[var(--text-primary)]">{a.label}</span>
                <span className="block text-xs text-[var(--text-muted)] mt-0.5">{a.hint}</span>
              </span>
            </label>
          ))}
        </div>

        {choice === "will_file" && (
          <div className="p-4 border-t border-[var(--border-subtle)]">
            <label htmlFor="expected-date" className="block text-xs font-bold text-[var(--text-primary)]">
              By when? <span className="font-normal text-[var(--text-muted)]">(optional)</span>
            </label>
            <input
              id="expected-date"
              type="date"
              value={expectedDate}
              onChange={(e) => setExpectedDate(e.target.value)}
              className="mt-1.5 w-full border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />
          </div>
        )}

        <div className="p-4 border-t border-[var(--border-subtle)]">
          <label htmlFor="vendor-note" className="block text-xs font-bold text-[var(--text-primary)]">
            Anything to add? <span className="font-normal text-[var(--text-muted)]">(optional)</span>
          </label>
          <textarea
            id="vendor-note"
            rows={3}
            maxLength={500}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Your customer will see this."
            className="mt-1.5 w-full border border-[var(--border-subtle)] px-3 py-2 text-sm resize-none"
          />
        </div>

        {submitError && (
          <p className="px-4 pb-2 text-xs" style={{ color: "var(--red-primary)" }} role="alert">
            {submitError}
          </p>
        )}

        <div className="p-4 border-t border-[var(--border-subtle)]">
          <button
            onClick={submit}
            disabled={!choice || submitting}
            className="w-full py-3 bg-black text-white text-sm font-bold disabled:opacity-40 transition-opacity flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
            {submitting ? "Sending…" : "Send this to my customer"}
          </button>
        </div>
      </Card>
    </Shell>
  );
}
