import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NotAuthenticated
from app.routers import auth, battles, brigades, equipment, stats, traditions

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Портал бригад ЗСУ")

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    SESSION_SECRET = "dev-insecure-secret-change-me"
    # ASCII-only: a Cyrillic message here can crash startup on consoles whose
    # stdout encoding isn't UTF-8 (e.g. default Windows cp1252 console).
    print(
        "WARNING: SESSION_SECRET is not set - using an insecure default for local "
        "development. Set your own SESSION_SECRET in production."
    )
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


@app.exception_handler(NotAuthenticated)
def redirect_to_login(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(auth.router)
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