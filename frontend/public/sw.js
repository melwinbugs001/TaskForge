/* global self */

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { body: event.data?.text() ?? "You have a task update." };
  }

  const title = payload.title || "Task update";
  const options = {
    body: payload.body || "There is an update to one of your tasks.",
    tag: payload.tag,
    renotify: false,
    data: { url: payload.url || "/" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const destination = new URL(event.notification.data?.url || "/", self.location.origin);
  if (destination.origin !== self.location.origin) return;

  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true })
    .then((clients) => {
      const existing = clients.find((client) => new URL(client.url).origin === self.location.origin);
      if (existing) {
        return existing.navigate(destination.href).then(() => existing.focus());
      }
      return self.clients.openWindow(destination.href);
    }));
});