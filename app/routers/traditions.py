import sqlite3

from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.templates import templates

router = APIRouter(prefix="/traditions", tags=["traditions"])


@router.get("")
def list_traditions(request: Request, db: sqlite3.Connection = Depends(get_db)):
    traditions = db.execute(
        """SELECT t.tradition_id, t.title, t.description, COUNT(bt.brigade_id) AS brigade_count
           FROM traditions t
           LEFT JOIN brigade_traditions bt ON t.tradition_id = bt.tradition_id
           GROUP BY t.tradition_id
           ORDER BY t.title"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "traditions_list.html", {"traditions": traditions}
    )