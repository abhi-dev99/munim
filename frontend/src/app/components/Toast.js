"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

/**
 * In-app toast, replacing native alert().
 *
 * There is deliberately no React context provider here: the root layout is
 * shared with other surfaces, so each screen owns its own stack. Use it as:
 *
 *   const { toasts, toast, dismissToast } = useToasts();
 *   ...
 *   toast("Warning email sent to the vendor.", { variant: "success" });
 *   ...
 *   <ToastStack toasts={toasts} onDismiss={dismissToast} />
 */

const VARIANTS = {
  success: { Icon: CheckCircle2, color: "var(--green-primary)", accent: "var(--green-primary)" },
  error:   { Icon: AlertTriangle, color: "var(--red-primary)",   accent: "var(--red-primary)"   },
  info:    { Icon: Info,          color: "var(--blue-primary)",  accent: "var(--blue-primary)"  },
};

export function useToasts() {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());
  const seq = useRef(0);

  const dismissToast = useCallback((id) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message, opts = {}) => {
    const { variant = "success", title = null, duration = 5000 } = opts;
    const id = `toast-${++seq.current}`;
    setToasts((prev) => [...prev.slice(-2), { id, message, variant, title }]);
    if (duration > 0) {
      timers.current.set(
        id,
        setTimeout(() => {
          timers.current.delete(id);
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration)
      );
    }
    return id;
  }, []);

  // Timers outliving the screen that scheduled them would setState on an
  // unmounted tree; clear them all on the way out.
  useEffect(() => {
    const map = timers.current;
    return () => {
      map.forEach((timer) => clearTimeout(timer));
      map.clear();
    };
  }, []);

  return { toasts, toast, dismissToast };
}

export default function ToastStack({ toasts = [], onDismiss }) {
  if (!toasts.length) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-[min(22rem,calc(100vw-2rem))] pointer-events-none"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((t) => {
        const cfg = VARIANTS[t.variant] || VARIANTS.info;
        const Icon = cfg.Icon;
        return (
          <div
            key={t.id}
            role={t.variant === "error" ? "alert" : "status"}
            aria-live={t.variant === "error" ? "assertive" : "polite"}
            className="pointer-events-auto bg-white border border-[var(--border-subtle)] rounded-none shadow-lg flex items-start gap-3 p-3.5 border-l-4"
            style={{ borderLeftColor: cfg.accent }}
          >
            <Icon size={17} className="flex-none mt-0.5" style={{ color: cfg.color }} aria-hidden="true" />
            <div className="flex-1 min-w-0">
              {t.title && (
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] mb-0.5">
                  {t.title}
                </p>
              )}
              <p className="text-sm text-[var(--text-primary)] font-medium leading-snug break-words">
                {t.message}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onDismiss?.(t.id)}
              aria-label="Dismiss notification"
              className="flex-none p-1 -m-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
