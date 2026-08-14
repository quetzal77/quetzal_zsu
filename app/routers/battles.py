import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_login
from app.database import get_db
from app.sanitize import sanitize_html
from app.templates import templates

router = APIRouter(prefix="/battles", tags=["battles"])


def _battle_status(start_date, end_date):
    if end_date:
        return "завершено"
    if start_date:
        return "триває"
    return None


_MONTHS_UK = ["січ", "лют", "бер", "кві", "тра", "чер", "лип", "сер", "вер", "жов", "лис", "гру"]


def _format_period(start_date: Optional[str], end_date: Optional[str]) -> str:
    """Coarse "лют – кві 2022"-style range for the timeline widget; falls back to
    raw ISO dates if either value isn't a well-formed YYYY-MM-DD string."""
    def parse(d):
        if not d:
            return None
        try:
            y, m, _ = d.split("-")
            return int(y), int(m)
        except ValueError:
            return None

    s, e = parse(start_date), parse(end_date)
    if s is None and e is None:
        return start_date or end_date or ""
    if s is None:
        return f"{_MONTHS_UK[e[1] - 1]} {e[0]}"
    if e is None:
        return f"{_MONTHS_UK[s[1] - 1]} {s[0]}"
    if s[0] == e[0] and s[1] == e[1]:
        return f"{_MONTHS_UK[s[1] - 1]} {s[0]}"
    if s[0] == e[0]:
        return f"{_MONTHS_UK[s[1] - 1]} – {_MONTHS_UK[e[1] - 1]} {s[0]}"
    return f"{_MONTHS_UK[s[1] - 1]} {s[0]} – {_MONTHS_UK[e[1] - 1]} {e[0]}"


def _optional_int(value: Optional[str]) -> Optional[int]:
    """HTML <select> sends "" for the "—" option; FastAPI's int parsing rejects
    that before it reaches our code, so these fields must arrive as str."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _locations(db: sqlite3.Connection):
    return db.execute(
        """SELECT l.location_id, l.city_name, r.region_name
           FROM locations l JOIN regions r ON l.region_id = r.region_id
           ORDER BY l.city_name COLLATE UKRAINIAN"""
    ).fetchall()


def _all_brigades(db: sqlite3.Connection):
    return db.execute(
        """SELECT brigade_id, name FROM brigades
           ORDER BY CAST(name AS INTEGER), name"""
    ).fetchall()


@router.get("")
def list_battles(request: Request, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """SELECT b.battle_id, b.name, b.start_date, b.end_date, b.description, l.city_name, r.region_name
           FROM battles b
           LEFT JOIN locations l ON b.location_id = l.location_id
           LEFT JOIN regions r ON l.region_id = r.region_id
           ORDER BY b.start_date"""
    ).fetchall()

    battles = []
    for r in rows:
        battle = dict(r)
        battle["status"] = _battle_status(r["start_date"], r["end_date"])
        battle["period"] = _format_period(r["start_date"], r["end_date"])
        battle["year"] = r["start_date"][:4] if r["start_date"] else None
        battles.append(battle)

    return templates.TemplateResponse(request, "battles_list.html", {"battles": battles})


@router.get("/new")
def new_battle_form(
    request: Request, db: sqlite3.Connection = Depends(get_db), _user: str = Depends(require_login)
):
    return templates.TemplateResponse(
        request, "battle_form.html",
        {"battle": None, "locations": _locations(db)},
    )


@router.post("/new")
def create_battle(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    location_id: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        cur = db.execute(
            """INSERT INTO battles (name, description, location_id, start_date, end_date)
               VALUES (?, ?, ?, ?, ?)""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(location_id),
                start_date or None,
                end_date or None,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/battles/{cur.lastrowid}/edit", status_code=303)


@router.get("/{battle_id}")
def battle_detail(battle_id: int, request: Request, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        """SELECT b.*, l.city_name, r.region_name
           FROM battles b
           LEFT JOIN locations l ON b.location_id = l.location_id
           LEFT JOIN regions r ON l.region_id = r.region_id
           WHERE b.battle_id = ?""",
        (battle_id,),
    ).fetchone()
    battle = dict(row) if row else None
    if battle:
        battle["status"] = _battle_status(battle["start_date"], battle["end_date"])

    brigades = db.execute(
        """SELECT br.brigade_id, br.name, br.emblem_file
           FROM brigade_battles bb
           JOIN brigades br ON bb.brigade_id = br.brigade_id
           WHERE bb.battle_id = ?
           ORDER BY br.name""",
        (battle_id,),
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "battle_detail.html",
        {"battle": battle, "brigades": brigades},
    )


@router.get("/{battle_id}/edit")
def edit_battle_form(
    battle_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    battle = db.execute(
        "SELECT * FROM battles WHERE battle_id = ?", (battle_id,)
    ).fetchone()

    brigades = db.execute(
        """SELECT br.brigade_id, br.name
           FROM brigade_battles bb
           JOIN brigades br ON bb.brigade_id = br.brigade_id
           WHERE bb.battle_id = ?
           ORDER BY CAST(br.name AS INTEGER), br.name""",
        (battle_id,),
    ).fetchall()

    assigned_ids = {r["brigade_id"] for r in brigades}
    all_brigades = [b for b in _all_brigades(db) if b["brigade_id"] not in assigned_ids]

    return templates.TemplateResponse(
        request,
        "battle_form.html",
        {
            "battle": battle,
            "brigades": brigades,
            "all_brigades": all_brigades,
            "locations": _locations(db),
        },
    )


@router.post("/{battle_id}/edit")
def update_battle(
    battle_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    location_id: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            """UPDATE battles SET
                   name = ?, description = ?, location_id = ?, start_date = ?, end_date = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE battle_id = ?""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(location_id),
                start_date or None,
                end_date or None,
                battle_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/battles/{battle_id}", status_code=303)


@router.post("/{battle_id}/delete")
def delete_battle(
    battle_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute("DELETE FROM brigade_battles WHERE battle_id = ?", (battle_id,))
    db.execute("DELETE FROM battles WHERE battle_id = ?", (battle_id,))
    db.commit()
    return RedirectResponse(url="/battles", status_code=303)


@router.post("/{battle_id}/brigades")
def add_brigade_to_battle(
    battle_id: int,
    brigade_id: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            "INSERT INTO brigade_battles (brigade_id, battle_id) VALUES (?, ?)",
            (brigade_id, battle_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/battles/{battle_id}/edit", status_code=303)


@router.post("/{battle_id}/brigades/{brigade_id}/remove")
def remove_brigade_from_battle(
    battle_id: int,
    brigade_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute(
        "DELETE FROM brigade_battles WHERE battle_id = ? AND brigade_id = ?",
        (battle_id, brigade_id),
    )
    db.commit()
    return RedirectResponse(url=f"/battles/{battle_id}/edit", status_code=303)
