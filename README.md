# firmeza-tracker

![Tests](https://github.com/lucas-eduardo-abreu/firmeza-tracker/actions/workflows/tests.yml/badge.svg)
![Coverage](coverage.svg)

Boss spawn tracker for MU Dream (private server). Records kill timestamps and shows
each boss's current respawn window in real time, with browser push notifications when
a boss enters or passes its spawn window.

## Stack

- Python 3.12 · Django 5 · PostgreSQL · gunicorn
- Web Push (pywebpush + VAPID) · Render cron job

## Features

- Per-boss, per-server, per-monster spawn tracking
- Color-coded status: waiting / approaching / in window / overdue
- Kill registration with manual or automatic timestamp
- User-level permissions — each user edits only their own records; superusers have
  full access
- Filter by map and boss
- Browser push notifications when a boss enters or passes its spawn window
- Animated boss GIFs

## Status legend

| Status     | Meaning                                    |
|------------|--------------------------------------------|
| Blue       | No record yet                              |
| Red        | Dead — inside minimum respawn window       |
| Yellow     | Possibly alive — between min and max       |
| Green      | Overdue — past maximum respawn window      |

## Bosses

| Boss        | Map              | Servers | Monsters | Respawn  |
|-------------|------------------|---------|----------|----------|
| Borgar      | Shadow Abyss     | 3       | 1        | 2–3h     |
| Dreadhorn   | Shadow Abyss     | 3       | 2        | 1–2h     |
| Moltragron  | Shadow Abyss     | 3       | 2        | 1–2h     |
| Red Dragon  | Shadow Abyss     | 3       | 1        | 10–11h   |
| Kharzul     | Ruined Lorencia  | 1       | 3        | 3–4h     |
| Kharzul     | Shadow Abyss     | 3       | 1        | 3–4h     |
| Vescrya     | Ruined Devias    | 1       | 3        | 3–4h     |
| Vescrya     | Shadow Abyss     | 3       | 1        | 3–4h     |
| Muggron     | Shadow Abyss     | 3       | 1        | 6h       |
| Muggron     | Crywolf Fortress | 1       | 4        | 6h       |
| Muggron     | Balgass Barracks | 1       | 4        | 6h       |
| Draviel     | Aquilas Temple   | 3       | 10       | 4–6h     |
| Blue Goblin | Shadow Abyss     | 3       | 3        | 10–11h   |
| Red Goblin  | Shadow Abyss     | 3       | 3        | 10–11h   |
| Yellow Goblin | Shadow Abyss   | 3       | 3        | 10–11h   |
| Skarnath    | Kardamahal       | 8       | 10       | 3–4h     |

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

App at `http://localhost:8000`.

## Tests

```bash
python manage.py test firmeza
```

## Deploy

Configured for Render via `render.yaml`. Includes:

- Web service running gunicorn
- PostgreSQL database
- Cron job (`* * * * *`) running `check_spawns` — detects status transitions and
  sends push notifications

Required env vars: `SECRET_KEY`, `DATABASE_URL`, `VAPID_PUBLIC_KEY`,
`VAPID_PRIVATE_KEY`, `VAPID_ADMIN_EMAIL`.
