import sqlite3

from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.templates import templates

router = APIRouter(prefix="/battles", tags=["battles"])


def _battle_status(start_date, end_date):
    if end_date:
        return "завершено"
    if start_date:
        return "триває"
    return None


@router.get("")
def list_battles(request: Request, db: sqlite3.Connection = Depends(get_db)):
    battles = db.execute(
        """SELECT b.battle_id, b.name, b.start_date, b.end_date, b.description, l.city_name, r.region_name
           FROM battles b
           LEFT JOIN locations l ON b.location_id = l.location_id
           LEFT JOIN regions r ON l.region_id = r.region_id
           ORDER BY b.start_date"""
    ).fetchall()
    return templates.TemplateResponse(request, "battles_list.html", {"battles": battles})


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
        """SELECT br.brigade_id, br.name
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