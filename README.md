# Портал бригад ЗСУ

Довідковий сайт про бригади, битви, спорядження й традиції Збройних Сил України.
Дані зберігаються в SQLite (`data/quetzal_zsu.db`), рендеринг сторінок — на сервері (FastAPI + Jinja2),
без збірки фронтенду.

## Функціонал

- Реєстр бригад із фільтрами за родом військ, корпусом, територіальним командуванням, типом військ і регіоном
- Два режими перегляду: картки і таблиця
- Живий пошук за назвою/номером бригади без перезавантаження сторінки
- Нарукавні знаки бригад (прозорий PNG, єдиний стандарт 440×520)
- Детальна сторінка бригади: бойовий шлях, спорядження, традиції, фотогалерея, статистика
- Форма створення й редагування бригади (без автентифікації)
- Хронологія битв з переліком бригад-учасниць і їх ролі
- Сторінка статистики: розподіл за родом військ і ОК, хронологія битв
- Довідники: спорядження, традиції
- Favicon — жовтий тризуб ЗСУ

## Стек

Python 3.13 · FastAPI · Uvicorn · Jinja2 · SQLite (stdlib `sqlite3`, без ORM)

## Структура проєкту

```
app/
├── main.py            # точка входу FastAPI
├── database.py        # підключення до data/quetzal_zsu.db
├── models.py          # Pydantic-схеми
├── templates.py       # спільний Jinja2Templates + cache-busting CSS
├── routers/           # brigades, battles, equipment, traditions, stats
└── templates/         # Jinja2 HTML-шаблони
static/
├── css/style.css      # всі стилі (без збірки)
└── img/               # нарукавні знаки бригад + логотипи ЗСУ
data/
├── quetzal_zsu.db     # база даних SQLite
└── schema.sql         # канонічна версійована схема БД
docs/                  # архітектурний опис, вихідні дані бригад
.claude/skills/        # Claude Code скіли для розробки
quetzal_zsu.ps1        # Windows-скрипт: run / stop / check / install
```

Детальніше про архітектуру і технічні рішення — у [`CLAUDE.md`](CLAUDE.md) та [`docs/architecture.md`](docs/architecture.md).

---

## Запуск

Потрібен лише **Python 3.12+**.

### Windows — через `quetzal_zsu.ps1`

Скрипт перевіряє Python, встановлює залежності, запускає сервер. Якщо налаштовано псевдонім у `$PROFILE`:

```powershell
quetzal_zsu run     # запустити
quetzal_zsu stop    # зупинити
quetzal_zsu check   # перевірка без запуску
```

Або напряму:
```powershell
powershell -ExecutionPolicy Bypass -File .\quetzal_zsu.ps1 run
```

Відкрити: http://127.0.0.1:8000/brigades

### Будь-яка ОС — вручну

```bash
git clone <URL>
cd quetzal_zsu

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Відкрити: http://127.0.0.1:8000/brigades · Зупинити: `Ctrl+C`

> Якщо `uvicorn` не знаходиться в PATH — завжди використовуй `python -m uvicorn ...`

### Docker

```bash
docker build -t quetzal-zsu .
docker run --rm -p 8000:8000 -v "$(pwd)/data:/srv/data" quetzal-zsu
```

---

## Дані

`data/quetzal_zsu.db` містить повні довідники (роди військ, корпуси, регіони тощо) та бригади ДШВ із нарукавними знаками.
Схема версіонується в `data/schema.sql`.

Для імпорту бригад з `docs/brigades.md` (Claude Code): `/add-brigades <назва розділу>`
Для додавання нарукавного знака (Claude Code): `/add-brigade-emblem`

## Розгортання

Рекомендовано **Fly.io** (безкоштовний persistent volume для SQLite). Конфіг: `fly.toml`.
Детальніше: [`docs/architecture.md`](docs/architecture.md#4-де-розмістити-портал).