"""
Checks all spawn records for status transitions and sends push notifications.
Run every minute via cron: python manage.py check_spawns
"""
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from firmeza.tracker.models import SpawnRecord, PushSubscription


def send_push(subscription, title, body, icon=None):
    try:
        from pywebpush import webpush
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps({'title': title, 'body': body, 'icon': icon}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
        )
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('send_push failed for %s: %s', subscription.endpoint[:60], e)
        return False


class Command(BaseCommand):
    help = 'Check spawn records for transitions and send push notifications'

    def handle(self, *args, **options):
        if not settings.VAPID_PRIVATE_KEY:
            self.stdout.write('VAPID_PRIVATE_KEY not set, skipping.')
            return

        base_url = f'https://{settings.ALLOWED_HOSTS[0]}' if settings.ALLOWED_HOSTS else 'http://localhost'
        sent = 0
        failed = 0

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
                title = f'⚠️ {boss.name} — Possivelmente vivo!'
                body = f'{map_name} · S{server}{idx}'
            else:
                title = f'🟢 {boss.name} — VIVO!'
                body = f'{map_name} · S{server}{idx} · Mate agora!'

            self.stdout.write(f'Notificando: {title} | {body}')

            for sub in PushSubscription.objects.all():
                self.stdout.write(f'  → endpoint: {sub.endpoint[:60]}')
                if send_push(sub, title, body, icon=icon):
                    sent += 1
                else:
                    failed += 1

            record.last_notified_status = status
            record.save(update_fields=['last_notified_status'])

        self.stdout.write(f'check_spawns: {sent} enviadas, {failed} falhas.')
