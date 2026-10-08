const CACHE_NAME = 'hidrowize-shell-v1';
const RUNTIME_CACHE = 'hidrowize-runtime-v1';
const SHELL = [
  './', './index.html', './admin.html', './styles.css', './app.js', './api.js', './map.js', './manifest.json', './icon.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  const isStaticAsset = url.origin === self.location.origin || [
    'https://cdn.jsdelivr.net', 'https://unpkg.com', 'https://fonts.googleapis.com', 'https://fonts.gstatic.com'
  ].includes(url.origin);
  if (!isStaticAsset) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put('./index.html', copy));
      return response;
    }).catch(() => caches.match('./index.html')));
    return;
  }
  event.respondWith(caches.match(request).then(cached => {
    const update = fetch(request).then(response => {
      if (response.ok || response.type === 'opaque') caches.open(RUNTIME_CACHE).then(cache => cache.put(request, response.clone()));
      return response;
    });
    return cached || update;
  }));
});
