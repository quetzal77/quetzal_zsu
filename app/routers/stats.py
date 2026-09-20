import sqlite3

from fastapi import APIRouter, Depends, Request

from app.auth import require_login
from app.database import get_db
from app.templates import templates

router = APIRouter(tags=["stats"])


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

    branch_table = _branch_unit_table(db)
    brigades_by_year = _brigades_by_year(db)

    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "counts": counts,
            "branch_table": branch_table,
            "brigades_by_year": brigades_by_year,
        },
    )


_UNIT_TYPE_COLUMNS = [
    ("brigade", "Бригада", "Бригад"),
    ("regiment", "Полк", "Полків"),
    ("battalion", "Батальйон", "Батальйонів"),
    ("center", "Центр", "Центрів"),
]


def _cell(names: list[str]) -> dict:
    return {"count": len(names), "names": names}


def _branch_unit_table(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        """SELECT COALESCE(mb.branch_name, 'Без роду військ') AS branch_name,
                  b.name AS brigade_name, ut.type_name AS unit_type_name,
                  ac.corps_name AS corps_name
           FROM brigades b
           LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
           LEFT JOIN unit_types ut ON b.unit_type_id = ut.unit_type_id
           LEFT JOIN army_corps ac ON b.corps_id = ac.corps_id
           ORDER BY branch_name, CAST(b.name AS INTEGER), b.name"""
    ).fetchall()

    branches: dict[str, dict] = {}
    for r in rows:
        branch = branches.setdefault(
            r["branch_name"],
            {"corps": {}, "unit_types": {key: [] for key, _, _ in _UNIT_TYPE_COLUMNS}, "all": []},
        )
        branch["all"].append(r["brigade_name"])
        if r["corps_name"]:
            branch["corps"].setdefault(r["corps_name"], []).append(r["brigade_name"])
        for key, type_name, _ in _UNIT_TYPE_COLUMNS:
            if r["unit_type_name"] == type_name:
                branch["unit_types"][key].append(r["brigade_name"])

    table = []
    for branch_name, data in branches.items():
        row = {
            "branch": branch_name,
            "corps": _cell(sorted(data["corps"].keys())),
            "total": _cell(data["all"]),
        }
        for key, _, _ in _UNIT_TYPE_COLUMNS:
            row[key] = _cell(data["unit_types"][key])
        table.append(row)

    table.sort(key=lambda r: r["total"]["count"], reverse=True)
    return table


def _brigade_word(count: int) -> str:
    """Ukrainian plural form of "бригада" for the given count."""
    n = abs(count) % 100
    n1 = n % 10
    if 11 <= n <= 14:
        return "бригад"
    if n1 == 1:
        return "бригада"
    if 2 <= n1 <= 4:
        return "бригади"
    return "бригад"


def _brigade_sort_key(name: str):
    """Числове сортування назв з'єднань (25, 46, 95, 147), як і в реєстрі."""
    try:
        return (0, int(name))
    except ValueError:
        return (1, name)


def _brigades_by_year(db: sqlite3.Connection) -> list[dict]:
    """Один рік — одна дата на бригаду: brigade_date (коли підрозділ став
    бригадою), а якщо порожньо — formed_date (дата заснування). Інші типи
    з'єднань (полки, батальйони тощо) не враховуються."""
    rows = db.execute(
        """SELECT b.name AS brigade_name,
                  strftime('%Y', COALESCE(b.brigade_date, b.formed_date)) AS year
           FROM brigades b
           JOIN unit_types ut ON b.unit_type_id = ut.unit_type_id
           WHERE ut.type_name = 'Бригада'
             AND COALESCE(b.brigade_date, b.formed_date) IS NOT NULL"""
    ).fetchall()

    years: dict[str, list[str]] = {}
    for r in rows:
        if r["year"]:
            years.setdefault(r["year"], []).append(r["brigade_name"])

    result = []
    for year, names in sorted(years.items(), key=lambda kv: kv[0]):
        result.append(
            {
                "year": year,
                "count": len(names),
                "word": _brigade_word(len(names)),
                "names": sorted(names, key=_brigade_sort_key),
            }
        )
    return result
