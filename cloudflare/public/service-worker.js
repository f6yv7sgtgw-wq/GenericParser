const CACHE = 'generic-parser-mobile-gp-192';
const ASSETS = [
  "./",
  "./eventlog.html",
  "./favorites.html",
  "./release-identity.json",
  "./app.css",
  "./layout-0409.css",
  "./compact-04362.css",
  "./cards-0440.css",
  "./traffic-light-0443.css",
  "./source-colors-110.css",
  "./source-colors-140.css",
  "./ui-133.css",
  "./ui-134.css",
  "./ui-150.css",
  "./ui-151.css",
  "./ui-160.css",
  "./ui-161.css",
  "./ui-162.css",
  "./ui-180.css",
  "./build-identity-0450.js",
  "./favorites-store-150.js",
  "./favorites-150.js",
  "./app.js",
  "./controller-0450.js",
  "./controller-0411.js?v=runtime-reference",
  "./vinted-background-132.js",
  "./module-debug-0450.js",
  "./auto-resume-0450.js",
  "./source-colors-110.js",
  "./source-colors-140.js",
  "./ui-160.js",
  "./ui-180.js",
  "./eventlog-187.js",
  "./eventlog-writer-188.js",
  "./auto-resume-04462.js",
  "./controller-0411.js",
  "./eventlog-0450.js",
  "./manifest.webmanifest",
  "./icons/icon.svg"
];

const isDynamicRequest = url => (
  url.pathname.startsWith('/api/') ||
  ['/health', '/version', '/diagnostics', '/search'].includes(url.pathname)
);

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || isDynamicRequest(url)) return;

  const isNavigation = event.request.mode === 'navigate';
  event.respondWith(
    fetch(event.request, {cache: 'no-store'})
      .then(response => {
        if (response.ok) {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy)));
        }
        return response;
      })
      .catch(async () => {
        const exact = await caches.match(event.request, {ignoreSearch: true});
        if (exact) return exact;
        if (isNavigation) return await caches.match('./');
        return Response.error();
      })
  );
});
