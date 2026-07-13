import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import SESSION_USER_KEY, verify_password
from app.database import get_db
from app.templates import templates

router = APIRouter(tags=["auth"])


def _safe_next(next: str) -> str:
    """Only allow same-site relative redirects; a "//host" value is protocol-relative
    and would send the user off-site, so it's rejected along with any other absolute URL."""
    if next and next.startswith("/") and not next.startswith("//"):
        return next
    return "/brigades"


@router.get("/login")
def login_form(request: Request, next: str = "/brigades"):
    return templates.TemplateResponse(
        request, "login.html", {"next": _safe_next(next), "error": None}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/brigades"),
    db: sqlite3.Connection = Depends(get_db),
):
    next = _safe_next(next)
    row = db.execute(
        "SELECT username, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next": next, "error": "Невірний логін або пароль"},
            status_code=401,
        )
    request.session[SESSION_USER_KEY] = row["username"]
    return RedirectResponse(url=next, status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/brigades", status_code=303)
