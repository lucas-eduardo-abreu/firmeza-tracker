import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import Boss, Map, BossSpawnConfig, SpawnRecord, PushSubscription
from .forms import LoginForm, SpawnRecordForm


# ── Helpers ───────────────────────────────────────────────────

def make_config(boss_name='Borgar', map_name='Shadow Abyss',
                monsters=1, servers=3, rmin=2.0, rmax=3.0):
    boss, _ = Boss.objects.get_or_create(name=boss_name, defaults={'gif_filename': f'{boss_name}.gif'})
    map_obj, _ = Map.objects.get_or_create(name=map_name)
    config, _ = BossSpawnConfig.objects.get_or_create(
        boss=boss, map=map_obj,
        defaults={'monsters_per_server': monsters, 'server_count': servers,
                  'respawn_min_hours': rmin, 'respawn_max_hours': rmax},
    )
    return config


def make_record(config, user, server=1, index=1, hours_ago=5):
    return SpawnRecord.objects.create(
        config=config,
        server_number=server,
        monster_index=index,
        last_death=timezone.now() - timedelta(hours=hours_ago),
        reported_by=user,
    )


# ── Model tests ───────────────────────────────────────────────

class BossModelTest(TestCase):
    def test_str(self):
        boss = Boss(name='Borgar')
        self.assertEqual(str(boss), 'Borgar')

    def test_ordering_by_display_order(self):
        Boss.objects.create(name='Z', display_order=1)
        Boss.objects.create(name='A', display_order=2)
        names = list(Boss.objects.values_list('name', flat=True))
        self.assertEqual(names, ['Z', 'A'])


class MapModelTest(TestCase):
    def test_str(self):
        m = Map(name='Shadow Abyss')
        self.assertEqual(str(m), 'Shadow Abyss')


class BossSpawnConfigModelTest(TestCase):
    def setUp(self):
        self.config = make_config()

    def test_str(self):
        self.assertIn('Borgar', str(self.config))
        self.assertIn('Shadow Abyss', str(self.config))


class SpawnRecordModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', password='pass')
        self.config = make_config(rmin=2.0, rmax=4.0)

    def test_str(self):
        record = make_record(self.config, self.user, server=2, index=1, hours_ago=1)
        self.assertIn('S2', str(record))
        self.assertIn('#1', str(record))

    def test_next_spawn_min(self):
        death = timezone.now() - timedelta(hours=1)
        record = SpawnRecord(config=self.config, server_number=1, monster_index=1, last_death=death)
        expected = death + timedelta(hours=2)
        self.assertAlmostEqual(record.next_spawn_min.timestamp(), expected.timestamp(), delta=1)

    def test_next_spawn_max(self):
        death = timezone.now() - timedelta(hours=1)
        record = SpawnRecord(config=self.config, server_number=1, monster_index=1, last_death=death)
        expected = death + timedelta(hours=4)
        self.assertAlmostEqual(record.next_spawn_max.timestamp(), expected.timestamp(), delta=1)

    def test_status_waiting(self):
        # Died 30 min ago, min respawn is 2h → still waiting
        record = make_record(self.config, self.user, hours_ago=0.5)
        self.assertEqual(record.status, 'waiting')

    def test_status_window(self):
        # Died 3h ago, window is 2h–4h → in window
        record = make_record(self.config, self.user, hours_ago=3)
        self.assertEqual(record.status, 'window')

    def test_status_overdue(self):
        # Died 5h ago, max respawn is 4h → overdue
        record = make_record(self.config, self.user, hours_ago=5)
        self.assertEqual(record.status, 'overdue')


# ── Form tests ────────────────────────────────────────────────

class LoginFormTest(TestCase):
    def test_valid(self):
        form = LoginForm(data={'username': 'user', 'password': 'pass'})
        self.assertTrue(form.is_valid())

    def test_missing_username(self):
        form = LoginForm(data={'username': '', 'password': 'pass'})
        self.assertFalse(form.is_valid())

    def test_missing_password(self):
        form = LoginForm(data={'username': 'user', 'password': ''})
        self.assertFalse(form.is_valid())


class SpawnRecordFormTest(TestCase):
    def test_valid_with_datetime(self):
        form = SpawnRecordForm(data={'death_time': '2025-01-01 12:00:00'})
        self.assertTrue(form.is_valid())

    def test_valid_empty(self):
        form = SpawnRecordForm(data={'death_time': ''})
        self.assertTrue(form.is_valid())


# ── View tests ────────────────────────────────────────────────

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('player', password='pass123')

    def test_get_renders_form(self):
        r = self.client.get(reverse('login'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'FIRMEZA')

    def test_authenticated_user_redirected(self):
        self.client.login(username='player', password='pass123')
        r = self.client.get(reverse('login'))
        self.assertRedirects(r, reverse('dashboard'))

    def test_valid_login_redirects(self):
        r = self.client.post(reverse('login'), {'username': 'player', 'password': 'pass123'})
        self.assertRedirects(r, reverse('dashboard'))

    def test_invalid_login_shows_error(self):
        r = self.client.post(reverse('login'), {'username': 'player', 'password': 'wrong'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'incorretos')

    def test_invalid_form_rerenders(self):
        r = self.client.post(reverse('login'), {'username': '', 'password': ''})
        self.assertEqual(r.status_code, 200)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass123')
        self.client.login(username='player', password='pass123')

    def test_logout_redirects(self):
        r = self.client.post(reverse('logout'))
        self.assertRedirects(r, reverse('login'))


class DashboardViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass123')
        self.superuser = User.objects.create_superuser('admin', password='admin123')
        self.config = make_config(servers=3)
        self.client.login(username='player', password='pass123')

    def test_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse('dashboard'))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_renders_dashboard(self):
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Borgar')

    def test_filter_by_map(self):
        map_id = Map.objects.get(name='Shadow Abyss').id
        r = self.client.get(reverse('dashboard'), {'map': map_id})
        self.assertEqual(r.status_code, 200)

    def test_filter_by_boss(self):
        boss_id = Boss.objects.get(name='Borgar').id
        r = self.client.get(reverse('dashboard'), {'boss': boss_id})
        self.assertEqual(r.status_code, 200)

    def test_filter_by_server(self):
        r = self.client.get(reverse('dashboard'), {'server': 2})
        self.assertEqual(r.status_code, 200)

    def test_filter_server_excludes_configs(self):
        # Server 5 → config with server_count=3 should be excluded
        r = self.client.get(reverse('dashboard'), {'server': 5})
        self.assertEqual(len(r.context['data']), 0)

    def test_can_edit_own_record(self):
        make_record(self.config, self.user)
        r = self.client.get(reverse('dashboard'))
        monster = r.context['data'][0]['servers'][0]['monsters'][0]
        self.assertTrue(monster['can_edit'])

    def test_cannot_edit_other_user_record(self):
        other = User.objects.create_user('other', password='pass')
        make_record(self.config, other)
        r = self.client.get(reverse('dashboard'))
        monster = r.context['data'][0]['servers'][0]['monsters'][0]
        self.assertFalse(monster['can_edit'])

    def test_superuser_can_edit_any_record(self):
        other = User.objects.create_user('other', password='pass')
        make_record(self.config, other)
        self.client.login(username='admin', password='admin123')
        r = self.client.get(reverse('dashboard'))
        monster = r.context['data'][0]['servers'][0]['monsters'][0]
        self.assertTrue(monster['can_edit'])

    def test_no_record_can_edit(self):
        r = self.client.get(reverse('dashboard'))
        monster = r.context['data'][0]['servers'][0]['monsters'][0]
        self.assertTrue(monster['can_edit'])

    def test_no_configs_shows_empty(self):
        BossSpawnConfig.objects.all().delete()
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.context['data'], [])

    def test_server_range_in_context(self):
        r = self.client.get(reverse('dashboard'))
        server_range = list(r.context['server_range'])
        self.assertIn(1, server_range)
        self.assertIn(3, server_range)


class RecordDeathViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass123')
        self.other = User.objects.create_user('other', password='pass123')
        self.superuser = User.objects.create_superuser('admin', password='admin123')
        self.config = make_config()
        self.client.login(username='player', password='pass123')

    def _post(self, data=None):
        payload = {'config_id': self.config.id, 'server_number': 1, 'monster_index': 1}
        if data:
            payload.update(data)
        return self.client.post(reverse('record_death'), payload)

    def test_requires_login(self):
        self.client.logout()
        r = self._post()
        self.assertEqual(r.status_code, 302)

    def test_get_not_allowed(self):
        r = self.client.get(reverse('record_death'))
        self.assertEqual(r.status_code, 405)

    def test_creates_record_without_death_time(self):
        r = self._post()
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn('id', data)
        self.assertEqual(data['reported_by'], 'player')
        self.assertTrue(SpawnRecord.objects.exists())

    def test_creates_record_with_death_time(self):
        r = self._post({'death_time': '2025-06-01T10:00'})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn('2025-06-01', data['last_death'])

    def test_creates_record_with_aware_death_time(self):
        r = self._post({'death_time': '2025-06-01T10:00:00+00:00'})
        self.assertEqual(r.status_code, 200)

    def test_updates_existing_own_record(self):
        make_record(self.config, self.user)
        r = self._post({'death_time': '2025-06-01T10:00'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SpawnRecord.objects.count(), 1)

    def test_cannot_update_other_user_record(self):
        make_record(self.config, self.other)
        r = self._post()
        self.assertEqual(r.status_code, 403)

    def test_superuser_can_update_any_record(self):
        make_record(self.config, self.other)
        self.client.login(username='admin', password='admin123')
        r = self._post()
        self.assertEqual(r.status_code, 200)

    def test_404_on_invalid_config(self):
        r = self.client.post(reverse('record_death'),
                             {'config_id': 9999, 'server_number': 1, 'monster_index': 1})
        self.assertEqual(r.status_code, 404)

    def test_response_contains_spawn_times(self):
        r = self._post()
        data = json.loads(r.content)
        self.assertIn('next_spawn_min', data)
        self.assertIn('next_spawn_max', data)
        self.assertIn('status', data)


class DeleteRecordViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass123')
        self.other = User.objects.create_user('other', password='pass123')
        self.superuser = User.objects.create_superuser('admin', password='admin123')
        self.config = make_config()
        self.client.login(username='player', password='pass123')

    def test_requires_login(self):
        record = make_record(self.config, self.user)
        self.client.logout()
        r = self.client.post(reverse('delete_record', args=[record.id]))
        self.assertEqual(r.status_code, 302)

    def test_get_not_allowed(self):
        record = make_record(self.config, self.user)
        r = self.client.get(reverse('delete_record', args=[record.id]))
        self.assertEqual(r.status_code, 405)

    def test_owner_can_delete(self):
        record = make_record(self.config, self.user)
        r = self.client.post(reverse('delete_record', args=[record.id]))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SpawnRecord.objects.filter(id=record.id).exists())

    def test_other_user_cannot_delete(self):
        record = make_record(self.config, self.other)
        r = self.client.post(reverse('delete_record', args=[record.id]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(SpawnRecord.objects.filter(id=record.id).exists())

    def test_superuser_can_delete_any(self):
        record = make_record(self.config, self.other)
        self.client.login(username='admin', password='admin123')
        r = self.client.post(reverse('delete_record', args=[record.id]))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SpawnRecord.objects.filter(id=record.id).exists())

    def test_404_on_invalid_record(self):
        r = self.client.post(reverse('delete_record', args=[9999]))
        self.assertEqual(r.status_code, 404)


# ── PushSubscription model tests ─────────────────────────────

class PushSubscriptionModelTest(TestCase):
    def test_str(self):
        user = User.objects.create_user('player', password='pass')
        sub = PushSubscription(user=user, endpoint='https://push.example.com/abc', p256dh='x', auth='y')
        self.assertIn('player', str(sub))


# ── Push API view tests ───────────────────────────────────────

class PushViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass')
        self.client.login(username='player', password='pass')
        self.sub_payload = {
            'endpoint': 'https://push.example.com/test',
            'keys': {'p256dh': 'abc123', 'auth': 'xyz'},
        }

    def test_vapid_key_returns_public_key(self):
        with self.settings(VAPID_PUBLIC_KEY='test-public-key'):
            r = self.client.get(reverse('push_vapid_key'))
            self.assertEqual(r.status_code, 200)
            self.assertEqual(json.loads(r.content)['publicKey'], 'test-public-key')

    def test_subscribe_creates_subscription(self):
        r = self.client.post(
            reverse('push_subscribe'),
            data=json.dumps(self.sub_payload),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(endpoint=self.sub_payload['endpoint']).exists())

    def test_subscribe_upserts_existing(self):
        self.client.post(reverse('push_subscribe'),
                         data=json.dumps(self.sub_payload), content_type='application/json')
        self.client.post(reverse('push_subscribe'),
                         data=json.dumps(self.sub_payload), content_type='application/json')
        self.assertEqual(PushSubscription.objects.count(), 1)

    def test_unsubscribe_removes_subscription(self):
        PushSubscription.objects.create(
            user=self.user, endpoint=self.sub_payload['endpoint'], p256dh='x', auth='y')
        r = self.client.post(
            reverse('push_unsubscribe'),
            data=json.dumps({'endpoint': self.sub_payload['endpoint']}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PushSubscription.objects.exists())

    def test_requires_login(self):
        self.client.logout()
        r = self.client.post(reverse('push_subscribe'),
                             data=json.dumps(self.sub_payload), content_type='application/json')
        self.assertEqual(r.status_code, 302)


# ── check_spawns command tests ────────────────────────────────

class CheckSpawnsCommandTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('player', password='pass')
        self.config = make_config(rmin=2.0, rmax=4.0)
        self.sub = PushSubscription.objects.create(
            user=self.user, endpoint='https://push.example.com/x', p256dh='p', auth='a')

    def test_skips_when_no_vapid_key(self):
        out = StringIO()
        with self.settings(VAPID_PRIVATE_KEY=''):
            call_command('check_spawns', stdout=out)
        self.assertIn('not set', out.getvalue())

    def test_no_notifications_when_status_unchanged(self):
        record = make_record(self.config, self.user, hours_ago=0.5)  # waiting
        record.last_notified_status = 'waiting'
        record.save()
        out = StringIO()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=out)
            mock_send.assert_not_called()
        self.assertIn('0 enviadas', out.getvalue())

    def test_sends_notification_on_window_transition(self):
        record = make_record(self.config, self.user, hours_ago=3)  # window
        record.last_notified_status = 'waiting'
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=StringIO())
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertIn('Possivelmente', args[1])

    def test_sends_notification_on_overdue_transition(self):
        record = make_record(self.config, self.user, hours_ago=5)  # overdue
        record.last_notified_status = 'window'
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=StringIO())
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertIn('VIVO', args[1])

    def test_updates_last_notified_status(self):
        record = make_record(self.config, self.user, hours_ago=3)  # window
        record.last_notified_status = 'waiting'
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push'):
            call_command('check_spawns', stdout=StringIO())
        record.refresh_from_db()
        self.assertEqual(record.last_notified_status, 'window')

    def test_updates_status_to_waiting_without_sending(self):
        record = make_record(self.config, self.user, hours_ago=0.5)  # waiting
        record.last_notified_status = ''
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=StringIO())
            mock_send.assert_not_called()
        record.refresh_from_db()
        self.assertEqual(record.last_notified_status, 'waiting')

    def test_multi_monster_body_includes_index(self):
        config = make_config(boss_name='Draviel', monsters=10, servers=3, rmin=2.0, rmax=4.0)
        record = make_record(config, self.user, hours_ago=3)
        record.last_notified_status = 'waiting'
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=StringIO())
            args = mock_send.call_args[0]
            self.assertIn('#1', args[2])

    def test_icon_uses_boss_gif(self):
        record = make_record(self.config, self.user, hours_ago=3)
        record.last_notified_status = 'waiting'
        record.save()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push') as mock_send:
            call_command('check_spawns', stdout=StringIO())
            kwargs = mock_send.call_args[1]
            self.assertIn('Borgar.gif', kwargs['icon'])

    def test_send_push_returns_true_on_success(self):
        from firmeza.tracker.management.commands.check_spawns import send_push
        with patch('pywebpush.webpush', return_value=None):
            result = send_push(self.sub, 'title', 'body')
        self.assertTrue(result)

    def test_send_push_returns_error_on_exception(self):
        from firmeza.tracker.management.commands.check_spawns import send_push
        with self.settings(VAPID_PRIVATE_KEY='bad-key'):
            result = send_push(self.sub, 'title', 'body')
        self.assertEqual(result, 'error')

    def test_failed_counter_when_send_fails(self):
        record = make_record(self.config, self.user, hours_ago=3)
        record.last_notified_status = 'waiting'
        record.save()
        out = StringIO()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push', return_value='error'):
            call_command('check_spawns', stdout=out)
        self.assertIn('1 falhas', out.getvalue())

    def test_output_shows_sent_and_failed(self):
        record = make_record(self.config, self.user, hours_ago=3)
        record.last_notified_status = 'waiting'
        record.save()
        out = StringIO()
        with self.settings(VAPID_PRIVATE_KEY='key', ALLOWED_HOSTS=['example.com']), \
             patch('firmeza.tracker.management.commands.check_spawns.send_push', return_value='ok'):
            call_command('check_spawns', stdout=out)
        self.assertIn('enviadas', out.getvalue())


# ── Seed command tests ────────────────────────────────────────

class SeedCommandTest(TestCase):
    def test_seed_creates_bosses_and_configs(self):
        out = StringIO()
        call_command('seed', stdout=out)
        self.assertGreater(Boss.objects.count(), 0)
        self.assertGreater(BossSpawnConfig.objects.count(), 0)
        self.assertIn('Seed concluído', out.getvalue())

    def test_seed_idempotent(self):
        call_command('seed', stdout=StringIO())
        boss_count = Boss.objects.count()
        config_count = BossSpawnConfig.objects.count()
        call_command('seed', stdout=StringIO())
        self.assertEqual(Boss.objects.count(), boss_count)
        self.assertEqual(BossSpawnConfig.objects.count(), config_count)

    def test_seed_updates_display_order(self):
        call_command('seed', stdout=StringIO())
        Boss.objects.filter(name='Borgar').update(display_order=999)
        call_command('seed', stdout=StringIO())
        self.assertEqual(Boss.objects.get(name='Borgar').display_order, 10)

    def test_seed_updates_gif_filename(self):
        call_command('seed', stdout=StringIO())
        Boss.objects.filter(name='Borgar').update(gif_filename='wrong.gif')
        call_command('seed', stdout=StringIO())
        self.assertEqual(Boss.objects.get(name='Borgar').gif_filename, 'Borgar.gif')
