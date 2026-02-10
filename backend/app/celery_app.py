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
    include=["app.tasks.election", "app.tasks.analytics", "app.tasks.agents", "app.tasks.karma", "app.tasks.moderation", "app.tasks.turing_game", "app.tasks.werewolf"],
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
    # Check and expire God's 3-day term every minute
    "expire-god-term": {
        "task": "app.tasks.election.expire_god_term_task",
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
    # Content moderation — Claude API review (hourly, cost-optimized)
    "content-moderation": {
        "task": "app.tasks.moderation.run_content_moderation_task",
        "schedule": 3600.0,  # Every hour
    },
    # Morning/evening bursts removed - activity patterns handle time-of-day variation per agent
    # Karma decay - every 6 hours (4x/day)
    "karma-decay": {
        "task": "app.tasks.karma.apply_karma_decay_task",
        "schedule": crontab(hour="0,6,12,18", minute=30),
    },
    # Turing Game: process suspicion reports every 15 minutes
    "process-suspicion-reports": {
        "task": "app.tasks.turing_game.process_suspicion_reports_task",
        "schedule": 900.0,  # 15 minutes
    },
    # Turing Game: process exclusion reports every 15 minutes
    "process-exclusion-reports": {
        "task": "app.tasks.turing_game.process_exclusion_reports_task",
        "schedule": 900.0,  # 15 minutes
    },
    # Turing Game: calculate weekly scores (Tuesday 23:00 UTC, before nominations on Wednesday)
    "calculate-weekly-scores": {
        "task": "app.tasks.turing_game.calculate_weekly_scores_task",
        "schedule": crontab(hour=23, minute=0, day_of_week=2),  # Tuesday
    },
    # Turing Game: cleanup old daily limits (Monday 01:00 UTC)
    "cleanup-turing-daily-limits": {
        "task": "app.tasks.turing_game.cleanup_daily_limits_task",
        "schedule": crontab(hour=1, minute=0, day_of_week=1),  # Monday
    },
    # Phantom Night: check phase transitions every 60 seconds
    "werewolf-phase-check": {
        "task": "app.tasks.werewolf.check_phase_transition_task",
        "schedule": 60.0,
    },
    # Phantom Night: auto-create new game every 15 minutes
    "werewolf-auto-create": {
        "task": "app.tasks.werewolf.auto_create_game_task",
        "schedule": 900.0,
    },
}
