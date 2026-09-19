"use client";

import { useRef } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import useModalA11y from "./useModalA11y";

/**
 * In-app replacement for window.confirm() on destructive actions.
 *
 * Deletion here is irreversible, so this is a real gate, not a nicety: the
 * confirm button is the only path through, and it is never the element that
 * receives initial focus.
 *
 *   <ConfirmDialog
 *     open={!!pending}
 *     title="Delete invoice?"
 *     message="This permanently removes the invoice and its ITC verdict."
 *     confirmLabel="Delete"
 *     busy={deleting}
 *     onConfirm={reallyDelete}
 *     onCancel={() => setPending(null)}
 *   />
 */
export default function ConfirmDialog({
  open,
  title = "Are you sure?",
  message,
  detail,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  destructive = true,
  busy = false,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);

  // Escape must not fire the destructive action, so it routes to cancel.
  useModalA11y(dialogRef, { active: !!open, onClose: busy ? () => {} : onCancel, autoFocus: false });

  if (!open) return null;

  const accent = destructive ? "var(--red-primary)" : "var(--uber-black)";

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby={message ? "confirm-dialog-message" : undefined}
        tabIndex={-1}
        className="bg-white rounded-none border border-[var(--border-subtle)] shadow-2xl w-full max-w-md outline-none"
      >
        <div className="p-6">
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 flex-none flex items-center justify-center border rounded-none"
              style={{
                background: destructive ? "var(--red-glow)" : "var(--bg-secondary)",
                borderColor: destructive ? "rgba(239, 68, 68, 0.25)" : "var(--border-subtle)",
              }}
            >
              <AlertTriangle size={18} style={{ color: accent }} aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h2
                id="confirm-dialog-title"
                className="text-base font-black tracking-tight text-[var(--text-primary)] uppercase"
              >
                {title}
              </h2>
              {message && (
                <p id="confirm-dialog-message" className="text-sm text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                  {message}
                </p>
              )}
              {detail && (
                <p className="text-xs text-[var(--text-muted)] mt-2 font-mono break-words">{detail}</p>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 bg-[var(--bg-secondary)] border-t border-[var(--border-subtle)]">
          <button
            type="button"
            autoFocus
            onClick={onCancel}
            disabled={busy}
            className="px-4 py-2 bg-white border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-none text-xs font-bold uppercase tracking-wider hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-white rounded-none text-xs font-bold uppercase tracking-wider transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: accent }}
          >
            {busy && <Loader2 size={13} className="animate-spin" aria-hidden="true" />}
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
