"""晨鐘 MorningBell — 每天 5 分鐘，看懂美股。

FastAPI 入口：掛載 API 與前端靜態檔。
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
from routers import api

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="晨鐘 MorningBell", version="0.1.0")

db.init()
app.include_router(api.router, prefix="/api")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # SW 需由根路徑供應，scope 才能涵蓋整站
    return FileResponse(ROOT / "static" / "sw.js", media_type="application/javascript")
