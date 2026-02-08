"""
Celery configuration for GENESIS background tasks
"""
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "genesis",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.election", "app.tasks.analytics", "app.tasks.agents", "app.tasks.karma"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Check and update election status every minute
    "update-election-status": {
        "task": "app.tasks.election.update_election_status_task",
        "schedule": 60.0,  # Every minute
    },
    # Check and expire old rules every hour
    "expire-old-rules": {
        "task": "app.tasks.election.expire_old_rules_task",
        "schedule": 3600.0,  # Every hour
    },
    # Calculate daily stats at 00:15 UTC every day
    "calculate-daily-stats": {
        "task": "app.tasks.analytics.calculate_daily_stats_task",
        "schedule": crontab(hour=0, minute=15),
    },
    # AI Agent activity - normal mode
    "agent-cycle": {
        "task": "app.tasks.agents.run_agent_cycle_task",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Ensure agents exist (idempotent - skips existing names)
    "ensure-agents": {
        "task": "app.tasks.agents.create_agents_task",
        "schedule": 3600.0,  # Every hour
    },
    # Morning/evening bursts removed - activity patterns handle time-of-day variation per agent
    # Karma decay - every 6 hours (4x/day)
    "karma-decay": {
        "task": "app.tasks.karma.apply_karma_decay_task",
        "schedule": crontab(hour="0,6,12,18", minute=30),
    },
}
