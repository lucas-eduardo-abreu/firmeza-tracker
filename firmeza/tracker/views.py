from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Boss, Map, BossSpawnConfig, SpawnRecord
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

    if selected_map:
        configs = configs.filter(map__id=selected_map)
    if selected_boss:
        configs = configs.filter(boss__id=selected_boss)

    data = []
    for config in configs:
        servers = []
        for s in range(1, config.server_count + 1):
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
def delete_record(request, record_id):
    record = get_object_or_404(SpawnRecord, id=record_id)
    if not request.user.is_superuser and record.reported_by != request.user:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    record.delete()
    return JsonResponse({'ok': True})
