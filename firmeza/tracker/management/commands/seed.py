"""
Management command to seed boss and spawn configuration data.
Run with: python manage.py seed
"""
from django.core.management.base import BaseCommand
from firmeza.tracker.models import Boss, Map, BossSpawnConfig


# (boss_name, gif_filename, display_order, map_name, monsters_per_server, server_count, respawn_min_h, respawn_max_h)
BOSS_DATA = [
    ('Borgar',        'Borgar.gif',        10,  'Shadow Abyss',     1,  3, 2.0,  3.0),
    ('Dreadhorn',     'Dreadhorn.gif',     20,  'Shadow Abyss',     2,  3, 1.0,  2.0),
    ('Moltragron',    'Moltragron.gif',    30,  'Shadow Abyss',     2,  3, 1.0,  2.0),
    ('Red Dragon',    'Red Dragon.gif',    35,  'Shadow Abyss',     1,  3, 2.5,  2.5),
    ('Kharzul',       'Kharzul.gif',       40,  'Ruined Lorencia',  3,  1, 3.0,  4.0),
    ('Kharzul',       'Kharzul.gif',       40,  'Shadow Abyss',     1,  3, 3.0,  4.0),
    ('Vescrya',       'Vescrya.gif',       50,  'Ruined Devias',    3,  1, 3.0,  4.0),
    ('Vescrya',       'Vescrya.gif',       50,  'Shadow Abyss',     1,  3, 3.0,  4.0),
    ('Muggron',       'Muggron.gif',       60,  'Shadow Abyss',     1,  3, 6.0,  6.0),
    ('Muggron',       'Muggron.gif',       60,  'Crywolf Fortress', 4,  1, 6.0,  6.0),
    ('Muggron',       'Muggron.gif',       60,  'Balgass Barracks', 4,  1, 6.0,  6.0),
    ('Draviel',       'Draviel.gif',       65,  'Aquilas Temple',   10, 3, 4.0,  6.0),
    ('Blue Goblin',   'Blue Goblin.gif',   70,  'Shadow Abyss',     3,  3, 10.0, 11.0),
    ('Red Goblin',    'Red Goblin.gif',    80,  'Shadow Abyss',     3,  3, 10.0, 11.0),
    ('Yellow Goblin', 'Yellow Goblin.gif', 90,  'Shadow Abyss',     3,  3, 10.0, 11.0),
    ('Skarnath',      'Skarnath.gif',      110, 'Kardamahal',       10, 8, 3.0,  4.0),
    ('Cursed Santa',  'Cursed Santa.gif',  120, 'Shadow Abyss',     1,  3, 10.0, 10.0),
    ('White Wizard',  'White Wizard.gif',  130, 'Shadow Abyss',     1,  3, 10.0, 10.0),
    ('Death King',    'Death King.gif',    140, 'Shadow Abyss',     1,  3, 10.0, 10.0),
    ('Cryonox',       'Cryonox.gif',       150, 'Twisted Karutan',  4,  3, 10.0, 10.0),
]


class Command(BaseCommand):
    help = 'Seed database with boss and spawn configuration data'

    def handle(self, *args, **options):
        created_bosses = 0
        created_configs = 0

        for row in BOSS_DATA:
            boss_name, gif_file, display_order, map_name, mps, sc, rmin, rmax = row

            boss, boss_created = Boss.objects.get_or_create(
                name=boss_name,
                defaults={'display_order': display_order, 'gif_filename': gif_file},
            )
            update_fields = []
            if boss.display_order != display_order:
                boss.display_order = display_order
                update_fields.append('display_order')
            if boss.gif_filename != gif_file:
                boss.gif_filename = gif_file
                update_fields.append('gif_filename')
            if update_fields:
                boss.save(update_fields=update_fields)

            if boss_created:
                created_bosses += 1

            map_obj, _ = Map.objects.get_or_create(name=map_name)

            _, cfg_created = BossSpawnConfig.objects.get_or_create(
                boss=boss,
                map=map_obj,
                defaults={
                    'monsters_per_server': mps,
                    'server_count': sc,
                    'respawn_min_hours': rmin,
                    'respawn_max_hours': rmax,
                }
            )
            if cfg_created:
                created_configs += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seed concluído: {created_bosses} bosses criados, {created_configs} configurações criadas.'
        ))
