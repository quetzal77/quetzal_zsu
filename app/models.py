from typing import Optional

from pydantic import BaseModel


class BrigadeIn(BaseModel):
    name: str
    description: Optional[str] = None
    military_branch_id: Optional[int] = None
    corps_id: Optional[int] = None
    territorial_command_id: Optional[int] = None
    troop_type_id: Optional[int] = None
    formed_date: Optional[str] = None
    flag_date: Optional[str] = None
    location_id: Optional[int] = None
    emblem_file: Optional[str] = None
