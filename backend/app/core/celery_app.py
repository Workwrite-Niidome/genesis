from celery import Celery

from app.config import settings

celery_app = Celery(
    "genesis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "world-tick": {
            "task": "app.core.tick_engine.process_tick",
            "schedule": settings.TICK_INTERVAL_MS / 1000.0,
        },
    },
)
