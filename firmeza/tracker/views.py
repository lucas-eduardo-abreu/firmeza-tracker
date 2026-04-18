import json
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Boss, Map, BossSpawnConfig, SpawnRecord, PushSubscription
from .forms import LoginForm, SpawnRecordForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Usuário ou senha incorretos.')
    return render(request, 'tracker/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    configs = BossSpawnConfig.objects.select_related('boss', 'map').order_by('boss__display_order', 'boss__name', 'map__name')
    selected_map = request.GET.get('map', '')
    selected_boss = request.GET.get('boss', '')
    selected_server = request.GET.get('server', '')

    if selected_map:
        configs = configs.filter(map__id=selected_map)
    if selected_boss:
        configs = configs.filter(boss__id=selected_boss)
    if selected_server:
        configs = configs.filter(server_count__gte=selected_server)

    max_servers = BossSpawnConfig.objects.aggregate(m=models.Max('server_count'))['m'] or 1

    data = []
    for config in configs:
        server_range = range(1, config.server_count + 1)
        if selected_server:
            server_range = [int(selected_server)]
        servers = []
        for s in server_range:
            monsters = []
            for m in range(1, config.monsters_per_server + 1):
                record = SpawnRecord.objects.filter(
                    config=config, server_number=s, monster_index=m
                ).first()
                can_edit = (
                    request.user.is_superuser or
                    record is None or
                    (record and record.reported_by == request.user)
                )
                monsters.append({
                    'index': m,
                    'record': record,
                    'can_edit': can_edit,
                })
            servers.append({'number': s, 'monsters': monsters})
        data.append({'config': config, 'servers': servers})

    maps = Map.objects.all()
    bosses = Boss.objects.all()
    return render(request, 'tracker/dashboard.html', {
        'data': data,
        'maps': maps,
        'bosses': bosses,
        'selected_map': selected_map,
        'selected_boss': selected_boss,
        'selected_server': selected_server,
        'server_range': range(1, max_servers + 1),
    })


@login_required
@require_POST
def record_death(request):
    config_id = request.POST.get('config_id')
    server_number = int(request.POST.get('server_number'))
    monster_index = int(request.POST.get('monster_index'))
    death_time_str = request.POST.get('death_time')

    config = get_object_or_404(BossSpawnConfig, id=config_id)

    record = SpawnRecord.objects.filter(
        config=config, server_number=server_number, monster_index=monster_index
    ).first()

    if record and not request.user.is_superuser and record.reported_by != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)

    from django.utils.dateparse import parse_datetime
    if death_time_str:
        death_time = parse_datetime(death_time_str)
        if death_time and timezone.is_naive(death_time):
            death_time = timezone.make_aware(death_time)
    else:
        death_time = timezone.now()

    if record:
        record.last_death = death_time
        record.reported_by = request.user
        record.save()
    else:
        record = SpawnRecord.objects.create(
            config=config,
            server_number=server_number,
            monster_index=monster_index,
            last_death=death_time,
            reported_by=request.user,
        )

    return JsonResponse({
        'id': record.id,
        'last_death': record.last_death.isoformat(),
        'next_spawn_min': record.next_spawn_min.isoformat(),
        'next_spawn_max': record.next_spawn_max.isoformat(),
        'status': record.status,
        'reported_by': record.reported_by.username,
    })


@login_required
@require_POST
def push_subscribe(request):
    data = json.loads(request.body)
    endpoint = data['endpoint']
    p256dh = data['keys']['p256dh']
    auth = data['keys']['auth']
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def push_unsubscribe(request):
    data = json.loads(request.body)
    PushSubscription.objects.filter(endpoint=data.get('endpoint')).delete()
    return JsonResponse({'ok': True})


@login_required
def push_vapid_key(request):
    return JsonResponse({'publicKey': settings.VAPID_PUBLIC_KEY})


@login_required
@require_POST
def delete_record(request, record_id):
    record = get_object_or_404(SpawnRecord, id=record_id)
    if not request.user.is_superuser and record.reported_by != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    record.delete()
    return JsonResponse({'ok': True})
