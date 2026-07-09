import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.database import get_db

router = APIRouter(tags=["locations"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/locations")
def list_locations(request: Request, db: sqlite3.Connection = Depends(get_db)):
    locations = db.execute(
        """SELECT l.location_id, l.city_name, r.region_name,
                  COUNT(b.brigade_id) AS brigade_count
           FROM locations l
           JOIN regions r ON l.region_id = r.region_id
           LEFT JOIN brigades b ON b.location_id = l.location_id
           GROUP BY l.location_id
           ORDER BY r.region_name, l.city_name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "locations_list.html", {"locations": locations}
    )


@router.get("/regions")
def list_regions(request: Request, db: sqlite3.Connection = Depends(get_db)):
    regions = db.execute(
        """SELECT r.region_id, r.region_name, COUNT(l.location_id) AS location_count
           FROM regions r
           LEFT JOIN locations l ON l.region_id = r.region_id
           GROUP BY r.region_id
           ORDER BY r.region_name"""
    ).fetchall()
    return templates.TemplateResponse(
        request, "regions_list.html", {"regions": regions}
    )