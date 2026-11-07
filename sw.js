/* Service worker: cache app shell + lazy-cached page images for offline reading */
const CACHE = 'cet6-v2';
const SHELL = ['./','./index.html','./style.css','./app.js','./manifest.webmanifest','./img/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // page images: cache-first, then network, then cache-put
  if (url.pathname.includes('/img/')){
    e.respondWith(
      caches.open(CACHE).then(async c => {
        const hit = await c.match(req);
        if (hit) return hit;
        try {
          const res = await fetch(req);
          if (res && res.ok) c.put(req, res.clone());
          return res;
        } catch (err) {
          return hit || Response.error();
        }
      })
    );
    return;
  }
  // shell: stale-while-revalidate
  e.respondWith(
    caches.open(CACHE).then(async c => {
      const hit = await c.match(req);
      const net = fetch(req).then(res => { if (res && res.ok) c.put(req, res.clone()); return res; })
                            .catch(()=>hit);
      return hit || net;
    })
  );
});
