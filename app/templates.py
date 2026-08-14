from datetime import date, datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "static"

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

_UK_MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]


def format_date_uk(value) -> str:
    """Форматує дату з БД (РРРР-ММ-ДД) у читабельний вигляд: "22 липня 2024 р."."""
    if not value:
        return "—"
    if isinstance(value, (date, datetime)):
        d = value
    else:
        try:
            d = date.fromisoformat(str(value)[:10])
        except ValueError:
            return str(value)
    return f"{d.day} {_UK_MONTHS[d.month - 1]} {d.year} р."


templates.env.filters["uk_date"] = format_date_uk

# Cache-busting: browsers otherwise keep serving a stale style.css after edits
# since Starlette's StaticFiles doesn't force revalidation by default.
# Computed fresh on every call (not once at import) — uvicorn --reload only
# watches .py files, so a stale one-time value would never change after
# editing style.css without an unrelated Python-file restart.
_css_path = STATIC_DIR / "css" / "style.css"


def _asset_version() -> str:
    return str(int(_css_path.stat().st_mtime))


templates.env.globals["asset_version"] = _asset_version
