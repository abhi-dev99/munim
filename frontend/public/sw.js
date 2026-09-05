// Minimal app-shell service worker for the Munim.ai trader PWA.
//
// Scope: give the installed app *some* offline resilience — the /trader
// shell (HTML + hashed JS/CSS) stays cached so re-opening the app on a
// patchy connection shows the last-known UI instead of a blank white
// screen — and satisfy the "registered service worker" installability
// criterion. This deliberately does NOT cache or queue API calls: invoice
// upload and dashboard data always require a live round trip to the
// backend. Building an offline invoice queue is out of scope here.

const CACHE_VERSION = "munim-shell-v1";
const APP_SHELL = [
  "/trader",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(APP_SHELL))
      .catch(() => {
        // Best-effort precache — a failed fetch here (e.g. building offline)
        // shouldn't block installation; the runtime fetch handler below
        // will populate the cache lazily instead.
      })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_VERSION)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Never intercept cross-origin requests — the backend API, ngrok tunnel,
  // etc. Those must always hit the network live.
  if (url.origin !== self.location.origin) return;

  // Navigations (opening the installed app, refresh, deep link): network
  // first so traders see live data whenever they're online, falling back
  // to the cached shell only once the network is unreachable.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put("/trader", copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match("/trader"))
        )
    );
    return;
  }

  // Content-hashed static build assets and app icons: cache-first (they
  // never change under a given hash), refreshing the cache in the
  // background so future hashes stay picked up.
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((response) => {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
});
