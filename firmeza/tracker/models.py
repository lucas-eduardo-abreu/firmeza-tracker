from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Boss(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to='bosses/', blank=True, null=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Map(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BossSpawnConfig(models.Model):
    boss = models.ForeignKey(Boss, on_delete=models.CASCADE, related_name='spawn_configs')
    map = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='spawn_configs')
    monsters_per_server = models.PositiveSmallIntegerField(default=1)
    server_count = models.PositiveSmallIntegerField(default=1)
    respawn_min_hours = models.DecimalField(max_digits=5, decimal_places=2)
    respawn_max_hours = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('boss', 'map')
        ordering = ['boss__name', 'map__name']

    def __str__(self):
        return f"{self.boss.name} — {self.map.name}"


class SpawnRecord(models.Model):
    config = models.ForeignKey(BossSpawnConfig, on_delete=models.CASCADE, related_name='records')
    server_number = models.PositiveSmallIntegerField()
    monster_index = models.PositiveSmallIntegerField(default=1)
    last_death = models.DateTimeField()
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='spawn_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('config', 'server_number', 'monster_index')
        ordering = ['config__boss__name', 'server_number', 'monster_index']

    def __str__(self):
        return f"{self.config} S{self.server_number} #{self.monster_index}"

    @property
    def next_spawn_min(self):
        delta = timedelta(hours=float(self.config.respawn_min_hours))
        return self.last_death + delta

    @property
    def next_spawn_max(self):
        delta = timedelta(hours=float(self.config.respawn_max_hours))
        return self.last_death + delta

    @property
    def status(self):
        now = timezone.now()
        if now < self.next_spawn_min:
            return 'waiting'
        elif now <= self.next_spawn_max:
            return 'window'
        else:
            return 'overdue'
