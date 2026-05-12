from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import LOTTERIES, ROOT_DIR, get_lottery
from .database import get_draws, init_db, upsert_draws
from .fetchers.cwl import FetchError, fetch_cwl_draws
from .services.analytics import calculate_stats, recommend


app = FastAPI(title="彩票历史开奖分析工具", version="1.0.0")
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/src", StaticFiles(directory=FRONTEND_DIR / "src"), name="frontend-src")


@app.on_event("startup")
async def startup() -> None:
    init_db()
    scheduler.add_job(sync_all, "cron", hour=22, minute=30, id="daily_sync", replace_existing=True)
    scheduler.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler.shutdown(wait=False)


@app.get("/api/lotteries")
def lotteries() -> list[dict]:
    return [
        {
            "key": item.key,
            "name": item.name,
            "number_min": item.number_min,
            "number_max": item.number_max,
            "special_min": item.special_min,
            "special_max": item.special_max,
        }
        for item in LOTTERIES.values()
    ]


@app.get("/api/lottery/{lottery_type}/draws")
def api_draws(lottery_type: str, limit: int = Query(default=500, ge=1, le=2000)) -> dict:
    config = _config_or_404(lottery_type)
    return {"lottery": config.key, "draws": get_draws(config.key, limit=limit)}


@app.post("/api/lottery/{lottery_type}/sync")
async def api_sync(lottery_type: str, page_size: int = Query(default=500, ge=10, le=500)) -> dict:
    config = _config_or_404(lottery_type)
    try:
        draws = await fetch_cwl_draws(config, page_size=page_size)
    except (FetchError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"抓取失败：{exc}") from exc
    changed = upsert_draws(config.key, draws)
    return {"lottery": config.key, "fetched": len(draws), "changed": changed, "source": "中国福彩网"}


@app.get("/api/lottery/{lottery_type}/stats")
def api_stats(lottery_type: str, window: int = Query(default=30, ge=5, le=500)) -> dict:
    config = _config_or_404(lottery_type)
    return calculate_stats(config, get_draws(config.key, limit=2000), window=window)


@app.get("/api/lottery/{lottery_type}/recommend")
def api_recommend(
    lottery_type: str,
    count: int = Query(default=5, ge=1, le=20),
    window: int = Query(default=30, ge=5, le=500),
) -> dict:
    config = _config_or_404(lottery_type)
    draws = get_draws(config.key, limit=2000)
    if not draws:
        raise HTTPException(status_code=404, detail="暂无开奖数据，请先执行同步。")
    return recommend(config, draws, count=count, window=window)


async def sync_all() -> None:
    for config in LOTTERIES.values():
        try:
            draws = await fetch_cwl_draws(config, page_size=500)
            upsert_draws(config.key, draws)
        except Exception:
            continue


def _config_or_404(lottery_type: str):
    try:
        return get_lottery(lottery_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")