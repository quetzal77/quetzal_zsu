import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_login
from app.database import get_db
from app.sanitize import sanitize_html
from app.templates import templates

router = APIRouter(prefix="/brigades", tags=["brigades"])


def _optional_int(value: Optional[str]) -> Optional[int]:
    """HTML <select> sends "" for the "—" option; FastAPI's int parsing rejects
    that before it reaches our code, so these fields must arrive as str."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _lookups(db: sqlite3.Connection) -> dict:
    return {
        "military_branches": db.execute(
            "SELECT branch_id, branch_name FROM military_branches ORDER BY branch_name"
        ).fetchall(),
        "army_corps": db.execute(
            "SELECT corps_id, corps_name FROM army_corps ORDER BY corps_name"
        ).fetchall(),
        "territorial_commands": db.execute(
            "SELECT command_id, command_name FROM territorial_commands ORDER BY command_name"
        ).fetchall(),
        "troop_types": db.execute(
            "SELECT type_id, type_name FROM troop_types ORDER BY type_name"
        ).fetchall(),
        "locations": db.execute(
            """SELECT l.location_id, l.city_name, r.region_name
               FROM locations l JOIN regions r ON l.region_id = r.region_id
               ORDER BY l.city_name"""
        ).fetchall(),
    }


@router.get("")
def list_brigades(
    request: Request,
    military_branch_id: Optional[str] = None,
    corps_id: Optional[str] = None,
    territorial_command_id: Optional[str] = None,
    troop_type_id: Optional[str] = None,
    region_id: Optional[str] = None,
    q: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    military_branch_id = _optional_int(military_branch_id)
    corps_id = _optional_int(corps_id)
    territorial_command_id = _optional_int(territorial_command_id)
    troop_type_id = _optional_int(troop_type_id)
    region_id = _optional_int(region_id)

    query = """
        SELECT b.brigade_id, b.name, b.emblem_file, b.formed_date, b.flag_date,
               mb.branch_name, ac.corps_name, l.city_name,
               (
                   SELECT bt.unit_name
                   FROM brigade_traditions bt
                   JOIN traditions t ON t.tradition_id = bt.tradition_id
                   WHERE bt.brigade_id = b.brigade_id
                     AND t.is_honorific = 1
               ) AS honorific_name
        FROM brigades b
        LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
        LEFT JOIN army_corps ac ON b.corps_id = ac.corps_id
        LEFT JOIN locations l ON b.location_id = l.location_id
        WHERE 1=1
    """
    params: list = []
    if military_branch_id:
        query += " AND b.military_branch_id = ?"
        params.append(military_branch_id)
    if corps_id:
        query += " AND b.corps_id = ?"
        params.append(corps_id)
    if territorial_command_id:
        query += " AND b.territorial_command_id = ?"
        params.append(territorial_command_id)
    if troop_type_id:
        query += " AND b.troop_type_id = ?"
        params.append(troop_type_id)
    if region_id:
        query += " AND l.region_id = ?"
        params.append(region_id)
    if q:
        # ловимо збіг як на початку назви, так і на початку будь-якого
        # окремого слова всередині неї (розділювачі — пробіл або дефіс)
        query += " AND (b.name LIKE ? OR b.name LIKE ? OR b.name LIKE ?)"
        params.extend([f"{q}%", f"% {q}%", f"%-{q}%"])
    # CAST(name AS INTEGER) бере лише провідний номер бригади ("142-га ..." -> 142),
    # тому сортування виходить числове (15 перед 142), а не лексикографічне ("142" перед "15").
    query += " ORDER BY CAST(b.name AS INTEGER), b.name"

    brigades = db.execute(query, params).fetchall()
    regions = db.execute("SELECT region_id, region_name FROM regions ORDER BY region_name").fetchall()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "brigades": brigades,
            "regions": regions,
            **_lookups(db),
            "filters": {
                "military_branch_id": military_branch_id,
                "corps_id": corps_id,
                "territorial_command_id": territorial_command_id,
                "troop_type_id": troop_type_id,
                "region_id": region_id,
            },
        },
    )


@router.get("/new")
def new_brigade_form(
    request: Request, db: sqlite3.Connection = Depends(get_db), _user: str = Depends(require_login)
):
    return templates.TemplateResponse(
        request,
        "brigade_form.html",
        {"brigade": None, **_lookups(db)},
    )


@router.post("/new")
def create_brigade(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    military_branch_id: Optional[str] = Form(None),
    corps_id: Optional[str] = Form(None),
    territorial_command_id: Optional[str] = Form(None),
    troop_type_id: Optional[str] = Form(None),
    location_id: Optional[str] = Form(None),
    formed_date: Optional[str] = Form(None),
    flag_date: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        cur = db.execute(
            """INSERT INTO brigades
               (name, description, military_branch_id, corps_id, territorial_command_id,
                troop_type_id, location_id, formed_date, flag_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(military_branch_id),
                _optional_int(corps_id),
                _optional_int(territorial_command_id),
                _optional_int(troop_type_id),
                _optional_int(location_id),
                formed_date or None,
                flag_date or None,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/brigades/{cur.lastrowid}", status_code=303)


@router.get("/{brigade_id}")
def brigade_detail(brigade_id: int, request: Request, db: sqlite3.Connection = Depends(get_db)):
    brigade = db.execute(
        """SELECT b.*, mb.branch_name, ac.corps_name, tc.command_name, tt.type_name,
                  l.city_name, r.region_name,
                  (
                      SELECT bt.unit_name
                      FROM brigade_traditions bt
                      JOIN traditions t ON t.tradition_id = bt.tradition_id
                      WHERE bt.brigade_id = b.brigade_id
                        AND t.is_honorific = 1
                  ) AS honorific_name
           FROM brigades b
           LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
           LEFT JOIN army_corps ac ON b.corps_id = ac.corps_id
           LEFT JOIN territorial_commands tc ON b.territorial_command_id = tc.command_id
           LEFT JOIN troop_types tt ON b.troop_type_id = tt.type_id
           LEFT JOIN locations l ON b.location_id = l.location_id
           LEFT JOIN regions r ON l.region_id = r.region_id
           WHERE b.brigade_id = ?""",
        (brigade_id,),
    ).fetchone()

    battles = db.execute(
        """SELECT bt.battle_id, bt.name
           FROM brigade_battles bb
           JOIN battles bt ON bb.battle_id = bt.battle_id
           WHERE bb.brigade_id = ?
           ORDER BY bt.start_date""",
        (brigade_id,),
    ).fetchall()

    equipment = db.execute(
        """SELECT e.equipment_id, e.name, e.description
           FROM brigade_equipment be
           JOIN equipment e ON be.equipment_id = e.equipment_id
           WHERE be.brigade_id = ?
           ORDER BY e.name""",
        (brigade_id,),
    ).fetchall()

    photos = db.execute(
        """SELECT photo_id, file_path, position
           FROM brigade_photos
           WHERE brigade_id = ?
           ORDER BY position""",
        (brigade_id,),
    ).fetchall()

    traditions = db.execute(
        """SELECT t.tradition_id, t.title, t.description, bt.unit_name, bt.date_assigned
        FROM brigade_traditions bt
        JOIN traditions t ON t.tradition_id = bt.tradition_id
        WHERE bt.brigade_id = ?
        ORDER BY t.title""",
        (brigade_id,)
    ).fetchall()

    return templates.TemplateResponse(
        request,
        "brigade_detail.html",
        {"brigade": brigade, "battles": battles, "equipment": equipment, "photos": photos, "traditions": traditions},
    )


@router.post("/{brigade_id}/edit")
def update_brigade(
        brigade_id: int,
        name: str = Form(...),
        description: Optional[str] = Form(None),
        military_branch_id: Optional[str] = Form(None),
        corps_id: Optional[str] = Form(None),
        territorial_command_id: Optional[str] = Form(None),
        troop_type_id: Optional[str] = Form(None),
        location_id: Optional[str] = Form(None),
        formed_date: Optional[str] = Form(None),
        flag_date: Optional[str] = Form(None),
        photo_0: Optional[str] = Form(None),
        photo_1: Optional[str] = Form(None),
        photo_2: Optional[str] = Form(None),
        db: sqlite3.Connection = Depends(get_db),
        _user: str = Depends(require_login),
):
    try:
        db.execute(
            """UPDATE brigades SET
                   name = ?, description = ?, military_branch_id = ?, corps_id = ?,
                   territorial_command_id = ?, troop_type_id = ?, location_id = ?,
                   formed_date = ?, flag_date = ?, updated_at = CURRENT_TIMESTAMP
               WHERE brigade_id = ?""",
            (
                name,
                sanitize_html(description) or None,
                _optional_int(military_branch_id),
                _optional_int(corps_id),
                _optional_int(territorial_command_id),
                _optional_int(troop_type_id),
                _optional_int(location_id),
                formed_date or None,
                flag_date or None,
                brigade_id,
            ),
        )

        photos = [photo_0, photo_1, photo_2]

        existing = db.execute(
            """SELECT photo_id, file_path, position
               FROM brigade_photos
               WHERE brigade_id = ?
               ORDER BY position""",
            (brigade_id,),
        ).fetchall()

        for idx in range(3):
            new_path = photos[idx] or ""
            position = idx + 1  # ← 1, 2, 3 замість 0, 1, 2

            if new_path:
                if idx < len(existing):
                    db.execute(
                        """UPDATE brigade_photos
                           SET file_path = ?, position = ?
                           WHERE photo_id = ?""",
                        (new_path, position, existing[idx][0]),
                    )
                else:
                    db.execute(
                        """INSERT INTO brigade_photos (brigade_id, file_path, position)
                           VALUES (?, ?, ?)""",
                        (brigade_id, new_path, position),
                    )
            else:
                if idx < len(existing):
                    db.execute(
                        "DELETE FROM brigade_photos WHERE photo_id = ?",
                        (existing[idx][0],),
                    )

        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/brigades/{brigade_id}", status_code=303)



@router.get("/{brigade_id}/edit")
def edit_brigade_form(
    brigade_id: int,
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    brigade = db.execute(
        "SELECT * FROM brigades WHERE brigade_id = ?",
        (brigade_id,),
    ).fetchone()

    raw_photos = db.execute(
        """SELECT photo_id, brigade_id, file_path, position
           FROM brigade_photos
           WHERE brigade_id = ?
           ORDER BY position""",
        (brigade_id,),
    ).fetchall()

    photos = [
        {
            "photo_id": row[0],
            "brigade_id": row[1],
            "file_path": row[2],
            "position": row[3],
        }
        for row in raw_photos
    ]

    return templates.TemplateResponse(
        request,
        "brigade_form.html",
        {
            "brigade": brigade,
            "photos": photos,
            **_lookups(db),
        },
    )
