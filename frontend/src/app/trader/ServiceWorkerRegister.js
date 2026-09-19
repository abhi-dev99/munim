"use client";

import { useEffect } from "react";

/**
 * Registers the app-shell service worker (public/sw.js) that makes /trader
 * installable and gives it minimal offline resilience.
 *
 * Skipped outside production: Next's dev server serves unhashed, frequently
 * rebuilt chunks, and a caching service worker fighting that reload cycle is
 * a classic source of "why am I seeing stale code" confusion. Production
 * builds emit content-hashed assets, which is what the cache-first strategy
 * in sw.js is designed around.
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;
    if (process.env.NODE_ENV !== "production") return;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/trader/" })
      .catch((err) => console.warn("Service worker registration failed:", err));
  }, []);

  return null;
}
