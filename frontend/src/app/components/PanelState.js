"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

/**
 * One shared loading / error / empty treatment for every dashboard panel.
 *
 * Before this existed, a backend hiccup rendered a blank rectangle -- which
 * reads to anyone looking at the screen as "nothing was ever built here."
 * Every panel now says which of the three things happened, and an error
 * always offers a way back.
 *
 *   <PanelState state="loading" rows={4} />
 *   <PanelState state="error"  error={err} onRetry={load} />
 *   <PanelState state="empty"  title="No suppliers yet" message="Upload a GSTR-2B to start." />
 *
 * Props
 *   state      "loading" | "error" | "empty"                     (required)
 *   title      string   -- heading override
 *   message    string   -- body override
 *   error      Error|string -- used to build the default error message
 *   onRetry    fn       -- renders a retry button on the error state only
 *   retryLabel string   -- defaults to "Try again"
 *   icon       LucideIcon -- overrides the default icon (error/empty)
 *   rows       number   -- skeleton row count on the loading state
 *   variant    "card" (bordered box) | "inline" (bare, for table cells)
 *   compact    bool     -- tighter vertical padding
 *   className  string
 */

export function describeError(err) {
  if (!err) return null;
  if (typeof err === "string") return err;
  if (err.name === "TypeError" || err.message === "Failed to fetch") {
    return "Could not reach the Munim.ai server. Check that the backend is running.";
  }
  return err.message || "Something went wrong while loading this panel.";
}

const DEFAULTS = {
  error: {
    title: "Couldn't load this panel",
    message: "The server did not return data. Nothing has been lost — retry when you're ready.",
    Icon: AlertTriangle,
  },
  empty: {
    title: "Nothing here yet",
    message: "There is no data for this selection.",
    Icon: Inbox,
  },
};

function Skeleton({ rows, compact }) {
  return (
    <div
      className={`space-y-2.5 ${compact ? "p-3" : "p-4"}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Loading"
    >
      {Array.from({ length: Math.max(1, rows) }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="h-8 w-8 flex-none bg-gray-100 animate-pulse" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 bg-gray-100 animate-pulse" style={{ width: `${70 - i * 8}%` }} />
            <div className="h-2.5 bg-gray-50 animate-pulse" style={{ width: `${45 - i * 5}%` }} />
          </div>
          <div className="h-3 w-14 bg-gray-100 animate-pulse" />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export default function PanelState({
  state,
  title,
  message,
  error,
  onRetry,
  retryLabel = "Try again",
  icon,
  rows = 3,
  variant = "card",
  compact = false,
  className = "",
}) {
  const isCard = variant === "card";
  const shell = isCard
    ? `bg-white border border-[var(--border-subtle)] rounded-none ${className}`
    : className;

  if (state === "loading") {
    return (
      <div className={shell}>
        <Skeleton rows={rows} compact={compact} />
      </div>
    );
  }

  const isError = state === "error";
  const cfg = DEFAULTS[isError ? "error" : "empty"];
  const Icon = icon || cfg.Icon;
  const heading = title || cfg.title;
  const body = message || (isError ? describeError(error) || cfg.message : cfg.message);

  return (
    <div className={shell}>
      <div
        className={`flex flex-col items-center justify-center text-center ${compact ? "py-8 px-4" : "py-12 px-6"}`}
        role={isError ? "alert" : "status"}
      >
        <div
          className="w-12 h-12 rounded-none flex items-center justify-center mb-3 border"
          style={
            isError
              ? { background: "var(--red-glow)", borderColor: "rgba(239, 68, 68, 0.25)" }
              : { background: "var(--bg-secondary)", borderColor: "var(--border-subtle)" }
          }
        >
          <Icon
            size={20}
            style={{ color: isError ? "var(--red-primary)" : "var(--text-muted)" }}
          />
        </div>

        <h3 className="text-sm font-bold text-[var(--text-primary)] tracking-tight">{heading}</h3>
        <p className="text-xs text-[var(--text-secondary)] mt-1 max-w-sm leading-relaxed">{body}</p>

        {isError && onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-black text-white rounded-none text-xs font-bold uppercase tracking-wider hover:bg-gray-800 transition-colors"
          >
            <RefreshCw size={13} aria-hidden="true" />
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  );
}

/** Same thing, parked inside a <tbody> so table layouts keep their columns. */
export function PanelStateRow({ colSpan = 1, ...props }) {
  return (
    <tr>
      <td colSpan={colSpan} className="p-0">
        <PanelState variant="inline" {...props} />
      </td>
    </tr>
  );
}
