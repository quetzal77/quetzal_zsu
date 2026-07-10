from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import battles, brigades, equipment, stats, traditions

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Портал бригад ЗСУ")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(brigades.router)
app.include_router(battles.router)
app.include_router(equipment.router)
app.include_router(traditions.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return RedirectResponse(url="/brigades")


@app.get("/favicon.ico")
def favicon():
    # browsers request /favicon.ico directly regardless of <link rel="icon">;
    # serve the same tryzub image so that request stops 404-ing in the logs.
    return FileResponse(BASE_DIR / "static" / "img" / "zsu-tryzub.png", media_type="image/png")