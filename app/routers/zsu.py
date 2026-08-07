from fastapi import APIRouter, Request

from app.templates import templates

router = APIRouter(tags=["zsu"])

# Статична структура ЗСУ для сторінки-довідника. Плашки поки не клікабельні —
# data-slug лишається заготовкою під майбутній роутинг (напр. /zsu/{slug}).
# Функціональність готова лише для "Сили безпілотних систем" — решта плашок
# заморожені (disabled) до появи відповідних сторінок.
ACTIVE_SLUGS = {"unmanned-systems-forces"}
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
            {"slug": "special-operations-forces", "mark": "ССО", "name": "Сили спеціальних операцій"},
            {"slug": "territorial-defense-forces", "mark": "СТрО", "name": "Сили територіальної оборони"},
            {"slug": "logistics-forces", "mark": "СЛ", "name": "Сили логістики"},
            {"slug": "support-forces", "mark": "СП", "name": "Сили підтримки"},
            {"slug": "medical-forces", "mark": "МС", "name": "Медичні сили"},
            {"slug": "unmanned-systems-forces", "mark": "СБС", "name": "Сили безпілотних систем"},
        ],
    },
    {
        "title": "Окремі роди військ ЗСУ",
        "items": [
            {"slug": "air-assault-troops", "mark": "ДШВ", "name": "Десантно-штурмові війська"},
            {"slug": "signal-cyber-troops", "mark": "ВЗК", "name": "Війська зв’язку та кібербезпеки"},
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
