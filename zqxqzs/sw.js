const CACHE = 'meal-v3';
const FILES = ['/zqxqzs/', '/zqxqzs/index.html', '/zqxqzs/styles.css', '/zqxqzs/app.js', '/zqxqzs/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
