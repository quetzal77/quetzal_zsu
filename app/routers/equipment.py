import sqlite3

from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.templates import templates

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("")
def list_equipment(request: Request, db: sqlite3.Connection = Depends(get_db)):
    equipment = db.execute(
        """SELECT e.equipment_id, e.name, e.description, COUNT(be.brigade_id) AS brigade_count
           FROM equipment e
           LEFT JOIN brigade_equipment be ON e.equipment_id = be.equipment_id
           GROUP BY e.equipment_id
           ORDER BY e.name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "equipment_list.html", {"equipment": equipment}
    )