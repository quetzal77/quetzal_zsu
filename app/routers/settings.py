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
            {"col": "founded_date", "label": "Дата заснування", "type": "date"},
            {"col": "hq_location_id", "label": "Штаб", "type": "location"},
            {"col": "emblem_file", "label": "Герб"},
            {"col": "flag_file", "label": "Прапор"},
            {"col": "patch_file", "label": "Нарукавний знак"},
            {"col": "beret_badge_file", "label": "Беретний знак"},
        ],
        # Усі extra_cols фізично живуть у military_branch_details, на яку
        # military_branches посилається через details_id (fk_col нижче) —
        # _lookup_rows/create/update/delete підтягують/пишуть їх туди по ключу.
        "details": {"table": "military_branch_details", "id_col": "details_id", "fk_col": "details_id"},
        "wide": True,  # забагато полів в рядку для вузької колонки
        "dependents": [
            {"table": "brigades", "fk_col": "military_branch_id", "name_col": "name", "label": "бригад"},
        ],
    },
    "army-corps": {
        "table": "army_corps", "id_col": "corps_id", "name_col": "corps_name",
        "label": "Армійські корпуси", "singular": "армійський корпус",
        "extra_cols": [
            {"col": "founded_date", "label": "Дата заснування", "type": "date"},
            {"col": "emblem_file", "label": "Емблема"},
        ],
        "wide": True,  # рівно 4 елементи (назва + 2 поля + дії) — влазить в один рядок гріда
        "list_max_height": "150px",  # видно не більше ~3 рядків корпусів, решта — скролом
        "dependents": [
            {"table": "brigades", "fk_col": "corps_id", "name_col": "name", "label": "бригад"},
        ],
    },
    "territorial-commands": {
        "table": "territorial_commands", "id_col": "command_id", "name_col": "command_name",
        "label": "Оперативні командування", "singular": "оперативне командування",
        "dependents": [
            {"table": "brigades", "fk_col": "territorial_command_id", "name_col": "name", "label": "бригад"},
        ],
    },
    "troop-types": {
        "table": "troop_types", "id_col": "type_id", "name_col": "type_name",
        "label": "Типи родів військ", "singular": "тип роду військ",
        "extra_cols": [
            {"col": "collar_emblem_file", "label": "Комірна емблема"},
        ],
        "dependents": [
            {"table": "brigades", "fk_col": "troop_type_id", "name_col": "name", "label": "бригад"},
        ],
    },
    "unit-types": {
        "table": "unit_types", "id_col": "unit_type_id", "name_col": "type_name",
        "label": "Типи з'єднань", "singular": "тип з'єднання",
        "dependents": [
            {"table": "brigades", "fk_col": "unit_type_id", "name_col": "name", "label": "бригад"},
        ],
    },
    "equipment-types": {
        "table": "equipment_types", "id_col": "equipment_type_id", "name_col": "type_name",
        "label": "Типи спорядження", "singular": "тип спорядження",
        "dependents": [
            {"table": "equipment", "fk_col": "equipment_type_id", "name_col": "name", "label": "техніки"},
        ],
    },
}

# Довідники поза _LOOKUP_TABLES (регіони, локації) мають свій власний набір
# FK-залежностей — використовується тим самим _find_dependents нижче.
_REGION_DEPENDENTS = [
    {"table": "locations", "fk_col": "region_id", "name_col": "city_name", "label": "локацій"},
]
_LOCATION_DEPENDENTS = [
    # hq_location_id живе в military_branch_details, тому назва роду військ
    # підтягується JOIN'ом через сирий SQL (звичайний table/fk_col/name_col
    # тут не підходить — назва і FK лежать у різних таблицях).
    {
        "sql": """SELECT mb.branch_name AS name
                  FROM military_branch_details mbd
                  JOIN military_branches mb ON mb.details_id = mbd.details_id
                  WHERE mbd.hq_location_id = ?""",
        "label": "штабів родів військ",
    },
    {"table": "brigades", "fk_col": "location_id", "name_col": "name", "label": "бригад"},
    {"table": "battles", "fk_col": "location_id", "name_col": "name", "label": "боїв"},
]


def _find_dependents(db: sqlite3.Connection, dependents: list, item_id: int) -> list[str]:
    """Для кожного залежного FK шукає рядки, що посилаються на item_id, і формує
    список рядків виду "бригад: «81-ша...», «93-тя...»" для повідомлення про помилку."""
    blockers = []
    for dep in dependents:
        if "sql" in dep:
            rows = db.execute(dep["sql"], (item_id,)).fetchall()
        else:
            rows = db.execute(
                f"SELECT {dep['name_col']} AS name FROM {dep['table']} WHERE {dep['fk_col']} = ?",
                (item_id,),
            ).fetchall()
        if rows:
            names = ", ".join(f"«{r['name']}»" for r in rows)
            blockers.append(f"{dep['label']}: {names}")
    return blockers


def _delete_blocked_message(item_label: str, blockers: list) -> str:
    return f"Не можна видалити {item_label} — на нього посилаються {'; '.join(blockers)}."


def _optional_int(value: Optional[str]) -> Optional[int]:
    """HTML <select> sends "" for the "—" option; FastAPI's int parsing rejects
    that before it reaches our code, so these fields must arrive as str."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _lookup_config(slug: str) -> dict:
    config = _LOOKUP_TABLES.get(slug)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown lookup table")
    return config


def _lookup_rows(db: sqlite3.Connection, slug: str):
    config = _lookup_config(slug)
    name_col = config["name_col"]
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    details = config.get("details")
    # CAST(... AS INTEGER) читає провідний номер ("11-й корпус" -> 11), тому
    # сортування виходить числове (8 перед 11), а не лексикографічне; для назв
    # без провідного числа CAST дає 0 і сортування падає на текстовий регістр.
    if details:
        # extra_cols фізично лежать в details['table'], приєднаній по details_id.
        extra_select = "".join(f", d.{col}" for col in extra_cols)
        return db.execute(
            f"SELECT t.{config['id_col']} AS id, t.{name_col} AS name{extra_select} "
            f"FROM {config['table']} t "
            f"LEFT JOIN {details['table']} d ON t.{details['fk_col']} = d.{details['id_col']} "
            f"ORDER BY CAST(t.{name_col} AS INTEGER), t.{name_col} COLLATE UKRAINIAN"
        ).fetchall()
    extra_select = "".join(f", {col}" for col in extra_cols)
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
    return RedirectResponse(url="/settings#panel-regions", status_code=303)


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
    return RedirectResponse(url="/settings#panel-regions", status_code=303)


@router.post("/regions/{region_id}/delete")
def delete_region(
    request: Request,
    region_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    blockers = _find_dependents(db, _REGION_DEPENDENTS, region_id)
    if blockers:
        region = db.execute(
            "SELECT region_name FROM regions WHERE region_id = ?", (region_id,)
        ).fetchone()
        context = _settings_context(db)
        context["delete_blocked_message"] = _delete_blocked_message(f"регіон «{region['region_name']}»", blockers)
        context["scroll_to"] = "panel-regions"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    try:
        db.execute("DELETE FROM regions WHERE region_id = ?", (region_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings#panel-regions", status_code=303)


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
        context["scroll_to"] = "panel-locations"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    try:
        db.execute(
            "INSERT INTO locations (city_name, region_id) VALUES (?, ?)",
            (city_name, region_id),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings#panel-locations", status_code=303)


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
        context["scroll_to"] = "panel-locations"
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
    return RedirectResponse(url="/settings#panel-locations", status_code=303)


@router.post("/locations/{location_id}/delete")
def delete_location(
    request: Request,
    location_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    blockers = _find_dependents(db, _LOCATION_DEPENDENTS, location_id)
    if blockers:
        location = db.execute(
            "SELECT city_name FROM locations WHERE location_id = ?", (location_id,)
        ).fetchone()
        context = _settings_context(db)
        context["delete_blocked_message"] = _delete_blocked_message(f"локацію «{location['city_name']}»", blockers)
        context["scroll_to"] = "panel-locations"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    try:
        db.execute("DELETE FROM locations WHERE location_id = ?", (location_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/settings#panel-locations", status_code=303)


def _extra_col_values(config: dict, form_values: dict) -> list:
    """Convert raw form strings to DB-ready values per column type: "location"
    columns are FK ints (like brigades' Optional[str] -> Optional[int] fields),
    everything else (text/date, both stored as plain TEXT) passes through as-is."""
    values = []
    for ec in config.get("extra_cols", []):
        raw = form_values.get(ec["col"])
        values.append(_optional_int(raw) if ec.get("type") == "location" else (raw or None))
    return values


@router.post("/lookups/{slug}")
def create_lookup_item(
    slug: str,
    name: str = Form(...),
    founded_date: Optional[str] = Form(None),
    hq_location_id: Optional[str] = Form(None),
    emblem_file: Optional[str] = Form(None),
    flag_file: Optional[str] = Form(None),
    patch_file: Optional[str] = Form(None),
    beret_badge_file: Optional[str] = Form(None),
    collar_emblem_file: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    form_values = {
        "founded_date": founded_date, "hq_location_id": hq_location_id,
        "emblem_file": emblem_file, "flag_file": flag_file,
        "patch_file": patch_file, "beret_badge_file": beret_badge_file,
        "collar_emblem_file": collar_emblem_file,
    }
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    values = _extra_col_values(config, form_values)
    details = config.get("details")
    try:
        if details:
            # extra_cols ідуть в окрему деталізуючу таблицю, а сама назва —
            # в основну, з посиланням на щойно створений рядок деталей.
            if extra_cols:
                placeholders = ", ".join("?" for _ in extra_cols)
                cur = db.execute(
                    f"INSERT INTO {details['table']} ({', '.join(extra_cols)}) VALUES ({placeholders})", values
                )
            else:
                cur = db.execute(f"INSERT INTO {details['table']} DEFAULT VALUES")
            details_id = cur.lastrowid
            db.execute(
                f"INSERT INTO {config['table']} ({config['name_col']}, {details['fk_col']}) VALUES (?, ?)",
                (name, details_id),
            )
        else:
            cols = [config["name_col"], *extra_cols]
            placeholders = ", ".join("?" for _ in cols)
            db.execute(
                f"INSERT INTO {config['table']} ({', '.join(cols)}) VALUES ({placeholders})", [name, *values]
            )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/settings#panel-{slug}", status_code=303)


@router.post("/lookups/{slug}/{item_id}/edit")
def update_lookup_item(
    slug: str,
    item_id: int,
    name: str = Form(...),
    founded_date: Optional[str] = Form(None),
    hq_location_id: Optional[str] = Form(None),
    emblem_file: Optional[str] = Form(None),
    flag_file: Optional[str] = Form(None),
    patch_file: Optional[str] = Form(None),
    beret_badge_file: Optional[str] = Form(None),
    collar_emblem_file: Optional[str] = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    form_values = {
        "founded_date": founded_date, "hq_location_id": hq_location_id,
        "emblem_file": emblem_file, "flag_file": flag_file,
        "patch_file": patch_file, "beret_badge_file": beret_badge_file,
        "collar_emblem_file": collar_emblem_file,
    }
    extra_cols = [ec["col"] for ec in config.get("extra_cols", [])]
    values = _extra_col_values(config, form_values)
    details = config.get("details")
    try:
        if details:
            row = db.execute(
                f"SELECT {details['fk_col']} AS details_id FROM {config['table']} WHERE {config['id_col']} = ?",
                (item_id,),
            ).fetchone()
            details_id = row["details_id"] if row else None
            if details_id is None:
                # Захисний випадок (напр. старий рядок без details) — створюємо
                # рядок деталей і прив'язуємо його замість оновлення неіснуючого.
                if extra_cols:
                    placeholders = ", ".join("?" for _ in extra_cols)
                    cur = db.execute(
                        f"INSERT INTO {details['table']} ({', '.join(extra_cols)}) VALUES ({placeholders})", values
                    )
                else:
                    cur = db.execute(f"INSERT INTO {details['table']} DEFAULT VALUES")
                details_id = cur.lastrowid
                db.execute(
                    f"UPDATE {config['table']} SET {details['fk_col']} = ? WHERE {config['id_col']} = ?",
                    (details_id, item_id),
                )
            elif extra_cols:
                set_clause = ", ".join(f"{col} = ?" for col in extra_cols)
                db.execute(
                    f"UPDATE {details['table']} SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
                    f"WHERE {details['id_col']} = ?",
                    [*values, details_id],
                )
            db.execute(
                f"UPDATE {config['table']} SET {config['name_col']} = ?, updated_at = CURRENT_TIMESTAMP "
                f"WHERE {config['id_col']} = ?",
                (name, item_id),
            )
        else:
            set_clause = ", ".join(f"{col} = ?" for col in [config["name_col"], *extra_cols])
            db.execute(
                f"UPDATE {config['table']} SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
                f"WHERE {config['id_col']} = ?",
                [name, *values, item_id],
            )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/settings#panel-{slug}", status_code=303)


@router.post("/lookups/{slug}/{item_id}/delete")
def delete_lookup_item(
    request: Request,
    slug: str,
    item_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _user: str = Depends(require_login),
):
    config = _lookup_config(slug)
    blockers = _find_dependents(db, config.get("dependents", []), item_id)
    if blockers:
        item = db.execute(
            f"SELECT {config['name_col']} AS name FROM {config['table']} WHERE {config['id_col']} = ?",
            (item_id,),
        ).fetchone()
        context = _settings_context(db)
        item_label = f"{config['singular']} «{item['name']}»" if item else config["singular"]
        context["delete_blocked_message"] = _delete_blocked_message(item_label, blockers)
        context["scroll_to"] = f"panel-{slug}"
        return templates.TemplateResponse(request, "settings.html", context, status_code=400)
    details = config.get("details")
    try:
        details_id = None
        if details:
            row = db.execute(
                f"SELECT {details['fk_col']} AS details_id FROM {config['table']} WHERE {config['id_col']} = ?",
                (item_id,),
            ).fetchone()
            details_id = row["details_id"] if row else None
        db.execute(f"DELETE FROM {config['table']} WHERE {config['id_col']} = ?", (item_id,))
        if details_id is not None:
            db.execute(f"DELETE FROM {details['table']} WHERE {details['id_col']} = ?", (details_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=f"/settings#panel-{slug}", status_code=303)
