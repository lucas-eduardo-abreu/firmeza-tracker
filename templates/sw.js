self.addEventListener('push', function(event) {
  let data = { title: 'Firmeza Tracker', body: 'Boss spawn!', icon: null };
  try { data = event.data.json(); } catch(e) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/static/bosses/Borgar.gif',
      vibrate: [200, 100, 200],
      tag: data.title,
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
