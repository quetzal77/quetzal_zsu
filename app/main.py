from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import battles, brigades, equipment, locations, traditions

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Портал бригад ЗСУ")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(brigades.router)
app.include_router(battles.router)
app.include_router(equipment.router)
app.include_router(traditions.router)
app.include_router(locations.router)


@app.get("/")
def root():
    return RedirectResponse(url="/brigades")