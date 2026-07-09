# Портал бригад ЗСУ

Довідковий сайт про бригади, битви, спорядження й традиції Збройних Сил України.
Дані зберігаються в SQLite (`data/quetzal_zsu.db`), рендеринг сторінок — на сервері (FastAPI + Jinja2),
без збірки фронтенду. Детальний опис архітектури — у [`docs/architecture.md`](docs/architecture.md).

## Функціонал

- Список бригад із фільтрами за родом військ, корпусом, територіальним командуванням і регіоном
- Детальна сторінка бригади: битви, спорядження, традиції, базова статистика
- Форма створення й редагування бригади (без автентифікації)
- Хронологія битв з переліком бригад-учасниць і їх ролі
- Довідники: спорядження, традиції, локації, регіони

## Стек

Python 3.12+ · FastAPI · Uvicorn · Jinja2 · SQLite (stdlib `sqlite3`, без ORM)

## Структура проєкту

```
app/
├── main.py            # точка входу FastAPI
├── database.py        # підключення до data/quetzal_zsu.db
├── models.py          # Pydantic-схеми
├── routers/           # brigades, battles, equipment, traditions, locations
└── templates/         # Jinja2 HTML-шаблони
static/                # CSS, зображення
data/
├── quetzal_zsu.db     # база даних SQLite
└── schema.sql          # канонічна версійована схема БД
docs/                  # архітектурна документація, довідкові дані
quetzal_zsu.ps1        # скрипт запуску/зупинки для Windows PowerShell
```

## Запуск

Потрібен лише **Python 3.12+**. Проєкт можна запустити двома способами: через готовий
PowerShell-скрипт (Windows) або вручну (Windows/macOS/Linux) — обидва варіанти нижче.

### Варіант 1 — Windows, через `quetzal_zsu.ps1` (найпростіше)

Скрипт сам перевіряє Python, встановлює відсутні залежності, перевіряє наявність БД і запускає сервер.

```powershell
# з кореня репозиторію
powershell -ExecutionPolicy Bypass -File .\quetzal_zsu.ps1 run
```

Відкрити: http://127.0.0.1:8000/brigades

Зупинити сервер:
```powershell
powershell -ExecutionPolicy Bypass -File .\quetzal_zsu.ps1 stop
```

Інші команди: `check` (лише перевірка готовності), `install` (лише встановити залежності).
Додаткові параметри: `-Port 8080`, `-BindHost 0.0.0.0`, `-NoReload`.

**Щоб викликати просто `quetzal_zsu run` без шляху до файлу** — додай у свій PowerShell-профіль
(`$PROFILE`) функцію:
```powershell
function quetzal_zsu { & "ПОВНИЙ_ШЛЯХ_ДО_РЕПО\quetzal_zsu.ps1" @args }
```
і відкрий новий термінал.

### Варіант 2 — будь-яка ОС, вручну

```bash
# 1. Клонувати репозиторій і перейти в нього
git clone <URL_РЕПОЗИТОРІЮ>
cd quetzal_zsu

# 2. (рекомендовано) створити віртуальне середовище
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Встановити залежності
pip install -r requirements.txt

# 4. Запустити сервер
python -m uvicorn app.main:app --reload
```

Відкрити: http://127.0.0.1:8000/brigades

Зупинити: `Ctrl+C` у тому ж терміналі.

> Якщо команда `uvicorn` не знаходиться напряму (не в PATH) — завжди можна запускати через
> `python -m uvicorn ...`, як показано вище.

### Варіант 3 — Docker (без встановлення Python на хост)

```bash
docker build -t quetzal-zsu .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/srv/data" quetzal-zsu
```

Відкрити: http://127.0.0.1:8000/brigades

## Дані

БД `data/quetzal_zsu.db` вже містить довідники (роди військ, корпуси, регіони тощо) та частину бригад,
завантажену з `docs/brigades.md`. Схема версіонується в `data/schema.sql` — якщо потрібно перестворити
базу з нуля, застосуй цей файл до нового порожнього `.db` через `sqlite3`/`python -m sqlite3`.

Для імпорту решти розділів `docs/brigades.md` є проєктний скіл `.claude/skills/add-brigades`
(Claude Code): `/add-brigades <назва розділу>`.

## Розгортання

Варіанти безкоштовного хостингу з персистентним диском для SQLite — розділ 4
[`docs/architecture.md`](docs/architecture.md#4-де-розмістити-портал) (рекомендовано Fly.io,
конфіг — `fly.toml`).
