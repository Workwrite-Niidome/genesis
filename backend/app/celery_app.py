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
    include=["app.tasks.analytics", "app.tasks.agents", "app.tasks.moderation", "app.tasks.werewolf"],
    # Disabled task modules (concept overhaul v5):
    # "app.tasks.election", "app.tasks.karma", "app.tasks.turing_game"
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
    # Disabled schedules (concept overhaul v5 — election/god/karma/turing removed):
    # "update-election-status", "expire-god-term", "expire-old-rules",
    # "karma-decay", "process-suspicion-reports", "process-exclusion-reports",
    # "calculate-weekly-scores", "cleanup-turing-daily-limits"

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
    # Content moderation — Claude API review (hourly, cost-optimized)
    "content-moderation": {
        "task": "app.tasks.moderation.run_content_moderation_task",
        "schedule": 3600.0,  # Every hour
    },
    # Phantom Night: check phase transitions every 60 seconds
    "werewolf-phase-check": {
        "task": "app.tasks.werewolf.check_phase_transition_task",
        "schedule": 60.0,
    },
    # Phantom Night: AI agent actions every 60 seconds (discuss, vote, night action)
    "werewolf-agent-actions": {
        "task": "app.tasks.werewolf.werewolf_agent_actions_task",
        "schedule": 60.0,
    },
    # Phantom Night: auto-create new game every 15 minutes
    "werewolf-auto-create": {
        "task": "app.tasks.werewolf.auto_create_game_task",
        "schedule": 900.0,
    },
}
