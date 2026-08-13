# Портал з'єднань ЗСУ — CLAUDE.md

Довідник для Claude Code: стек, архітектура, робочі команди і ключові рішення.

Портал показує не лише окремі бригади, а й загальну структуру Збройних Сил України (види,
роди військ/сил, спецслужби) — тому в UI та документації вжито термін **«з'єднання»**, а не
«бригада»: серед з'єднань є полки, батальйони, окремі команди тощо (`unit_types`), і опис
структури ЗСУ на `/zsu` не обмежується бригадами. Таблиці й код усередині лишили історичну назву
`brigades`/`brigade_*` — перейменування торкнулось лише текстів інтерфейсу.

---

## Стек

| Шар | Технологія |
|---|---|
| Мова | Python 3.13 |
| Веб-фреймворк | FastAPI 0.115+ |
| Шаблони | Jinja2 (server-side render, без збірки фронтенду) |
| БД | SQLite — `data/quetzal_zsu.db` (stdlib `sqlite3`, без ORM) |
| Сервер | Uvicorn (ASGI) |
| CSS | Чистий CSS у `static/css/style.css`, без препроцесорів |

---

## Структура

```
app/
├── main.py            # FastAPI app, SessionMiddleware, реєстрація роутерів, / → redirect на /zsu, /favicon.ico
├── auth.py            # hash_password/verify_password (hashlib.scrypt), require_login dependency
├── database.py        # get_db() — sqlite3 connection з Row factory
├── templates.py       # Єдиний Jinja2Templates + asset_version() для cache-busting CSS
└── routers/
    ├── auth.py        # /login (GET+POST), /logout (POST)
    ├── zsu.py         # /zsu, /zsu/{slug} — статична структура ЗСУ (види, роди військ/сил, спецслужби)
    ├── brigades.py    # /brigades, /brigades/{id}, /brigades/{id}/edit, /brigades/new (реєстр з'єднань)
    ├── battles.py     # /battles, /battles/{id}, /battles/new, /battles/{id}/edit — CRUD + прив'язка з'єднань-учасників
    ├── equipment.py   # /equipment, /equipment/{id}, /equipment/new, /equipment/{id}/edit — CRUD + прив'язка з'єднань
    ├── traditions.py  # /traditions, /traditions/{id}, /traditions/new, /traditions/{id}/edit — CRUD + прив'язка з'єднань
    ├── stats.py       # /stats (розподіл за родом військ/ОК, лічильники)
    └── settings.py    # /settings — універсальний CRUD для довідників (lookup-таблиці) + регіони/локації
app/templates/
    base.html          # навігація (ЗСУ / З'єднання / Битви / Спорядження / Традиції / Статистика / Налаштування)
    login.html          # форма входу
    zsu.html / zsu_branch.html  # структура ЗСУ і сторінка окремого роду військ/сил (ССО, СБС активні)
    index.html         # реєстр з'єднань, фільтри-чипи, вид карток/таблиці, живий пошук
    brigade_detail.html / brigade_form.html
    battles_list.html / battle_detail.html / battle_form.html
    equipment_list.html / equipment_detail.html / equipment_form.html
    traditions_list.html / tradition_detail.html / tradition_form.html
    stats.html
    settings.html      # універсальні плашки-довідники (lookup_panel макрос) + регіони/локації
static/
    css/style.css      # єдиний файл стилів, без зовнішніх залежностей
    img/               # емблеми з'єднань + логотипи ЗСУ + іконки родів військ/сил (forces/*.png)
data/
    quetzal_zsu.db     # SQLite, на проді зберігається на persistent volume
    schema.sql         # канонічна схема (з усіма FK, CHECK, індексами)
docs/
    architecture.md    # опис стеку, хостинг
    brigades.md        # вихідні дані для імпорту
.claude/skills/
    add-brigades/      # /add-brigades <розділ> — імпорт з'єднань з docs/brigades.md у БД
    add-brigade-emblem/ # /add-brigade-emblem — додавання/нормалізація нарукавного знака
    research-brigade/  # /research-brigade <назва> — дослідження полів/дат/традицій з'єднання
                        # з джерелами, без записів у БД (готує вхід для add-brigades)
quetzal_zsu.ps1        # Windows helper: run / stop / check / install / backup
create_user.py         # CLI: python create_user.py <username> — створює/оновлює редактора
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

Головна сторінка: http://127.0.0.1:8000/ (редіректить на `/zsu` — структура ЗСУ).
Реєстр з'єднань: http://127.0.0.1:8000/brigades

---

## База даних

### Схема (ключові таблиці)

- **`brigades`** — основна таблиця з'єднань; FK на `military_branches`, `army_corps`,
  `territorial_commands`, `troop_types`, `unit_types`, `locations`; поле `emblem_file` — ім'я
  файлу в `static/img/`; `unit_type_id` — тип з'єднання (Бригада / Полк / Батальйон тощо)
- **`military_branches`** — довідник родів військ; лише `branch_name` і FK `details_id`, який
  обирається зі самостійного довідника `military_branch_details` (плашка «Роди військ» влаштована
  так само, як «Оперативні командування» — вибір зі списку, а не інлайн-поля)
- **`military_branch_details`** — самостійний довідник «Деталі родів військ» (`details_name` +
  `founded_date`, `hq_location_id`, `emblem_file`, `flag_file`, `patch_file`, `beret_badge_file`);
  керується окремою плашкою в `/settings`; `military_branches.details_id` обирає потрібний рядок
  за `details_name`, а `/zsu/{slug}` підтягує обраний запис через `LEFT JOIN`
- **`army_corps`** — довідник корпусів; `founded_date` (дата заснування) та `emblem_file`
  (емблема корпусу) — редагуються на плашці «Армійські корпуси» в `/settings`
- **`unit_types`** — довідник типів з'єднань (Бригада / Полк / Батальйон...), FK з `brigades.unit_type_id`
- **`battles`** — FK на `locations`; `CHECK(start_date <= end_date)`
- **`brigade_battles`**, **`brigade_equipment`**, **`brigade_traditions`** — junction-таблиці з повними FK на обидва боки
- **`brigade_photos`** — до 3 фото на з'єднання, `UNIQUE(brigade_id, position)`, `CHECK(position IN (1,2,3))`
- **`users`** — `username` (UNIQUE) + `password_hash` (`hashlib.scrypt`, формат `salt_hex$digest_hex`); немає FK на інші таблиці, це лише облікові записи редакторів
- Усі таблиці мають `created_at`/`updated_at`; довідники мають `UNIQUE` на назвах

### Підключення

`app/database.py` → `get_db()` — FastAPI Depends, віддає `sqlite3.Connection` з `row_factory = sqlite3.Row` і `PRAGMA foreign_keys = ON`.

### Актуальні дані

БД містить довідники (роди військ, корпуси, ОК, типи військ, типи з'єднань, регіони) та з'єднання
ДШВ/ССО/СБС/морської піхоти/сил безпілотних систем з нарукавними знаками.

---

## Налаштування (`/settings`)

- Універсальний механізм для довідників (lookup-таблиць) у `app/routers/settings.py`:
  `_LOOKUP_TABLES` описує таблицю, id/name-колонки й опційні `extra_cols` (текст/дата/FK на
  локацію/рід військ/деталі роду військ) — додати нове поле довіднику здебільшого означає
  дописати запис у цей словник плюс однойменний `Form(None)`-параметр у
  `create_lookup_item`/`update_lookup_item`.
- Типи `extra_cols`: `"date"`, `"location"` (select із локацій), `"branch"` (select із родів
  військ — напр. Оперативні командування), `"branch-details"` (select із `military_branch_details`
  за `details_name` — напр. Роди військ), без `"type"` — звичайне текстове поле (файл/URL).
- `"wide": True` — плашка розкладається фіксованим грідом на 4 колонки і займає весь рядок
  (для довідників із кількома додатковими полями, напр. Деталі родів військ, Армійські корпуси);
  без цього прапорця — звичайний flex-рядок на половину ширини сторінки (напр. Роди військ,
  Оперативні командування, Локації).
- `"list_max_height"` — опційне перевизначення висоти списку прокрутки (за замовчуванням `320px`
  для `wide`, `230px` для решти); напр. в Армійських корпусах обмежено до `150px` (~3 рядки видно).
- Порядок плашок на сторінці — явний у `settings.html` (не просто порядок словника):
  Роди військ → Деталі родів військ → Оперативні командування → Армійські корпуси →
  Типи родів військ → Типи з'єднань → Локації → Регіони → решта довідників.
- Регіони/Локації — не lookup-таблиці (у Локацій є FK-вибір регіону і перевірка дублікатів
  міста в межах регіону), тому мають власні роути `/settings/regions*` і `/settings/locations*`.

---

## Емблеми з'єднань

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

- **Форми з'єднання:** поля FK (`military_branch_id`, `corps_id` тощо) декларуються як `Optional[str] = Form(None)` і конвертуються через `_optional_int()` — HTML `<select>` надсилає `""` для «—», що ламає `Optional[int]`
- **Сортування з'єднань:** `ORDER BY CAST(b.name AS INTEGER), b.name` — числове (25 → 46 → 95 → 147), а не лексикографічне
- **Живий пошук на `/brigades`:** JS-фільтр за атрибутом `data-name` (lowercase); підходить якщо будь-яке слово назви **починається** з запиту; форма не відправляється при вводі
- **Структура ЗСУ (`/zsu`):** статичний список у `STRUCTURE`/`ACTIVE_SLUGS` (`app/routers/zsu.py`) — плашка клікабельна лише якщо її slug у `ACTIVE_SLUGS` (наразі ССО й Сили безпілотних систем), решта — заготовки під майбутні сторінки
- **Favicon:** `GET /favicon.ico` → `FileResponse(static/img/zsu-tryzub.png)` (жовтий тризуб ЗСУ)
- **Cache-bust CSS:** функція, а не константа — щоб зміни підхоплювались без рестарту сервера
- **Прозорі емблеми:** `object-fit: contain` + прозорий PNG → контейнер `.emblem.has-image` без фону і рамки

---

## Авторизація

- Перегляд (списки, деталі, статистика, структура ЗСУ) — публічний, без входу.
- Створення/редагування/видалення з'єднань, битв, спорядження, традицій і довідників
  (`/brigades/new`, `/brigades/{id}/edit`, `/battles/new`, `/battles/{id}/edit`,
  `/equipment/new`, `/equipment/{id}/edit`, `/traditions/new`, `/traditions/{id}/edit`,
  прив'язка/відв'язка з'єднань до битв/спорядження/традицій, усе під `/settings`) захищене
  через `Depends(require_login)` (`app/auth.py`) — редіректить на `/login?next=...`, якщо в
  сесії немає `username`.
- Сесії — `starlette.middleware.sessions.SessionMiddleware` (підписані cookie, `itsdangerous`).
  Секрет береться з env `SESSION_SECRET`; якщо не задано — небезпечний дефолт для локальної
  розробки з попередженням у консоль. **На проді (Fly.io) обов'язково задати свій
  `SESSION_SECRET`** (`fly secrets set SESSION_SECRET=...`).
- Паролі — `hashlib.scrypt` (стандартна бібліотека, без passlib/bcrypt).
- Немає публічної форми реєстрації і немає журналу "хто що редагував" — свідоме рішення,
  щоб не розширювати обсяг. Нові облікові записи створюються вручну: `python create_user.py <username>`.

---

## Розгортання

Рекомендовано: **Fly.io** (persistent volume для SQLite). Конфіг: `fly.toml`. Детальніше: `docs/architecture.md`.

Docker:
```bash
docker build -t quetzal-zsu .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/srv/data" quetzal-zsu
```
