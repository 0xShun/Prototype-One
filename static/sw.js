const CACHE_NAME = 'studentsense-cache-v2';
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

self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { title: 'StudentSense', body: event.data ? event.data.text() : '' };
  }
  event.waitUntil(self.registration.showNotification(payload.title || 'StudentSense', {
    body: payload.body || 'You have a new notification.',
    icon: '/static/logo.png',
    data: { url: payload.url || '/' },
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL(event.notification.data.url || '/', self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
    for (const client of clientList) {
      if (client.url === target && 'focus' in client) {
        return client.focus();
      }
    }
    return clients.openWindow(target);
  }));
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
