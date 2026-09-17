/**
 * Smart Campus Service Worker
 * Provides offline caching for static assets and application shell.
 */
const CACHE_NAME = 'smart-campus-v2';

const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/facilities.html',
    '/announcements.html',
    '/dashboard.html',
    '/report-issue.html',
    '/my-reports.html',
    '/login.html',
    '/signup.html',
    '/profile.html',
    '/CSS/style.css',
    '/css/style.css',
    '/js/app.js',
    '/manifest.json',
    '/icons/icon-192.png'
];

// Install Event: pre-cache application shell
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.warn('⚠️ Service worker asset caching partial fail:', err);
            });
        })
    );
    self.skipWaiting();
});

// Activate Event: cleanup older versions of cache
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// Fetch Event: Network-first with cache fallback for static files; Network-only for API
self.addEventListener('fetch', (event) => {
    const requestUrl = new URL(event.request.url);

    // Dynamic API requests or uploads must never be cached statically
    if (requestUrl.pathname.startsWith('/api') || requestUrl.pathname.startsWith('/uploads')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    if (event.request.mode === 'navigate') {
                        return caches.match('/index.html');
                    }
                });
            })
    );
});

