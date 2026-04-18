# Firmeza Tracker

![Tests](https://github.com/lucas-eduardo-abreu/firmeza-tracker/actions/workflows/tests.yml/badge.svg)
![Coverage](coverage.svg)

Tracker de spawn de bosses para MU Dream.

## Funcionalidades

- Acompanhamento em tempo real de cada boss por servidor e monstro
- Contagem regressiva automática com status visual
- Registro de morte com horário manual ou automático
- Permissões por usuário — cada um edita apenas seus próprios registros
- Superusuário tem acesso total
- Filtros por mapa e boss

## Status

| Cor | Significado |
|-----|-------------|
| 🔵 Azul | Sem registro |
| 🔴 Vermelho | Morto (dentro do tempo mínimo) |
| 🟡 Amarelo | Possivelmente vivo (entre mínimo e máximo) |
| 🟢 Verde | Vivo (acima do tempo máximo) |

## Bosses

| Boss | Mapa | Servidores | Monstros | Respawn |
|------|------|-----------|----------|---------|
| Borgar | Shadow Abyss | 3 | 1 | 2–3h |
| Dreadhorn | Shadow Abyss | 3 | 2 | 1–2h |
| Moltragron | Shadow Abyss | 3 | 2 | 1–2h |
| Red Dragon | Shadow Abyss | 3 | 1 | 10–11h |
| Kharzul | Ruined Lorencia | 1 | 3 | 3–4h |
| Kharzul | Shadow Abyss | 3 | 1 | 3–4h |
| Vescrya | Ruined Devias | 1 | 3 | 3–4h |
| Vescrya | Shadow Abyss | 3 | 1 | 3–4h |
| Muggron | Shadow Abyss | 3 | 1 | 6h |
| Muggron | Crywolf Fortress | 1 | 4 | 6h |
| Muggron | Balgass Barracks | 1 | 4 | 6h |
| Draviel | Aquilas Temple | 3 | 10 | 4–6h |
| Blue Goblin | Shadow Abyss | 3 | 3 | 10–11h |
| Red Goblin | Shadow Abyss | 3 | 3 | 10–11h |
| Yellow Goblin | Shadow Abyss | 3 | 3 | 10–11h |
| Skarnath | Kardamahal | 8 | 10 | 3–4h |

## Setup local

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

## Deploy (VPS)

1. Clone o repositório
2. Copie `.env.example` para `.env` e preencha as variáveis
3. Instale as dependências: `pip install -r requirements.txt`
4. Rode as migrações: `python manage.py migrate`
5. Popule os dados: `python manage.py seed`
6. Colete os estáticos: `python manage.py collectstatic`
7. Suba com gunicorn: `gunicorn firmeza.wsgi`
