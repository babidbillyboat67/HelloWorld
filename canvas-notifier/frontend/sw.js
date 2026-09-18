// Service worker: makes the app installable and turns incoming Web Push
// messages into an actual phone notification.

const CACHE_NAME = "canvas-notifier-v1";
const CORE_ASSETS = ["./", "./index.html", "./styles.css", "./app.js", "./manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "Canvas Notifier", body: "You have an assignment coming due." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (err) {
      payload.body = event.data.text();
    }
  }

  const options = {
    body: payload.body,
    icon: "icons/icon-192.png",
    badge: "icons/icon-192.png",
    data: { url: payload.url || "./" },
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "./";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});
