import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_db
from app.templates import templates

router = APIRouter(tags=["zsu"])

# Статична структура ЗСУ для сторінки-довідника. Плашки поки не клікабельні —
# data-slug лишається заготовкою під майбутній роутинг (напр. /zsu/{slug}).
# Функціональність готова лише для "Сили безпілотних систем" і "Сили спеціальних
# операцій" — решта плашок заморожені (disabled) до появи відповідних сторінок.
ACTIVE_SLUGS = {"unmanned-systems-forces", "special-operations-forces"}
STRUCTURE = [
    {
        "title": "Загальна структура",
        "items": [
            {"slug": "general-staff", "mark": "ГШ", "name": "Генеральний штаб Збройних Сил України",
             "hint": "Орган стратегічного управління"},
            {"slug": "joint-forces-command", "mark": "КОС", "name": "Командування об’єднаних сил ЗС України",
             "hint": "Оперативне командування"},
        ],
    },
    {
        "title": "Види ЗСУ",
        "items": [
            {"slug": "ground-forces", "mark": "СВ", "name": "Сухопутні війська"},
            {"slug": "air-force", "mark": "ПС", "name": "Повітряні Сили"},
            {"slug": "navy", "mark": "ВМС", "name": "Військово-Морські Сили"},
        ],
    },
    {
        "title": "Окремі роди сил ЗСУ",
        "items": [
            {"slug": "special-operations-forces", "mark": "ССО", "name": "Сили спеціальних операцій",
             "icon": "forces/sso_patch.png"},
            {"slug": "territorial-defense-forces", "mark": "СТрО", "name": "Сили територіальної оборони"},
            {"slug": "logistics-forces", "mark": "СЛ", "name": "Сили логістики"},
            {"slug": "support-forces", "mark": "СП", "name": "Сили підтримки"},
            {"slug": "medical-forces", "mark": "МС", "name": "Медичні сили"},
            {"slug": "unmanned-systems-forces", "mark": "СБС", "name": "Сили безпілотних систем",
             "icon": "forces/sbs_patch.png"},
        ],
    },
    {
        "title": "Окремі роди військ ЗСУ",
        "items": [
            {"slug": "air-assault-troops", "mark": "ДШВ", "name": "Десантно-штурмові війська"},
            {"slug": "signal-cyber-troops", "mark": "ВЗК", "name": "Війська зв’язку та кібербезпеки"},
        ],
    },
    {
        "title": "Спецслужби та органи безпеки",
        "items": [
            {"slug": "sbu", "mark": "СБУ", "name": "Служба безпеки України"},
            {"slug": "gur", "mark": "ГУР", "name": "Головне управління розвідки"},
            {"slug": "szru", "mark": "СЗР", "name": "Зовнішня розвідка України"},
        ],
    },
    {
        "title": "Правоохоронні органи та формування з правоохоронними функціями",
        "items": [
            {"slug": "ngu", "mark": "НГУ", "name": "Національна гвардія України"},
            {"slug": "dpsu", "mark": "ДПСУ", "name": "Державна прикордонна служба України"},
            {"slug": "npu", "mark": "НПУ", "name": "Національна поліція України"},
            {"slug": "dsns", "mark": "ДСНС", "name": "Державна служба України з надзвичайних ситуацій"},
        ],
    },
]


@router.get("/zsu")
def zsu(request: Request):
    structure = [
        {
            **group,
            "items": [
                {**item, "active": item["slug"] in ACTIVE_SLUGS}
                for item in group["items"]
            ],
        }
        for group in STRUCTURE
    ]
    return templates.TemplateResponse(request, "zsu.html", {"structure": structure})


def _find_item(slug: str) -> dict:
    for group in STRUCTURE:
        for item in group["items"]:
            if item["slug"] == slug:
                return item
    raise HTTPException(status_code=404)


@router.get("/zsu/{slug}")
def zsu_branch(slug: str, request: Request, db: sqlite3.Connection = Depends(get_db)):
    # Активні лише слаги з ACTIVE_SLUGS — решта плашок на /zsu заморожені
    # (disabled) і не лінкуються сюди, але прямий запит все одно має 404-ити.
    if slug not in ACTIVE_SLUGS:
        raise HTTPException(status_code=404)
    item = _find_item(slug)

    # Назва пункту структури співпадає з military_branches.branch_name —
    # звідти береться герб/прапор/штаб роду військ (див. /settings).
    branch = db.execute(
        """SELECT mb.*, l.city_name, r.region_name
           FROM military_branches mb
           LEFT JOIN locations l ON mb.hq_location_id = l.location_id
           LEFT JOIN regions r ON l.region_id = r.region_id
           WHERE mb.branch_name = ?""",
        (item["name"],),
    ).fetchone()

    brigades = db.execute(
        """SELECT b.brigade_id, b.name, b.emblem_file, b.flag_date,
                  tt.type_name AS troop_type_name,
                  tt.collar_emblem_file AS troop_type_collar_file,
                  (
                      SELECT bt.unit_name
                      FROM brigade_traditions bt
                      JOIN traditions t ON t.tradition_id = bt.tradition_id
                      WHERE bt.brigade_id = b.brigade_id
                        AND t.is_honorific = 1
                  ) AS honorific_name
           FROM brigades b
           LEFT JOIN troop_types tt ON b.troop_type_id = tt.type_id
           WHERE b.military_branch_id = ?
           ORDER BY
               CASE WHEN tt.type_name IS NULL THEN 1 ELSE 0 END,
               tt.type_name COLLATE UKRAINIAN,
               CAST(b.name AS INTEGER), b.name""",
        (branch["branch_id"] if branch else -1,),
    ).fetchall()

    return templates.TemplateResponse(
        request, "zsu_branch.html", {"item": item, "branch": branch, "brigades": brigades}
    )
