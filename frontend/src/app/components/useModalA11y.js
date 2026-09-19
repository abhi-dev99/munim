"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE = [
  "a[href]",
  "area[href]",
  "button:not([disabled])",
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
  "iframe",
  "object",
  "embed",
  '[tabindex]:not([tabindex="-1"])',
  '[contenteditable="true"]',
].join(",");

/**
 * Focus trapping, Escape-to-close and focus restoration for a dialog.
 *
 * Pass the ref of the dialog's outermost element (the one carrying
 * role="dialog"). The element should also carry tabIndex={-1} so there is
 * somewhere to park focus when the dialog has no focusable children yet.
 *
 *   const ref = useRef(null);
 *   useModalA11y(ref, { active: isOpen, onClose });
 */
export default function useModalA11y(containerRef, { active = true, onClose, autoFocus = true } = {}) {
  const restoreRef = useRef(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!active) return undefined;

    restoreRef.current = typeof document !== "undefined" ? document.activeElement : null;

    const visible = () => {
      const node = containerRef.current;
      if (!node) return [];
      return Array.from(node.querySelectorAll(FOCUSABLE)).filter(
        (el) => el.getClientRects().length > 0 && el.getAttribute("aria-hidden") !== "true"
      );
    };

    let cancelFocus = null;
    if (autoFocus) {
      // One frame of slack so the dialog's own content has mounted.
      const frame = requestAnimationFrame(() => {
        const first = visible()[0];
        (first || containerRef.current)?.focus?.();
      });
      cancelFocus = () => cancelAnimationFrame(frame);
    }

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (e.key !== "Tab") return;

      const node = containerRef.current;
      if (!node) return;

      const items = visible();
      if (items.length === 0) {
        e.preventDefault();
        node.focus?.();
        return;
      }

      const first = items[0];
      const last = items[items.length - 1];
      const current = document.activeElement;

      if (e.shiftKey) {
        if (current === first || !node.contains(current)) {
          e.preventDefault();
          last.focus();
        }
      } else if (current === last || !node.contains(current)) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown, true);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      if (cancelFocus) cancelFocus();
      document.removeEventListener("keydown", handleKeyDown, true);
      document.body.style.overflow = previousOverflow;
      const restore = restoreRef.current;
      if (restore && typeof restore.focus === "function" && document.contains(restore)) {
        restore.focus();
      }
    };
  }, [active, autoFocus, containerRef]);
}
