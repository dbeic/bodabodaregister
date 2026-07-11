/**
 * Service Worker for BBS Badge Management System PWA
 * Enables offline capability and caching
 */

const CACHE_NAME = 'bbs-badge-v1';
const OFFLINE_URL = '/offline';

// Assets to cache immediately
const PRECACHE_URLS = [
    '/',
    '/manifest.json',
    '/static/css/style.css',
    '/static/js/main.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png'
];

// Install event - cache core assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Pre-caching app shell');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => {
                console.log('[SW] Skip waiting on install');
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheWhitelist.indexOf(cacheName) === -1) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('[SW] Claiming clients');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip API requests - they need fresh data
    if (url.pathname.startsWith('/api/') || 
        url.pathname.startsWith('/qr-pin/') ||
        url.pathname.startsWith('/badge/')) {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip verification endpoint - needs server validation
    if (url.pathname === '/verify-qr') {
        event.respondWith(fetch(request));
        return;
    }
    
    // Try cache first, fall back to network
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {
                if (cachedResponse) {
                    // Return cached response and update cache in background
                    event.waitUntil(
                        fetch(request).then(networkResponse => {
                            return caches.open(CACHE_NAME).then(cache => {
                                cache.put(request, networkResponse.clone());
                                return networkResponse;
                            });
                        }).catch(() => {
                            // Network failed, cached response is fine
                        })
                    );
                    return cachedResponse;
                }
                
                // Not in cache, try network
                return fetch(request).then(networkResponse => {
                    // Cache the successful response for future
                    if (networkResponse && networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(request, responseClone);
                        });
                    }
                    return networkResponse;
                }).catch(() => {
                    // Network failed and not in cache - return offline page for HTML
                    if (request.headers.get('Accept') && 
                        request.headers.get('Accept').includes('text/html')) {
                        return caches.match(OFFLINE_URL);
                    }
                    // Return error response for other resources
                    return new Response('Offline', {
                        status: 503,
                        statusText: 'Service Unavailable'
                    });
                });
            })
    );
});

// Handle push notifications (optional)
self.addEventListener('push', event => {
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: 'BBS Update', body: event.data.text() };
        }
    }
    
    const options = {
        body: data.body || 'New update available',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/'
        }
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'BBS Badge System', options)
    );
});

// Handle notification click
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(windowClients => {
            // Check if there's already a window/tab open with the target URL
            for (let client of windowClients) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            // If not, open a new window/tab
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Handle messages from the main thread
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
