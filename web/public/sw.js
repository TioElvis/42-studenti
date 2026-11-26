/* Service worker for browser notifications (Web Push). It caches nothing. */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data?.json() ?? {};
  } catch {
    /* malformed payload: still show a generic notification */
  }
  event.waitUntil(
    self.registration.showNotification(data.title || "42 Studenti", {
      body: data.body,
      tag: data.tag,
      data: { url: data.url || "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let url = new URL(event.notification.data?.url || "/", self.location.origin);
  // Only ever open pages of this app.
  if (url.origin !== self.location.origin) url = new URL("/", self.location.origin);

  event.waitUntil(
    (async () => {
      const [client] = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      if (client) {
        try {
          await client.focus();
          await client.navigate(url.href);
          return;
        } catch {
          /* a tab this worker doesn't control: open a new one */
        }
      }
      await self.clients.openWindow(url.href);
    })(),
  );
});
