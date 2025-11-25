const CACHE_NAME = 'learningpwa-cache-v3';
const urlsToCache = [
  '/',
  '/index.html',
  '/about.html',
  '/journal.html',
  '/projects.html',
  '/css/style.css',
  '/js/main.js',
  '/js/script.js',
  '/js/storage.js',
  '/js/browser.js',
  '/js/thirdparty.js',
  '/images/icon-192.png',
  '/images/icon-512.png',
  '/images/logo.png',
  '/images/profile.jpeg',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Use network-first strategy for reflections.json to ensure fresh data
  if (event.request.url.includes('reflections.json')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Clone the response before caching
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return response;
        })
        .catch(() => {
          // If network fails, try to serve from cache
          return caches.match(event.request);
        })
    );
  } else {
    // Use cache-first strategy for static assets
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          return response || fetch(event.request);
        })
    );
  }
});
