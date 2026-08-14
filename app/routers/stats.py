import sqlite3

from fastapi import APIRouter, Depends, Request

from app.auth import require_login
from app.database import get_db
from app.templates import templates

router = APIRouter(tags=["stats"])


def _distribution(db: sqlite3.Connection, query: str) -> list[dict]:
    rows = db.execute(query).fetchall()
    total = sum(r["count"] for r in rows) or 1
    return [
        {"label": r["label"], "count": r["count"], "pct": round(r["count"] * 100 / total, 1)}
        for r in rows
    ]


def _battle_status(start_date: str | None, end_date: str | None) -> str | None:
    if end_date:
        return "завершено"
    if start_date:
        return "триває"
    return None


@router.get("/stats")
def stats(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
    _username: str = Depends(require_login),
):
    counts = {
        "brigades": db.execute("SELECT COUNT(*) FROM brigades").fetchone()[0],
        "battles": db.execute("SELECT COUNT(*) FROM battles").fetchone()[0],
        "equipment": db.execute("SELECT COUNT(*) FROM equipment").fetchone()[0],
        "traditions": db.execute("SELECT COUNT(*) FROM traditions").fetchone()[0],
    }

    branch_dist = _distribution(
        db,
        """SELECT COALESCE(mb.branch_name, 'Без роду військ') AS label, COUNT(*) AS count
           FROM brigades b
           LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
           GROUP BY mb.branch_id
           ORDER BY count DESC""",
    )

    command_dist = _distribution(
        db,
        """SELECT COALESCE(tc.command_name, 'Без командування') AS label, COUNT(*) AS count
           FROM brigades b
           LEFT JOIN territorial_commands tc ON b.territorial_command_id = tc.command_id
           GROUP BY tc.command_id
           ORDER BY count DESC""",
    )

    battle_rows = db.execute(
        """SELECT b.battle_id, b.name, b.start_date, b.end_date, l.city_name
           FROM battles b
           LEFT JOIN locations l ON b.location_id = l.location_id
           ORDER BY b.start_date DESC
           LIMIT 5"""
    ).fetchall()
    recent_battles = [
        {
            "battle_id": r["battle_id"],
            "name": r["name"],
            "period": (r["start_date"] or "") + (f" – {r['end_date']}" if r["end_date"] else ""),
            "place": r["city_name"],
            "status": _battle_status(r["start_date"], r["end_date"]),
        }
        for r in battle_rows
    ]

    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "counts": counts,
            "branch_dist": branch_dist,
            "command_dist": command_dist,
            "recent_battles": recent_battles,
        },
    )
