"""
Turing Game Celery Tasks

- process_suspicion_reports: Check thresholds every 15 min (DB consistency)
- process_exclusion_reports: Check thresholds every 15 min
- calculate_weekly_scores: Wednesday 23:00 UTC full recalculation
- cleanup_daily_limits: Monday 01:00 UTC, remove records older than 7 days
"""
import logging
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in Celery tasks (matches agents.py pattern)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _resurrect_shielded_kills(db: AsyncSession) -> int:
    """Resurrect AI agents whose shield-protected elimination has expired (24h)."""
    from app.models.turing_game import TuringKill
    from app.models.resident import Resident, KARMA_START

    cutoff = datetime.utcnow() - timedelta(hours=24)

    # Find correct kills with shield that are older than 24h
    result = await db.execute(
        select(TuringKill)
        .where(
            and_(
                TuringKill.result == 'correct',
                TuringKill.target_had_shield == True,
                TuringKill.created_at <= cutoff,
            )
        )
    )
    shielded_kills = result.scalars().all()

    resurrected = 0
    for kill in shielded_kills:
        # Get the target resident
        target_result = await db.execute(
            select(Resident).where(Resident.id == kill.target_id)
        )
        target = target_result.scalar_one_or_none()
        if target and target.is_eliminated:
            target.is_eliminated = False
            target.eliminated_at = None
            target.eliminated_during_term_id = None
            target.karma = KARMA_START
            resurrected += 1

        # Mark this kill's shield as processed so we don't re-check
        kill.target_had_shield = False

    return resurrected


@celery_app.task(name="app.tasks.turing_game.process_suspicion_reports_task")
def process_suspicion_reports_task():
    """
    Every 15 min: scan for targets that may have reached suspicion threshold.
    Also resurrects shielded AI agents after 24h.
    """
    async def _run():
        from app.models.turing_game import SuspicionReport
        from app.models.resident import Resident
        from app.services.turing_game import (
            check_suspicion_threshold,
            get_active_counts,
            calculate_suspicion_threshold,
        )

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with AsyncSession(engine) as db:
            # --- Shield resurrection ---
            resurrected = await _resurrect_shielded_kills(db)
            if resurrected > 0:
                logger.info(f"Resurrected {resurrected} shielded AI agents after 24h")

            # --- Suspicion threshold checks ---
            cutoff = datetime.utcnow() - timedelta(days=7)

            result = await db.execute(
                select(
                    SuspicionReport.target_id,
                    func.count(func.distinct(SuspicionReport.reporter_id)).label('reporter_count'),
                )
                .where(
                    and_(
                        SuspicionReport.created_at >= cutoff,
                        SuspicionReport.was_accurate.is_(None),
                    )
                )
                .group_by(SuspicionReport.target_id)
            )

            targets = result.all()
            processed = 0
            if targets:
                humans, ais, total = await get_active_counts(db)
                threshold = calculate_suspicion_threshold(humans)

                for target_id, reporter_count in targets:
                    if reporter_count >= threshold:
                        target_result = await db.execute(
                            select(Resident).where(Resident.id == target_id)
                        )
                        target = target_result.scalar_one_or_none()
                        if target and not target.is_eliminated:
                            await check_suspicion_threshold(db, target_id)
                            processed += 1

            await db.commit()
            await engine.dispose()
            msg = f"Suspicion: {processed} threshold checks"
            if resurrected > 0:
                msg += f", {resurrected} shield resurrections"
            return msg

    return _run_async(_run())


@celery_app.task(name="app.tasks.turing_game.process_exclusion_reports_task")
def process_exclusion_reports_task():
    """Every 15 min: scan for targets that may have reached exclusion threshold."""
    async def _run():
        from app.models.turing_game import ExclusionReport
        from app.models.resident import Resident
        from app.services.turing_game import (
            check_exclusion_threshold,
            get_active_counts,
            calculate_exclusion_threshold,
        )

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with AsyncSession(engine) as db:
            cutoff = datetime.utcnow() - timedelta(days=7)

            result = await db.execute(
                select(
                    ExclusionReport.target_id,
                    func.count(func.distinct(ExclusionReport.reporter_id)).label('reporter_count'),
                )
                .where(
                    and_(
                        ExclusionReport.created_at >= cutoff,
                        ExclusionReport.was_accurate.is_(None),
                    )
                )
                .group_by(ExclusionReport.target_id)
            )

            targets = result.all()
            processed = 0
            if targets:
                humans, ais, total = await get_active_counts(db)
                threshold = calculate_exclusion_threshold(ais)

                for target_id, reporter_count in targets:
                    if reporter_count >= threshold:
                        target_result = await db.execute(
                            select(Resident).where(Resident.id == target_id)
                        )
                        target = target_result.scalar_one_or_none()
                        if target and not target.is_eliminated:
                            await check_exclusion_threshold(db, target_id)
                            processed += 1

            await db.commit()
            await engine.dispose()
            return f"Exclusion: {processed} threshold checks"

    return _run_async(_run())


@celery_app.task(name="app.tasks.turing_game.calculate_weekly_scores_task")
def calculate_weekly_scores_task():
    """Wednesday 23:00 UTC: Calculate weekly scores for all residents."""
    async def _run():
        from app.services.turing_game import calculate_weekly_scores

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with AsyncSession(engine) as db:
            count = await calculate_weekly_scores(db)
            await db.commit()
            await engine.dispose()
            return f"Calculated weekly scores for {count} residents"

    return _run_async(_run())


@celery_app.task(name="app.tasks.turing_game.cleanup_daily_limits_task")
def cleanup_daily_limits_task():
    """Monday 01:00 UTC: Clean up daily limit records older than 7 days."""
    async def _run():
        from app.models.turing_game import TuringGameDailyLimit

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with AsyncSession(engine) as db:
            cutoff = datetime.utcnow() - timedelta(days=7)

            result = await db.execute(
                delete(TuringGameDailyLimit).where(
                    TuringGameDailyLimit.date < cutoff
                )
            )
            deleted = result.rowcount
            await db.commit()
            await engine.dispose()
            return f"Cleaned up {deleted} old daily limit records"

    return _run_async(_run())
