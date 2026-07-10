# Портал бригад ЗСУ — CLAUDE.md

Довідник для Claude Code: стек, архітектура, робочі команди і ключові рішення.

---

## Стек

| Шар | Технологія |
|---|---|
| Мова | Python 3.13 |
| Веб-фреймворк | FastAPI 0.139+ |
| Шаблони | Jinja2 (server-side render, без збірки фронтенду) |
| БД | SQLite — `data/quetzal_zsu.db` (stdlib `sqlite3`, без ORM) |
| Сервер | Uvicorn (ASGI) |
| CSS | Чистий CSS у `static/css/style.css`, без препроцесорів |

---

## Структура

```
app/
├── main.py            # FastAPI app, реєстрація роутерів, маршрут /favicon.ico
├── database.py        # get_db() — sqlite3 connection з Row factory
├── models.py          # Pydantic-схеми для форм (BrigadeIn тощо)
├── templates.py       # Єдиний Jinja2Templates + asset_version() для cache-busting CSS
└── routers/
    ├── brigades.py    # /brigades, /brigades/{id}, /brigades/{id}/edit, /brigades/new
    ├── battles.py     # /battles, /battles/{id}
    ├── equipment.py   # /equipment
    ├── traditions.py  # /traditions
    └── stats.py       # /stats (розподіл за родом військ/ОК, лічильники)
app/templates/
    base.html          # навігація, favicon, asset_version CSS cache-bust
    index.html         # список бригад, фільтри-чипи, вид карток/таблиці, живий пошук
    brigade_detail.html
    brigade_form.html
    battles_list.html / battle_detail.html
    equipment_list.html / traditions_list.html
    stats.html
static/
    css/style.css      # єдиний файл стилів, без зовнішніх залежностей
    img/               # емблеми бригад + логотипи ЗСУ
data/
    quetzal_zsu.db     # SQLite, на проді зберігається на persistent volume
    schema.sql         # канонічна схема (з усіма FK, CHECK, індексами)
docs/
    architecture.md    # опис стеку, хостинг
    brigades.md        # вихідні дані для імпорту
.claude/skills/
    add-brigades/      # /add-brigades <розділ> — імпорт бригад з docs/brigades.md у БД
    add-brigade-emblem/ # /add-brigade-emblem — додавання/нормалізація нарукавного знака
quetzal_zsu.ps1        # Windows helper: run / stop / check / install
```

---

## Запуск

```powershell
# Windows (глобальний псевдонім, вже налаштований у $PROFILE)
quetzal_zsu run
quetzal_zsu stop

# або напряму
powershell -ExecutionPolicy Bypass -File .\quetzal_zsu.ps1 run
```

```bash
# будь-яка ОС
python -m uvicorn app.main:app --reload
```

Сторінка: http://127.0.0.1:8000/brigades

---

## База даних

### Схема (ключові таблиці)

- **`brigades`** — основна таблиця; FK на `military_branches`, `army_corps`, `territorial_commands`, `troop_types`, `locations`; поле `emblem_file` — ім'я файлу в `static/img/`
- **`battles`** — FK на `locations`; `CHECK(start_date <= end_date)`
- **`brigade_battles`**, **`brigade_equipment`**, **`brigade_traditions`** — junction-таблиці з повними FK на обидва боки
- **`brigade_photos`** — до 3 фото на бригаду, `UNIQUE(brigade_id, position)`, `CHECK(position IN (1,2,3))`
- Усі таблиці мають `created_at`/`updated_at`; довідники мають `UNIQUE` на назвах

### Підключення

`app/database.py` → `get_db()` — FastAPI Depends, віддає `sqlite3.Connection` з `row_factory = sqlite3.Row` і `PRAGMA foreign_keys = ON`.

### Актуальні дані

БД містить довідники (7 родів військ, 18 корпусів, 6 ОК, 9 типів військ, 27 регіонів) та 14 бригад ДШВ з нарукавними знаками для 13 з них.

---

## Емблеми бригад

- Формат: **PNG 440×520 px, RGBA з прозорим фоном** — усі в `static/img/brigade-{N}.png`
- Прозорий фон зроблено flood-fill від кутів (tolerance=18)
- CSS `.emblem.has-image` / `.detail-emblem.has-image` → `background: transparent; border: none`
- Для додавання нових: `/add-brigade-emblem`

---

## CSS і кеш

- Єдиний файл: `static/css/style.css`
- `app/templates.py` рахує `mtime` файлу **при кожному запиті** і передає як `asset_version()` у шаблони → `<link href="/static/css/style.css?v=...">` — автоматичний cache-bust без перезапуску сервера

---

## Ключові поведінкові правила

- **Форми бригади:** поля FK (`military_branch_id`, `corps_id` тощо) декларуються як `Optional[str] = Form(None)` і конвертуються через `_optional_int()` — HTML `<select>` надсилає `""` для «—», що ламає `Optional[int]`
- **Сортування бригад:** `ORDER BY CAST(b.name AS INTEGER), b.name` — числове (25 → 46 → 95 → 147), а не лексикографічне
- **Живий пошук на `/brigades`:** JS-фільтр за атрибутом `data-name` (lowercase); підходить якщо будь-яке слово назви **починається** з запиту; форма не відправляється при вводі
- **Favicon:** `GET /favicon.ico` → `FileResponse(static/img/zsu-tryzub.png)` (жовтий тризуб ЗСУ)
- **Cache-bust CSS:** функція, а не константа — щоб зміни підхоплювались без рестарту сервера
- **Прозорі емблеми:** `object-fit: contain` + прозорий PNG → контейнер `.emblem.has-image` без фону і рамки

---

## Розгортання

Рекомендовано: **Fly.io** (persistent volume для SQLite). Конфіг: `fly.toml`. Детальніше: `docs/architecture.md`.

Docker:
```bash
docker build -t quetzal-zsu .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/srv/data" quetzal-zsu
```
