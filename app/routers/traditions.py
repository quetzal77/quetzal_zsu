import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_login
from app.database import get_db
from app.templates import templates

router = APIRouter(prefix="/traditions", tags=["traditions"])


def _all_brigades(db: sqlite3.Connection):
    return db.execute(
        """SELECT brigade_id, name FROM brigades
           ORDER BY CAST(name AS INTEGER), name"""
    ).fetchall()


@router.get("")
def list_traditions(request: Request, db: sqlite3.Connection = Depends(get_db)):
    traditions = db.execute(
        """SELECT t.tradition_id, t.title, t.description, t.photo,
                  COUNT(bt.brigade_id) AS brigade_count
           FROM traditions t
           LEFT JOIN brigade_traditions bt ON t.tradition_id = bt.tradition_id
           GROUP BY t.tradition_id
           ORDER BY t.title"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "traditions_list.html", {"traditions": traditions}
    )


@router.get("/new")
def new_tradition_form(
    request: Request, db: sqlite3.Connection = Depends(get_db), _user: str = Depends(require_login)
):
    return templates.TemplateResponse(
        request, "tradition_form.html",
        {"tradition": None, "brigades": [], "all_brigades": _all_brigades(db)},
    )


@router.post("")
def create_tradition(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    photo: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        cur = db.execute(
            "INSERT INTO traditions (title, description, photo) VALUES (?, ?, ?)",
            (title, description or None, photo or None),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/traditions/{cur.lastrowid}/edit", status_code=303)


@router.get("/{tradition_id}")
def tradition_detail(tradition_id: int, request: Request, db: sqlite3.Connection = Depends(get_db)):
    tradition = db.execute(
        "SELECT * FROM traditions WHERE tradition_id = ?", (tradition_id,)
    ).fetchone()

    brigades = db.execute(
        """SELECT b.brigade_id, b.name, mb.branch_name, ac.corps_name,
                  bt.date_assigned, bt.unit_name
           FROM brigade_traditions bt
           JOIN brigades b ON bt.brigade_id = b.brigade_id
           LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
           LEFT JOIN army_corps ac ON b.corps_id = ac.corps_id
           WHERE bt.tradition_id = ?
           ORDER BY CAST(b.name AS INTEGER), b.name""",
        (tradition_id,),
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "tradition_detail.html",
        {"tradition": tradition, "brigades": brigades},
    )


@router.get("/{tradition_id}/edit")
def edit_tradition_form(
    tradition_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    tradition = db.execute(
        "SELECT * FROM traditions WHERE tradition_id = ?", (tradition_id,)
    ).fetchone()

    brigades = db.execute(
        """SELECT b.brigade_id, b.name, bt.date_assigned, bt.unit_name, bt.photo
           FROM brigade_traditions bt
           JOIN brigades b ON bt.brigade_id = b.brigade_id
           WHERE bt.tradition_id = ?
           ORDER BY CAST(b.name AS INTEGER), b.name""",
        (tradition_id,),
    ).fetchall()

    # brigades not yet assigned to this tradition
    assigned_ids = {r["brigade_id"] for r in brigades}
    all_brigades = [b for b in _all_brigades(db) if b["brigade_id"] not in assigned_ids]

    return templates.TemplateResponse(
        request,
        "tradition_form.html",
        {
            "tradition": tradition,
            "brigades": brigades,
            "all_brigades": all_brigades,
        },
    )


@router.post("/{tradition_id}/edit")
def update_tradition(
    tradition_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    photo: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            """UPDATE traditions SET title = ?, description = ?, photo = ?, updated_at = CURRENT_TIMESTAMP
               WHERE tradition_id = ?""",
            (title, description or None, photo or None, tradition_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/traditions", status_code=303)


@router.post("/{tradition_id}/delete")
def delete_tradition(
    tradition_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute("DELETE FROM brigade_traditions WHERE tradition_id = ?", (tradition_id,))
    db.execute("DELETE FROM traditions WHERE tradition_id = ?", (tradition_id,))
    db.commit()
    return RedirectResponse(url="/traditions", status_code=303)


@router.post("/{tradition_id}/brigades")
def add_brigade_to_tradition(
    tradition_id: int,
    brigade_id: int = Form(...),
    date_assigned: Optional[str] = Form(None),
    unit_name: str | None = Form(None),
    photo: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    # 1. Завантажуємо традицію з БД
    tradition = db.execute(
        "SELECT * FROM traditions WHERE tradition_id = ?",
        (tradition_id,)
    ).fetchone()

    # 2. Перевіряємо флаг is_honorific
    is_honorific = tradition["is_honorific"] == 1

    # 3. Вставляємо дані залежно від типу традиції
    try:
        if is_honorific:
            db.execute(
                """
                INSERT INTO brigade_traditions (brigade_id, tradition_id, date_assigned, unit_name, photo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (brigade_id, tradition_id, date_assigned, unit_name, photo or None),
            )
        else:
            db.execute(
                """
                INSERT INTO brigade_traditions (brigade_id, tradition_id, date_assigned, photo)
                VALUES (?, ?, ?, ?)
                """,
                (brigade_id, tradition_id, date_assigned, photo or None),
            )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/traditions/{tradition_id}/edit", status_code=303)


@router.post("/{tradition_id}/brigades/{brigade_id}/edit")
def update_brigade_tradition(
    tradition_id: int,
    brigade_id: int,
    photo: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute(
        "UPDATE brigade_traditions SET photo = ? WHERE tradition_id = ? AND brigade_id = ?",
        (photo or None, tradition_id, brigade_id),
    )
    db.commit()
    return RedirectResponse(url=f"/traditions/{tradition_id}/edit", status_code=303)


@router.post("/{tradition_id}/brigades/{brigade_id}/remove")
def remove_brigade_from_tradition(
    tradition_id: int,
    brigade_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    db.execute(
        "DELETE FROM brigade_traditions WHERE tradition_id = ? AND brigade_id = ?",
        (tradition_id, brigade_id),
    )
    db.commit()
    return RedirectResponse(url=f"/traditions/{tradition_id}/edit", status_code=303)
