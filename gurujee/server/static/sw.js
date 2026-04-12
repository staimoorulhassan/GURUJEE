/* GURUJEE Service Worker — cache-first for static assets (T040) */
const CACHE_NAME = 'gurujee-v1';
const STATIC_ASSETS = ['/', '/static/app.js', '/static/style.css', '/static/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { url } = event.request;
  // Pass-through for API/WS paths
  if (url.includes('/chat') || url.includes('/agents') || url.includes('/ws') ||
      url.includes('/automate') || url.includes('/notifications') || url.includes('/health')) {
    return;
  }
  // Cache-first for everything else
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
