from pathlib import Path

from fastapi.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "static"

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Cache-busting: browsers otherwise keep serving a stale style.css after edits
# since Starlette's StaticFiles doesn't force revalidation by default.
# Computed fresh on every call (not once at import) — uvicorn --reload only
# watches .py files, so a stale one-time value would never change after
# editing style.css without an unrelated Python-file restart.
_css_path = STATIC_DIR / "css" / "style.css"


def _asset_version() -> str:
    return str(int(_css_path.stat().st_mtime))


templates.env.globals["asset_version"] = _asset_version
