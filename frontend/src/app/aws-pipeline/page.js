"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

// Real-time view onto the AWS Step Functions invoice pipeline
// (Textract -> ComputeVerdict -> Explain -> Finalize), reading straight out
// of the same munim-invoices DynamoDB table the pipeline itself writes to.
// Deliberately its own route, not wired into the existing OTP/dashboard
// flow -- that flow's data still comes from the original Cloud Run/Supabase
// backend (see CLAUDE.md), unchanged by this page.
const AWS_READ_API_URL = process.env.NEXT_PUBLIC_AWS_READ_API_URL || "";
const AWS_READ_TOKEN = process.env.NEXT_PUBLIC_AWS_READ_TOKEN || "";

function maskTrader(id) {
  // Phone-number-shaped trader ids get the middle masked before they ever
  // render -- this page is public, and a real WhatsApp number used for
  // testing shouldn't sit on a public page just to prove the pipeline works.
  if (/^\d{10,}$/.test(id)) {
    return `${id.slice(0, 4)}${"*".repeat(id.length - 6)}${id.slice(-2)}`;
  }
  return id;
}

const STATUS_STYLE = {
  CONFIRMED: { color: "var(--ok)", bg: "var(--ok-bg)", Icon: CheckCircle2, label: "Confirmed" },
  FIXABLE_BLOCKED: { color: "var(--warn)", bg: "var(--warn-bg)", Icon: AlertTriangle, label: "Fixable / Blocked" },
  AT_RISK: { color: "var(--warn)", bg: "var(--warn-bg)", Icon: AlertTriangle, label: "At Risk" },
  INELIGIBLE: { color: "var(--muted-fg)", bg: "var(--muted-bg)", Icon: XCircle, label: "Ineligible" },
  FRAUD_FLAGGED: { color: "var(--crit)", bg: "var(--crit-bg)", Icon: XCircle, label: "Fraud Flagged" },
  EXTRACT_FAILED: { color: "var(--crit)", bg: "var(--crit-bg)", Icon: XCircle, label: "Extraction Failed" },
  RECEIVED: { color: "var(--muted-fg)", bg: "var(--muted-bg)", Icon: Clock, label: "In Pipeline" },
};

export default function AwsPipelinePage() {
  const [state, setState] = useState({ loading: true, error: null, items: [] });

  useEffect(() => {
    if (!AWS_READ_API_URL) {
      setState({ loading: false, error: "NEXT_PUBLIC_AWS_READ_API_URL not configured at build time.", items: [] });
      return;
    }
    fetch(`${AWS_READ_API_URL}?token=${encodeURIComponent(AWS_READ_TOKEN)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`AWS read API returned ${res.status}`);
        return res.json();
      })
      .then((data) => setState({ loading: false, error: null, items: data.items || [] }))
      .catch((err) => setState({ loading: false, error: err.message, items: [] }));
  }, []);

  const finalized = state.items.filter((i) => i.itc_verdict);
  const blockedTotal = finalized.reduce((sum, i) => sum + Number(i.itc_verdict?.itc_blocked || 0), 0);
  const eligibleTotal = finalized.reduce((sum, i) => sum + Number(i.itc_verdict?.itc_amount || 0), 0);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--fg)", fontFamily: "var(--font-body)" }}>
      <style>{`
        :root {
          --bg: #f7f5f2; --fg: #1c1a17; --card: #ffffff; --border: #e6e1d9;
          --muted-fg: #6b6459; --muted-bg: #efece6;
          --accent: #2f6f4f; --accent-fg: #ffffff;
          --ok: #1e7d4f; --ok-bg: #e4f4ea;
          --warn: #a5590c; --warn-bg: #fbead2;
          --crit: #b13a2f; --crit-bg: #fbe6e3;
          --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          --font-mono: "SFMono-Regular", Consolas, monospace;
        }
        @media (prefers-color-scheme: dark) {
          :root:not([data-theme="light"]) {
            --bg: #14120f; --fg: #f0ede6; --card: #1e1b17; --border: #322e27;
            --muted-fg: #a39a8a; --muted-bg: #241f19;
            --accent: #4fa172; --accent-fg: #0b1410;
            --ok: #3ecb85; --ok-bg: #10281c;
            --warn: #e2a23f; --warn-bg: #2e2210;
            --crit: #e2685a; --crit-bg: #301813;
          }
        }
        :root[data-theme="dark"] {
          --bg: #14120f; --fg: #f0ede6; --card: #1e1b17; --border: #322e27;
          --muted-fg: #a39a8a; --muted-bg: #241f19;
          --accent: #4fa172; --accent-fg: #0b1410;
          --ok: #3ecb85; --ok-bg: #10281c;
          --warn: #e2a23f; --warn-bg: #2e2210;
          --crit: #e2685a; --crit-bg: #301813;
        }
        .wrap { max-width: 920px; margin: 0 auto; padding: 32px 16px 64px; }
        .eyebrow { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); font-weight: 700; }
        h1 { font-size: 28px; margin: 6px 0 4px; letter-spacing: -0.01em; }
        .sub { color: var(--muted-fg); font-size: 14px; margin: 0 0 24px; line-height: 1.5; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 28px; }
        .stat { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
        .stat-label { font-size: 12px; color: var(--muted-fg); margin-bottom: 4px; }
        .stat-value { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; margin-bottom: 12px; }
        .row-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
        .trader { font-family: var(--font-mono); font-size: 13px; color: var(--muted-fg); }
        .pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .reason { margin-top: 10px; font-size: 14px; line-height: 1.5; }
        .meta { margin-top: 8px; font-size: 12px; color: var(--muted-fg); display: flex; gap: 14px; flex-wrap: wrap; }
        .amt { font-variant-numeric: tabular-nums; font-weight: 600; }
        .empty, .err { text-align: center; color: var(--muted-fg); padding: 48px 16px; }
        .footer-note { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 12px; color: var(--muted-fg); line-height: 1.6; }
      `}</style>
      <div className="wrap">
        <div className="eyebrow">Munim-AI &middot; AWS Ship-It Build</div>
        <h1>Invoice Pipeline — Live from DynamoDB</h1>
        <p className="sub">
          Every row below is read directly off <code>munim-invoices</code>, written by the real
          Step Functions pipeline (Meta webhook &rarr; Textract &rarr; ComputeVerdict &rarr; Bedrock
          Explain &rarr; Finalize). Nothing here is seeded or simulated for this page.
        </p>

        {state.loading && (
          <div className="empty"><Loader2 className="animate-spin" style={{ display: "inline" }} /> Loading live data&hellip;</div>
        )}

        {state.error && (
          <div className="err">Couldn&rsquo;t reach the AWS read API: {state.error}</div>
        )}

        {!state.loading && !state.error && (
          <>
            <div className="stats">
              <div className="stat">
                <div className="stat-label">Invoices processed</div>
                <div className="stat-value">{state.items.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Verdicts finalized</div>
                <div className="stat-value">{finalized.length}</div>
              </div>
              <div className="stat">
                <div className="stat-label">ITC blocked (&#8377;)</div>
                <div className="stat-value">{blockedTotal.toLocaleString("en-IN")}</div>
              </div>
              <div className="stat">
                <div className="stat-label">ITC eligible (&#8377;)</div>
                <div className="stat-value">{eligibleTotal.toLocaleString("en-IN")}</div>
              </div>
            </div>

            {state.items.length === 0 && <div className="empty">No invoices in the pipeline yet.</div>}

            {state.items.map((it) => {
              const verdict = it.itc_verdict;
              const style = STATUS_STYLE[it.status] || STATUS_STYLE.RECEIVED;
              const Icon = style.Icon;
              return (
                <div className="card" key={it.invoice_id}>
                  <div className="row-top">
                    <span className="trader">{maskTrader(it.trader_id)}</span>
                    <span className="pill" style={{ color: style.color, background: style.bg }}>
                      <Icon size={14} /> {style.label}
                    </span>
                  </div>
                  {verdict && (
                    <>
                      <div className="reason">{verdict.reason}</div>
                      <div className="meta">
                        {Number(verdict.itc_blocked) > 0 && <span className="amt">Blocked: &#8377;{Number(verdict.itc_blocked).toLocaleString("en-IN")}</span>}
                        {Number(verdict.itc_amount) > 0 && <span className="amt">Eligible: &#8377;{Number(verdict.itc_amount).toLocaleString("en-IN")}</span>}
                        {verdict.legal_section && <span>Section {verdict.legal_section}</span>}
                        {it.gstin_supplier && <span>GSTIN {it.gstin_supplier}</span>}
                      </div>
                    </>
                  )}
                  <div className="meta">
                    {it.received_at && <span>Received {new Date(it.received_at).toLocaleString("en-IN")}</span>}
                    {it.finalized_at && <span>Finalized {new Date(it.finalized_at).toLocaleString("en-IN")}</span>}
                  </div>
                </div>
              );
            })}
          </>
        )}

        <div className="footer-note">
          Source: DynamoDB table <code>munim-invoices</code>, ap-south-1, read through a dedicated
          token-gated Lambda + API Gateway endpoint (never the OTP/session path). Trader identifiers
          that look like phone numbers are masked before render.
        </div>
      </div>
    </div>
  );
}
