"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, ExternalLink, Info } from "lucide-react";
import { explainInvoice } from "../utils/api";
import { useLanguage } from "../context/LanguageContext";

/**
 * "Says who?"
 *
 * A verdict without a citation is an opinion. This block puts the clause of
 * the CGST Act behind an invoice's verdict on screen, in the Act's own words.
 *
 * The important behaviour here is the negative one: when the backend cannot
 * trace a verdict to a specific clause it returns `citation: null`, and this
 * component says so rather than filling the space. A plausible-looking section
 * number that turns out not to exist is the one failure a CA would never
 * forgive, and it is the reason the quoted text lives in backend code rather
 * than being generated.
 *
 * Renders nothing at all until opened — the CA asked a question, so the fetch
 * belongs to the click, not to the render of every invoice in a list.
 */
export default function WhyBlocked({ invoiceId, apiBase, defaultOpen = false }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(defaultOpen);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!invoiceId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await explainInvoice(apiBase, invoiceId));
    } catch (err) {
      setError(err.message || "Could not load the explanation.");
    } finally {
      setLoading(false);
    }
  }, [apiBase, invoiceId]);

  useEffect(() => {
    if (open && !data && !loading && !error) load();
  }, [open, data, loading, error, load]);

  if (!invoiceId) return null;

  return (
    <div className="border-t border-[var(--border-subtle)]">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        <BookOpen className="w-3.5 h-3.5 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
        <span className="text-xs font-bold text-[var(--text-primary)]">{t("why_title")}</span>
        <span className="ml-auto text-[11px] text-[var(--text-muted)]">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2.5">
          {loading && (
            <div className="space-y-2" role="status" aria-live="polite">
              <div className="h-3 bg-gray-100 animate-pulse w-1/3" />
              <div className="h-3 bg-gray-100 animate-pulse w-full" />
              <div className="h-3 bg-gray-100 animate-pulse w-5/6" />
            </div>
          )}

          {!loading && error && (
            <p className="text-xs" style={{ color: "var(--red-primary)" }}>{error}</p>
          )}

          {!loading && !error && data && !data.citation && (
            <div
              className="flex gap-2 p-2.5 text-xs leading-relaxed"
              style={{ background: "var(--bg-secondary)", color: "var(--text-secondary)" }}
            >
              <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              <span>
                {t("why_none")}
                {data.reason ? ` — “${data.reason}”` : ""}
              </span>
            </div>
          )}

          {!loading && !error && data?.citation && (
            <>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                  {t("why_section")}
                </p>
                <p className="text-xs font-bold text-[var(--text-primary)] mt-0.5">
                  {data.citation.section}
                </p>
                <p className="text-[11px] text-[var(--text-secondary)]">{data.citation.title}</p>
              </div>

              <blockquote
                className="text-[11px] leading-relaxed border-l-2 pl-2.5 py-1 text-[var(--text-secondary)]"
                style={{ borderColor: "var(--blue-primary)" }}
              >
                {data.citation.quote}
              </blockquote>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                  {t("why_means")}
                </p>
                <p className="text-xs text-[var(--text-primary)] mt-0.5 leading-relaxed">
                  {data.citation.plain}
                </p>
              </div>

              {data.citation.fix && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                    {t("why_fix")}
                  </p>
                  <p className="text-xs text-[var(--text-primary)] mt-0.5 leading-relaxed">
                    {data.citation.fix}
                  </p>
                </div>
              )}

              {/* The distinction matters to a CA: a citation resolved from the
                  engine's own recorded reason is traceable to the rule that
                  fired. One inferred from the verdict alone is a reasonable
                  guess about an older row, and is labelled as such. */}
              {data.citation_derived_from === "status" && (
                <p className="text-[11px] text-[var(--text-muted)] italic">
                  {t("why_derived_status")}
                </p>
              )}

              <a
                href={data.citation.source}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] font-bold text-[var(--blue-primary)] hover:underline"
              >
                {t("why_source")}
                <ExternalLink className="w-3 h-3" aria-hidden="true" />
              </a>
            </>
          )}
        </div>
      )}
    </div>
  );
}
