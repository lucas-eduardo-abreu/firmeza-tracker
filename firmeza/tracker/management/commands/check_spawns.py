"""
Checks all spawn records for status transitions and sends push notifications.
Run every minute via cron: python manage.py check_spawns
"""
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from firmeza.tracker.models import SpawnRecord, PushSubscription


def send_push(subscription, title, body, icon=None, image=None):
    import logging
    log = logging.getLogger(__name__)
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps({'title': title, 'body': body, 'icon': icon, 'image': image}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
        )
        return 'ok'
    except Exception as e:
        status = getattr(getattr(e, 'response', None), 'status_code', None)
        if status in (401, 404, 410):
            log.warning('Subscription invalid (%s), deleting: %s', status, subscription.endpoint[:60])
            return 'expired'
        log.error('send_push failed for %s: %s', subscription.endpoint[:60], e)
        return 'error'


class Command(BaseCommand):
    help = 'Check spawn records for transitions and send push notifications'

    def handle(self, *args, **options):
        if not settings.VAPID_PRIVATE_KEY:
            self.stdout.write('VAPID_PRIVATE_KEY not set, skipping.')
            return

        base_url = f'https://{settings.ALLOWED_HOSTS[0]}' if settings.ALLOWED_HOSTS else 'http://localhost'
        sent = 0
        failed = 0

        now = timezone.now()
        deleted = 0
        for record in list(SpawnRecord.objects.select_related('config')):
            if record.status == 'overdue':
                if (now - record.next_spawn_max).total_seconds() > 3600:
                    record.delete()
                    deleted += 1
        if deleted:
            self.stdout.write(f'Removidos {deleted} registros com overdue > 1h.')

        for record in SpawnRecord.objects.select_related('config__boss', 'config__map'):
            status = record.status

            if status == record.last_notified_status:
                continue
            if status not in ('window', 'overdue'):
                record.last_notified_status = status
                record.save(update_fields=['last_notified_status'])
                continue

            boss = record.config.boss
            map_name = record.config.map.name
            server = record.server_number
            idx = f' #{record.monster_index}' if record.config.monsters_per_server > 1 else ''
            icon = f'{base_url}/static/bosses/{boss.gif_filename}' if boss.gif_filename else None

            if status == 'window':
                title = f'\u26a0\ufe0f {boss.name} \u2014 Possivelmente vivo!'
                body = f'{map_name} \u00b7 S{server}{idx}'
            else:
                title = f'\U0001f7e2 {boss.name} \u2014 VIVO!'
                body = f'{map_name} \u00b7 S{server}{idx} \u00b7 Mate agora!'

            self.stdout.write(f'Notificando: {boss.name} S{server}{idx} [{status}]')

            for sub in PushSubscription.objects.all():
                self.stdout.write(f'  → endpoint: {sub.endpoint[:60]}')
                result = send_push(sub, title, body, icon=icon, image=icon)
                if result == 'ok':
                    sent += 1
                elif result == 'expired':
                    sub.delete()
                else:
                    failed += 1

            record.last_notified_status = status
            record.save(update_fields=['last_notified_status'])

        self.stdout.write(f'check_spawns: {sent} enviadas, {failed} falhas.')
