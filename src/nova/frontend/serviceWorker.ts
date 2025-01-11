/// <reference lib="webworker" />
/// <reference no-default-lib="true"/>
/// <reference lib="es2020" />

declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = 'nova-cache-v1';
const API_CACHE_NAME = 'nova-api-cache-v1';

const isApiRequest = (request: Request) => {
  return request.url.includes('/api/');
};

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/manifest.json',
        '/static/js/main.js',
        '/static/css/main.css',
      ]);
    })
  );
});

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
});

self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    (async () => {
      const cache = await caches.open(isApiRequest(event.request) ? API_CACHE_NAME : CACHE_NAME);

      try {
        const cachedResponse = await cache.match(event.request);
        if (cachedResponse) {
          return cachedResponse;
        }

        const response = await fetch(event.request);
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }

        const responseToCache = response.clone();
        await cache.put(event.request, responseToCache);
        return response;
      } catch (error) {
        const cachedResponse = await cache.match(event.request);
        if (cachedResponse) {
          return cachedResponse;
        }
        throw error;
      }
    })() as Promise<Response>
  );
});

self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-alerts') {
    event.waitUntil(
      fetch('/api/alerts/sync')
        .then((response) => response.json())
        .then((data) => {
          if (data.showNotification) {
            return self.registration.showNotification('Alerts Synced', {
              body: 'New alerts are available',
              icon: '/icon-192x192.png',
              badge: '/badge-72x72.png',
              data: { url: '/alerts' },
            });
          }
        })
    );
  }
});

self.addEventListener('push', (event: PushEvent) => {
  const data = event.data?.json() ?? {
    title: 'New Alert',
    body: 'Check your alerts for updates',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    data: { url: '/alerts' },
  };

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      data: data.data,
    })
  );
});

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close();

  event.waitUntil(
    self.clients.openWindow(event.notification.data.url)
  );
});
