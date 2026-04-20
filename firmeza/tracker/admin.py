from django.contrib import admin
from .models import Boss, Map, BossSpawnConfig, SpawnRecord, PushSubscription


@admin.register(Boss)
class BossAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Map)
class MapAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(BossSpawnConfig)
class BossSpawnConfigAdmin(admin.ModelAdmin):
    list_display = ('boss', 'map', 'monsters_per_server', 'server_count', 'respawn_min_hours', 'respawn_max_hours')
    list_filter = ('boss', 'map')


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint_short', 'created_at')

    def endpoint_short(self, obj):
        return obj.endpoint[:60]
    endpoint_short.short_description = 'endpoint'


@admin.register(SpawnRecord)
class SpawnRecordAdmin(admin.ModelAdmin):
    list_display = ('config', 'server_number', 'monster_index', 'last_death', 'reported_by', 'updated_at')
    list_filter = ('config__boss', 'config__map')
    search_fields = ('reported_by__username',)
    readonly_fields = ('created_at', 'updated_at')
