self.addEventListener('push', function(event) {
  let data = { title: 'Firmeza Tracker', body: 'Boss spawn!', icon: null, image: null };
  try { data = event.data.json(); } catch(e) {}

  const options = {
    body: data.body,
    icon: data.icon || '/static/bosses/Borgar.gif',
    vibrate: [200, 100, 200],
    tag: data.title,
    renotify: true,
  };
  if (data.image) options.image = data.image;

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
