from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from app.core.config import settings
from app.api.v1 import analytics, health, predictions, history, diseases, auth, internal
from app.ml.model_loader import ml_manager
from app.services.keep_alive_service import ping_keep_alive_job
from app.utils.logger import logger

scheduler: BackgroundScheduler | None = None


def _start_keep_alive_scheduler() -> None:
    global scheduler
    if scheduler and scheduler.running:
        return

    try:
        timezone = ZoneInfo(settings.KEEP_ALIVE_TIMEZONE)
        trigger = CronTrigger.from_crontab(settings.KEEP_ALIVE_CRON, timezone=timezone)
    except Exception as exc:
        logger.exception("Invalid keep-alive schedule; scheduler disabled: %s", exc)
        return

    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        ping_keep_alive_job,
        trigger=trigger,
        id="keep-alive",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Keep-alive scheduler started with cron '%s' in %s.",
        settings.KEEP_ALIVE_CRON,
        settings.KEEP_ALIVE_TIMEZONE,
    )


def _shutdown_keep_alive_scheduler() -> None:
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Keep-alive scheduler stopped.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend for Deep Learning based Plant Disease Classification (Apple Leaf)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Geliştirme için Flutter isteklerine izin (Production'da daraltılmalı)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    ml_manager.load_model()
    _start_keep_alive_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    _shutdown_keep_alive_scheduler()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})

app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_PREFIX}/predictions", tags=["Predictions"])
app.include_router(history.router, prefix=f"{settings.API_V1_PREFIX}/history", tags=["History"])
app.include_router(diseases.router, prefix=f"{settings.API_V1_PREFIX}/diseases", tags=["Diseases"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(internal.router, prefix="/internal", tags=["Internal"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Plant Disease Classifier API"}

@app.head("/")
def head_root():
    return None
