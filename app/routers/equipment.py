import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_login
from app.database import get_db
from app.sanitize import sanitize_html
from app.templates import templates

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _optional_int(value: Optional[str]) -> Optional[int]:
    """HTML <select> sends "" for the "—" option; FastAPI's int parsing rejects
    that before it reaches our code, so this field must arrive as str."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _equipment_types(db: sqlite3.Connection):
    return db.execute(
        "SELECT equipment_type_id, type_name FROM equipment_types ORDER BY type_name"
    ).fetchall()


def _all_brigades(db: sqlite3.Connection):
    return db.execute(
        """SELECT brigade_id, name FROM brigades
           ORDER BY CAST(name AS INTEGER), name"""
    ).fetchall()


@router.get("")
def list_equipment(request: Request, db: sqlite3.Connection = Depends(get_db)):
    equipment = db.execute(
        """SELECT e.equipment_id, e.name, e.description, e.adopted_date, et.type_name
           FROM equipment e
           LEFT JOIN equipment_types et ON e.equipment_type_id = et.equipment_type_id
           ORDER BY (et.type_name IS NULL), et.type_name, e.name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "equipment_list.html", {"equipment": equipment}
    )


@router.get("/new")
def new_equipment_form(
    request: Request, db: sqlite3.Connection = Depends(get_db), _user: str = Depends(require_login)
):
    return templates.TemplateResponse(
        request, "equipment_form.html",
        {"equipment": None, "equipment_types": _equipment_types(db), "brigades": [], "all_brigades": []},
    )


@router.post("/new")
def create_equipment(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    equipment_type_id: Optional[str] = Form(None),
    photo: Optional[str] = Form(None),
    adopted_date: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        cur = db.execute(
            """INSERT INTO equipment (name, description, equipment_type_id, photo, adopted_date)
               VALUES (?, ?, ?, ?, ?)""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(equipment_type_id),
                photo or None,
                adopted_date or None,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/equipment/{cur.lastrowid}/edit", status_code=303)


@router.get("/{equipment_id}")
def equipment_detail(equipment_id: int, request: Request, db: sqlite3.Connection = Depends(get_db)):
    equipment = db.execute(
        """SELECT e.*, et.type_name
           FROM equipment e
           LEFT JOIN equipment_types et ON e.equipment_type_id = et.equipment_type_id
           WHERE e.equipment_id = ?""",
        (equipment_id,),
    ).fetchone()

    brigades = db.execute(
        """SELECT b.brigade_id, b.name, b.emblem_file, mb.branch_name
           FROM brigade_equipment be
           JOIN brigades b ON be.brigade_id = b.brigade_id
           LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
           WHERE be.equipment_id = ?
           ORDER BY CAST(b.name AS INTEGER), b.name""",
        (equipment_id,),
    ).fetchall()

    return templates.TemplateResponse(
        request, "equipment_detail.html", {"equipment": equipment, "brigades": brigades}
    )


@router.get("/{equipment_id}/edit")
def edit_equipment_form(
    equipment_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    equipment = db.execute(
        "SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,)
    ).fetchone()

    brigades = db.execute(
        """SELECT b.brigade_id, b.name
           FROM brigade_equipment be
           JOIN brigades b ON be.brigade_id = b.brigade_id
           WHERE be.equipment_id = ?
           ORDER BY CAST(b.name AS INTEGER), b.name""",
        (equipment_id,),
    ).fetchall()

    assigned_ids = {r["brigade_id"] for r in brigades}
    all_brigades = [b for b in _all_brigades(db) if b["brigade_id"] not in assigned_ids]

    return templates.TemplateResponse(
        request,
        "equipment_form.html",
        {
            "equipment": equipment,
            "equipment_types": _equipment_types(db),
            "brigades": brigades,
            "all_brigades": all_brigades,
        },
    )


@router.post("/{equipment_id}/edit")
def update_equipment(
    equipment_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    equipment_type_id: Optional[str] = Form(None),
    photo: Optional[str] = Form(None),
    adopted_date: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            """UPDATE equipment SET
                   name = ?, description = ?, equipment_type_id = ?, photo = ?, adopted_date = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE equipment_id = ?""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(equipment_type_id),
                photo or None,
                adopted_date or None,
                equipment_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/equipment/{equipment_id}", status_code=303)


@router.post("/{equipment_id}/delete")
def delete_equipment(
    equipment_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute("DELETE FROM brigade_equipment WHERE equipment_id = ?", (equipment_id,))
    db.execute("DELETE FROM equipment WHERE equipment_id = ?", (equipment_id,))
    db.commit()
    return RedirectResponse(url="/equipment", status_code=303)


@router.post("/{equipment_id}/brigades")
def add_brigade_to_equipment(
    equipment_id: int,
    brigade_id: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            "INSERT INTO brigade_equipment (brigade_id, equipment_id) VALUES (?, ?)",
            (brigade_id, equipment_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/equipment/{equipment_id}/edit", status_code=303)


@router.post("/{equipment_id}/brigades/{brigade_id}/remove")
def remove_brigade_from_equipment(
    equipment_id: int,
    brigade_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute(
        "DELETE FROM brigade_equipment WHERE equipment_id = ? AND brigade_id = ?",
        (equipment_id, brigade_id),
    )
    db.commit()
    return RedirectResponse(url=f"/equipment/{equipment_id}/edit", status_code=303)
