const CACHE_NAME = 'studentsense-cache-v1';
const APP_SHELL = [
  '/',
  '/offline/',
  '/static/offline.html',
  '/static/styles.css',
  '/static/manifest.json',
  '/static/logo.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((key) => {
      if (key !== CACHE_NAME) {
        return caches.delete(key);
      }
      return null;
    })))
  );
  self.clients.claim();
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const isDocumentRequest =
    event.request.mode === 'navigate' ||
    event.request.destination === 'document' ||
    (event.request.headers.get('accept') || '').includes('text/html');

  if (isDocumentRequest) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => caches.match('/static/offline.html').then((offlineResponse) => {
          if (offlineResponse) {
            return offlineResponse;
          }
          return caches.match('/');
        }))
    );

    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }

      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }

        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });
        return response;
      }).catch(() => caches.match('/static/offline.html').then((offlineResponse) => {
        if (offlineResponse) {
          return offlineResponse;
        }
        return caches.match('/');
      }));
    })
  );
});
