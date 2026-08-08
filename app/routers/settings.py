import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth import require_login
from app.database import get_db
from app.templates import templates

router = APIRouter(prefix="/settings", tags=["settings"])

# Прості довідники: одна назва-колонка (+ опційно кілька додаткових текстових
# колонок, напр. посилання на зображення). Слаг у URL валідується проти цього
# білого списку, тому інтерполяція назв таблиці/колонки в SQL нижче безпечна.
_LOOKUP_TABLES = {
    "military-branches": {
        "table": "military_branches", "id_col": "branch_id", "name_col": "branch_name",
        "label": "Роди військ", "singular": "рід військ",
        "extra_cols": [
            {"col": "emblem_file", "label": "Герб"},
            {"col": "flag_file", "label": "Прапор"},
        ],
        "wide": True,  # забагато полів в рядку (назва + герб + прапор) для вузької колонки
    },
    "army-corps": {
        "table": "army_corps", "id_col": "corps_id", "name_col": "corps_name",
        "label": "Армійські корпуси", "singular": "армійський корпус",
    },
    "territorial-commands": {
        "table": "territorial_commands", "id_col": "command_id", "name_col": "command_name",
        "label": "Оперативні командування", "singular": "оперативне командування",
    },
    "troop-types": {
        "table": "troop_types", "id_col": "type_id", "name_col": "type_name",
        "label": "Типи бригад", "singular": "тип бригади",
    },
    "unit-types": {
        "table": "unit_types", "id_col": "unit_type_id", "name_col": "type_name",
        "label": "Типи з'єднань", "singular": "тип з'єднання",
    },
    "equipment-types": {
        "table": "equipment_types", "id_col": "equipment_type_id", "name_col": "type_name",
        "label": "Типи спорядження", "singular": "тип спорядження",
    },
}


def _lookup_config(slug: str) -> dict:
    config = _LOOKUP_TABLES.get(slug)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown lookup table")
    return config


def _lookup_rows(db: sqlite3.Connection, slug: str):
    config = _lookup_config(slug)
    name_col = config["name_col"]
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    extra_select = "".join(f", {col}" for col in extra_cols)
    # CAST(... AS INTEGER) читає провідний номер ("11-й корпус" -> 11), тому
    # сортування виходить числове (8 перед 11), а не лексикографічне; для назв
    # без провідного числа CAST дає 0 і сортування падає на текстовий регістр.
    return db.execute(
        f"SELECT {config['id_col']} AS id, {name_col} AS name{extra_select} "
        f"FROM {config['table']} ORDER BY CAST({name_col} AS INTEGER), {name_col} COLLATE UKRAINIAN"
    ).fetchall()


def _regions(db: sqlite3.Connection):
    return db.execute(
        "SELECT region_id, region_name FROM regions ORDER BY region_name COLLATE UKRAINIAN"
    ).fetchall()


def _locations(db: sqlite3.Connection):
    return db.execute(
        """SELECT l.location_id, l.city_name, l.region_id, r.region_name
           FROM locations l
           JOIN regions r ON l.region_id = r.region_id
           ORDER BY l.city_name COLLATE UKRAINIAN"""
    ).fetchall()


def _settings_context(db: sqlite3.Connection) -> dict:
    lookups = [
        {
            "slug": slug,
            "label": config["label"],
            "singular": config["singular"],
            "rows": _lookup_rows(db, slug),
            "extra_cols": config.get("extra_cols", []),
            "wide": config.get("wide", False),
        }
        for slug, config in _LOOKUP_TABLES.items()
    ]
    return {"regions": _regions(db), "locations": _locations(db), "lookups": lookups}


@router.get("")
def settings_page(
    request: Request, db: sqlite3.Connection = Depends(get_db), _user: str = Depends(require_login)
):
    return templates.TemplateResponse(request, "settings.html", _settings_context(db))


@router.post("/regions")
def create_region(
    region_name: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute("INSERT INTO regions (region_name) VALUES (?)", (region_name,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/regions/{region_id}/edit")
def update_region(
    region_id: int,
    region_name: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute(
            "UPDATE regions SET region_name = ?, updated_at = CURRENT_TIMESTAMP WHERE region_id = ?",
            (region_name, region_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/regions/{region_id}/delete")
def delete_region(
    region_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute("DELETE FROM regions WHERE region_id = ?", (region_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/locations")
def create_location(
    request: Request,
    city_name: str = Form(...),
    region_id: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    duplicate = db.execute(
        "SELECT 1 FROM locations WHERE city_name = ? AND region_id = ?",
        (city_name, region_id),
    ).fetchone()
    if duplicate:
        context = _settings_context(db)
        context["location_error"] = f"Місто «{city_name}» вже є в цьому регіоні"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    try:
        db.execute(
            "INSERT INTO locations (city_name, region_id) VALUES (?, ?)",
            (city_name, region_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/locations/{location_id}/edit")
def update_location(
    request: Request,
    location_id: int,
    city_name: str = Form(...),
    region_id: int = Form(...),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    duplicate = db.execute(
        "SELECT 1 FROM locations WHERE city_name = ? AND region_id = ? AND location_id != ?",
        (city_name, region_id, location_id),
    ).fetchone()
    if duplicate:
        context = _settings_context(db)
        context["location_error"] = f"Місто «{city_name}» вже є в цьому регіоні"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    try:
        db.execute(
            """UPDATE locations SET city_name = ?, region_id = ?, updated_at = CURRENT_TIMESTAMP
               WHERE location_id = ?""",
            (city_name, region_id, location_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/locations/{location_id}/delete")
def delete_location(
    location_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    try:
        db.execute("DELETE FROM locations WHERE location_id = ?", (location_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/lookups/{slug}")
def create_lookup_item(
    slug: str,
    name: str = Form(...),
    emblem_file: Optional[str] = Form(None),
    flag_file: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    form_values = {"emblem_file": emblem_file, "flag_file": flag_file}
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    cols = [config["name_col"], *extra_cols]
    values = [name, *(form_values.get(col) or None for col in extra_cols)]
    placeholders = ", ".join("?" for _ in cols)
    try:
        db.execute(
            f"INSERT INTO {config['table']} ({', '.join(cols)}) VALUES ({placeholders})", values
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/lookups/{slug}/{item_id}/edit")
def update_lookup_item(
    slug: str,
    item_id: int,
    name: str = Form(...),
    emblem_file: Optional[str] = Form(None),
    flag_file: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    form_values = {"emblem_file": emblem_file, "flag_file": flag_file}
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    set_clause = ", ".join(f"{col} = ?" for col in [config["name_col"], *extra_cols])
    values = [name, *(form_values.get(col) or None for col in extra_cols), item_id]
    try:
        db.execute(
            f"UPDATE {config['table']} SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
            f"WHERE {config['id_col']} = ?",
            values,
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/lookups/{slug}/{item_id}/delete")
def delete_lookup_item(
    slug: str,
    item_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    try:
        db.execute(f"DELETE FROM {config['table']} WHERE {config['id_col']} = ?", (item_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings", status_code=303)
