// DB-074: tiny service worker. App shell works offline; API calls are handled (cached/queued) in api.js.
// Paths are built from the worker's own scope so it works under /SaarthiX-DocBuddy/ on GitHub Pages.
const CACHE = "docbuddy-v2";
const BASE = self.registration.scope; // e.g. https://srilaasya487.github.io/SaarthiX-DocBuddy/
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) =>
      Promise.allSettled([BASE, BASE + "manifest.webmanifest", BASE + "icon.svg"].map((u) => c.add(u)))
    )
  );
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request).then((m) => m || caches.match(BASE)))
  );
});
