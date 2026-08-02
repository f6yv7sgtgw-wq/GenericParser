const CACHE="generic-parser-mobile-0.34";
const ASSETS=["./","./app.css?v=0.34","./app.js?v=0.34","./manifest.webmanifest?v=0.34","./icons/icon.svg"];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=="GET"||url.pathname.includes("/api/"))return;
  event.respondWith(fetch(event.request,{cache:"no-store"}).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}
    return response;
  }).catch(async()=>await caches.match(event.request)||await caches.match("./")));
});
