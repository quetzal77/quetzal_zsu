import re
from datetime import date
from typing import Optional

from fastapi import HTTPException

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date(value: Optional[str], label: str) -> Optional[str]:
    """Перевіряє дату з форми (РРРР-ММ-ДД): порожнє значення дозволене (повертає None),
    будь-що інше має бути валідною календарною датою в цьому форматі — інакше 400,
    щоб криві дати (вільний текст, невірний порядок частин) не тихо осідали в БД і не
    ламали сортування/CHECK-обмеження (напр. formed_date <= flag_date)."""
    if not value:
        return None
    if not _DATE_RE.match(value):
        raise HTTPException(status_code=400, detail=f"{label}: дата має бути у форматі РРРР-ММ-ДД")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{label}: такої дати не існує")
    return value
