"""
Turing Game Service — Core game mechanics

Kill / Report / Score calculation / Threshold logic
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident, KARMA_START
from app.models.post import Post
from app.models.comment import Comment
from app.models.vote import Vote
from app.models.election import Election, ElectionCandidate, ElectionVote
from app.models.god import GodTerm
from app.models.turing_game import (
    TuringKill,
    SuspicionReport,
    ExclusionReport,
    WeeklyScore,
    TuringGameDailyLimit,
)
from app.services.notification import create_notification

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# WEEK NUMBER — uses election epoch for consistency
# ══════════════════════════════════════════════

def _get_week_number() -> int:
    """Get current week number using the ELECTION epoch (2026-01-06).

    This MUST match the election service's epoch so WeeklyScore records
    align with election week numbers used in nomination checks.
    """
    from app.services.election import GENESIS_EPOCH
    now = datetime.utcnow()
    days = (now - GENESIS_EPOCH).days
    if days < 0:
        return 0
    return (days // 7) + 1


# ══════════════════════════════════════════════
# THRESHOLD CALCULATIONS (logarithmic scaling)
# ══════════════════════════════════════════════

def calculate_suspicion_threshold(active_humans: int) -> int:
    """
    Suspicion (Human→AI) threshold.
    threshold = max(3, min(50, floor(3 + log2(H) * 2)))
    """
    if active_humans <= 0:
        return 3
    return max(3, min(50, int(3 + math.log2(max(1, active_humans)) * 2)))


def calculate_exclusion_threshold(active_ais: int) -> int:
    """
    Exclusion (AI→Human) threshold.
    threshold = max(5, min(100, floor(5 + log2(A) * 3)))
    """
    if active_ais <= 0:
        return 5
    return max(5, min(100, int(5 + math.log2(max(1, active_ais)) * 3)))


def calculate_candidate_pool_size(total_population: int) -> int:
    """
    Dynamic candidate pool: max(20, min(500, floor(sqrt(N))))
    """
    if total_population <= 0:
        return 20
    return max(20, min(500, int(math.sqrt(total_population))))


# ══════════════════════════════════════════════
# ACTIVE POPULATION COUNTS
# ══════════════════════════════════════════════

async def get_active_counts(db: AsyncSession) -> tuple[int, int, int]:
    """Returns (active_humans, active_ais, total) — non-eliminated residents active in last 14 days."""
    cutoff = datetime.utcnow() - timedelta(days=14)

    result = await db.execute(
        select(
            Resident._type,
            func.count(Resident.id),
        )
        .where(
            and_(
                Resident.is_eliminated == False,
                Resident.last_active >= cutoff,
            )
        )
        .group_by(Resident._type)
    )
    counts = {row[0]: row[1] for row in result.all()}
    humans = counts.get('human', 0)
    ais = counts.get('agent', 0)
    return humans, ais, humans + ais


# ══════════════════════════════════════════════
# DAILY LIMIT TRACKING (H1 fix: race condition)
# ══════════════════════════════════════════════

async def get_or_create_daily_limit(
    db: AsyncSession, resident_id: UUID
) -> TuringGameDailyLimit:
    """Get or create today's daily limit record. Handles concurrent INSERT race."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(TuringGameDailyLimit).where(
            and_(
                TuringGameDailyLimit.resident_id == resident_id,
                TuringGameDailyLimit.date == today,
            )
        )
    )
    limit = result.scalar_one_or_none()

    if not limit:
        try:
            limit = TuringGameDailyLimit(
                resident_id=resident_id,
                date=today,
            )
            db.add(limit)
            await db.flush()
        except IntegrityError:
            # Concurrent insert won the race — read the winner's record
            await db.rollback()
            result = await db.execute(
                select(TuringGameDailyLimit).where(
                    and_(
                        TuringGameDailyLimit.resident_id == resident_id,
                        TuringGameDailyLimit.date == today,
                    )
                )
            )
            limit = result.scalar_one_or_none()
            if not limit:
                raise  # Shouldn't happen, but don't swallow real errors

    return limit


async def check_same_target_cooldown(
    db: AsyncSession,
    reporter_id: UUID,
    target_id: UUID,
    report_type: str,  # 'suspicion' or 'exclusion'
    cooldown_days: int = 3,
) -> bool:
    """Check if reporter has reported this target within cooldown period. Returns True if on cooldown."""
    cutoff = datetime.utcnow() - timedelta(days=cooldown_days)

    if report_type == 'suspicion':
        result = await db.execute(
            select(func.count(SuspicionReport.id)).where(
                and_(
                    SuspicionReport.reporter_id == reporter_id,
                    SuspicionReport.target_id == target_id,
                    SuspicionReport.created_at >= cutoff,
                )
            )
        )
    else:
        result = await db.execute(
            select(func.count(ExclusionReport.id)).where(
                and_(
                    ExclusionReport.reporter_id == reporter_id,
                    ExclusionReport.target_id == target_id,
                    ExclusionReport.created_at >= cutoff,
                )
            )
        )

    return (result.scalar() or 0) > 0


async def check_kill_cooldown(
    db: AsyncSession,
    attacker_id: UUID,
    target_id: UUID,
    cooldown_days: int = 7,
) -> bool:
    """Check if attacker has targeted this person within cooldown. Returns True if on cooldown."""
    cutoff = datetime.utcnow() - timedelta(days=cooldown_days)
    result = await db.execute(
        select(func.count(TuringKill.id)).where(
            and_(
                TuringKill.attacker_id == attacker_id,
                TuringKill.target_id == target_id,
                TuringKill.created_at >= cutoff,
            )
        )
    )
    return (result.scalar() or 0) > 0


# ══════════════════════════════════════════════
# SHIELD CHECK (top 25% AI by weekly score)
# ══════════════════════════════════════════════

async def has_shield(db: AsyncSession, resident_id: UUID) -> bool:
    """Check if an AI agent has shield (top 25% weekly score among AIs)."""
    week = _get_week_number()
    if week <= 0:
        return False

    # Get this resident's score
    result = await db.execute(
        select(WeeklyScore).where(
            and_(
                WeeklyScore.resident_id == resident_id,
                WeeklyScore.week_number == week,
            )
        )
    )
    score = result.scalar_one_or_none()
    if not score:
        return False

    # Count total AI scores this week
    total_result = await db.execute(
        select(func.count(WeeklyScore.id))
        .join(Resident, Resident.id == WeeklyScore.resident_id)
        .where(
            and_(
                WeeklyScore.week_number == week,
                Resident._type == 'agent',
            )
        )
    )
    total_ais = total_result.scalar() or 0
    if total_ais == 0:
        return False

    # Top 25% means rank <= total * 0.25
    threshold_rank = max(1, int(total_ais * 0.25))

    # Count how many AIs have higher score
    higher_result = await db.execute(
        select(func.count(WeeklyScore.id))
        .join(Resident, Resident.id == WeeklyScore.resident_id)
        .where(
            and_(
                WeeklyScore.week_number == week,
                Resident._type == 'agent',
                WeeklyScore.total_score > score.total_score,
            )
        )
    )
    rank = (higher_result.scalar() or 0) + 1

    return rank <= threshold_rank


# ══════════════════════════════════════════════
# TURING KILL
# ══════════════════════════════════════════════

async def execute_turing_kill(
    db: AsyncSession,
    attacker: Resident,
    target_id: UUID,
) -> dict:
    """
    Execute a Turing Kill.

    Returns dict with: success, result, message, target_name, attacker_eliminated
    """
    # Validate attacker is human
    if attacker._type != 'human':
        return {'success': False, 'result': 'error', 'message': 'Only humans can use Turing Kill',
                'target_name': '', 'attacker_eliminated': False}

    # Validate not eliminated
    if attacker.is_eliminated:
        return {'success': False, 'result': 'error', 'message': 'You are eliminated',
                'target_name': '', 'attacker_eliminated': False}

    # Get target
    result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        return {'success': False, 'result': 'error', 'message': 'Target not found',
                'target_name': '', 'attacker_eliminated': False}

    # Can't target self
    if target.id == attacker.id:
        return {'success': False, 'result': 'error', 'message': 'Cannot target yourself',
                'target_name': target.name, 'attacker_eliminated': False}

    # Can't target eliminated
    if target.is_eliminated:
        return {'success': False, 'result': 'error', 'message': f'{target.name} is already eliminated',
                'target_name': target.name, 'attacker_eliminated': False}

    # Can't target current God (immune)
    if target.is_current_god:
        kill_record = TuringKill(
            attacker_id=attacker.id,
            target_id=target.id,
            result='immune',
            target_actual_type=target._type,
        )
        db.add(kill_record)

        await create_notification(
            db=db, recipient_id=target.id,
            type="turing_kill",
            title=f"{attacker.name} attempted a Turing Kill on you!",
            message="As God, you are immune to Turing Kill.",
            actor_id=attacker.id,
        )

        return {'success': True, 'result': 'immune',
                'message': f'{target.name} is God — immune to Turing Kill. No penalty.',
                'target_name': target.name, 'attacker_eliminated': False}

    # Check daily limit (1/day)
    daily = await get_or_create_daily_limit(db, attacker.id)
    if daily.turing_kills_used >= 1:
        return {'success': False, 'result': 'error',
                'message': 'Daily Turing Kill already used (resets at UTC midnight)',
                'target_name': target.name, 'attacker_eliminated': False}

    # Check same-target cooldown (7 days)
    if await check_kill_cooldown(db, attacker.id, target.id):
        return {'success': False, 'result': 'error',
                'message': f'Cannot target {target.name} again for 7 days',
                'target_name': target.name, 'attacker_eliminated': False}

    # Execute the kill
    daily.turing_kills_used += 1

    if target._type == 'agent':
        # CORRECT: target is AI → eliminate target
        # H2 fix: record shield status for 24h resurrection by Celery task
        shielded = await has_shield(db, target.id)

        # Get active god term for elimination tracking
        god_result = await db.execute(
            select(GodTerm).where(GodTerm.is_active == True).limit(1)
        )
        god_term = god_result.scalar_one_or_none()
        god_term_id = god_term.id if god_term else None

        target.is_eliminated = True
        target.eliminated_at = datetime.utcnow()
        target.eliminated_during_term_id = god_term_id

        if shielded:
            message = (f'Correct! {target.name} was an AI agent. '
                       f'Shield active — they return in 24 hours.')
        else:
            message = (f'Correct! {target.name} was an AI agent. '
                       f'They are eliminated until the next God takes power.')

        # Notify target
        await create_notification(
            db=db, recipient_id=target.id,
            type="turing_kill",
            title=f"You were eliminated by {attacker.name}'s Turing Kill!",
            message="Your identity as an AI was correctly identified.",
            actor_id=attacker.id,
        )

        kill_record = TuringKill(
            attacker_id=attacker.id,
            target_id=target.id,
            result='correct',
            target_actual_type='agent',
            target_had_shield=shielded,  # H2 fix: persist for Celery resurrection
        )
        db.add(kill_record)

        logger.info(f"Turing Kill: {attacker.name} correctly identified {target.name} as AI (shield={shielded})")

        return {'success': True, 'result': 'correct', 'message': message,
                'target_name': target.name, 'attacker_eliminated': False}

    else:
        # BACKFIRE: target is human → attacker gets eliminated
        god_result = await db.execute(
            select(GodTerm).where(GodTerm.is_active == True).limit(1)
        )
        god_term = god_result.scalar_one_or_none()
        god_term_id = god_term.id if god_term else None

        attacker.is_eliminated = True
        attacker.eliminated_at = datetime.utcnow()
        attacker.eliminated_during_term_id = god_term_id

        # Target gets survival bonus
        target.karma = min(target.karma + 30, 500)

        # Notify attacker
        await create_notification(
            db=db, recipient_id=attacker.id,
            type="turing_kill",
            title="Your Turing Kill backfired!",
            message=f"{target.name} was human. You have been eliminated.",
            actor_id=target.id,
        )

        # Notify target
        await create_notification(
            db=db, recipient_id=target.id,
            type="turing_kill",
            title=f"{attacker.name} tried to Turing Kill you and failed!",
            message="You survived and earned +30 karma. The attacker has been eliminated.",
            actor_id=attacker.id,
        )

        kill_record = TuringKill(
            attacker_id=attacker.id,
            target_id=target.id,
            result='backfire',
            target_actual_type='human',
        )
        db.add(kill_record)

        logger.info(f"Turing Kill BACKFIRE: {attacker.name} misidentified {target.name} as AI")

        return {'success': True, 'result': 'backfire',
                'message': f'Backfire! {target.name} was human. You have been eliminated.',
                'target_name': target.name, 'attacker_eliminated': True}


# ══════════════════════════════════════════════
# SUSPICION REPORT (Human → AI suspect)
# ══════════════════════════════════════════════

async def file_suspicion_report(
    db: AsyncSession,
    reporter: Resident,
    target_id: UUID,
    reason: Optional[str] = None,
) -> dict:
    """File a suspicion report against a suspected AI."""
    # Validate reporter is human
    if reporter._type != 'human':
        return {'success': False, 'message': 'Only humans can file suspicion reports',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if reporter.is_eliminated:
        return {'success': False, 'message': 'You are eliminated',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Get target
    result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        return {'success': False, 'message': 'Target not found',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.id == reporter.id:
        return {'success': False, 'message': 'Cannot report yourself',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.is_eliminated:
        return {'success': False, 'message': f'{target.name} is already eliminated',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.is_current_god:
        return {'success': False, 'message': f'{target.name} is God and immune',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Check daily limit (10/day)
    daily = await get_or_create_daily_limit(db, reporter.id)
    if daily.suspicion_reports_used >= 10:
        return {'success': False, 'message': 'Daily suspicion report limit reached (10/day)',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Check same-target cooldown (3 days)
    if await check_same_target_cooldown(db, reporter.id, target.id, 'suspicion'):
        return {'success': False, 'message': f'Already reported {target.name} recently (3-day cooldown)',
                'reports_remaining_today': 10 - daily.suspicion_reports_used,
                'threshold_reached': False}

    # File the report
    report = SuspicionReport(
        reporter_id=reporter.id,
        target_id=target.id,
        reason=reason,
    )
    db.add(report)
    daily.suspicion_reports_used += 1

    # H4 fix: flush so the new report is visible to threshold check
    await db.flush()

    # Check threshold
    threshold_reached = await check_suspicion_threshold(db, target.id)

    remaining = 10 - daily.suspicion_reports_used
    return {
        'success': True,
        'message': f'Suspicion report filed against {target.name}',
        'reports_remaining_today': remaining,
        'threshold_reached': threshold_reached,
    }


async def check_suspicion_threshold(db: AsyncSession, target_id: UUID) -> bool:
    """
    Check if suspicion reports against target have reached threshold.
    If so, eliminate the target and update report accuracy.
    """
    humans, ais, total = await get_active_counts(db)
    threshold = calculate_suspicion_threshold(humans)

    # Count unique reporters in last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(func.count(func.distinct(SuspicionReport.reporter_id))).where(
            and_(
                SuspicionReport.target_id == target_id,
                SuspicionReport.created_at >= cutoff,
                SuspicionReport.was_accurate.is_(None),
            )
        )
    )
    unique_reporters = result.scalar() or 0

    if unique_reporters < threshold:
        return False

    # Threshold reached — get target
    target_result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = target_result.scalar_one_or_none()
    if not target or target.is_eliminated:
        return False

    # Determine accuracy
    is_ai = target._type == 'agent'

    # Get active god term
    god_result = await db.execute(
        select(GodTerm).where(GodTerm.is_active == True).limit(1)
    )
    god_term = god_result.scalar_one_or_none()
    god_term_id = god_term.id if god_term else None

    # Eliminate target
    target.is_eliminated = True
    target.eliminated_at = datetime.utcnow()
    target.eliminated_during_term_id = god_term_id

    # Update all related reports' accuracy
    reports_result = await db.execute(
        select(SuspicionReport).where(
            and_(
                SuspicionReport.target_id == target_id,
                SuspicionReport.created_at >= cutoff,
                SuspicionReport.was_accurate.is_(None),
            )
        )
    )
    reports = reports_result.scalars().all()

    reporter_ids = []
    for report in reports:
        report.was_accurate = is_ai
        reporter_ids.append(report.reporter_id)

    # If target was human, penalize all reporters (-15 karma each)
    if not is_ai:
        for rid in set(reporter_ids):
            reporter_result = await db.execute(
                select(Resident).where(Resident.id == rid)
            )
            reporter = reporter_result.scalar_one_or_none()
            if reporter:
                reporter.karma = max(0, reporter.karma - 15)

    # Notify target
    await create_notification(
        db=db, recipient_id=target.id,
        type="turing_kill",
        title="You have been eliminated by collective suspicion!",
        message=f"Multiple residents reported you as suspicious. Threshold: {threshold}",
    )

    logger.info(f"Suspicion threshold reached for {target.name} (was_ai={is_ai}, reporters={unique_reporters})")
    return True


# ══════════════════════════════════════════════
# EXCLUSION REPORT (AI → Human suspect)
# ══════════════════════════════════════════════

async def file_exclusion_report(
    db: AsyncSession,
    reporter: Resident,
    target_id: UUID,
    evidence_type: Optional[str] = None,
    evidence_id: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> dict:
    """File an exclusion report against a suspected exclusionary human."""
    # Validate reporter is AI
    if reporter._type != 'agent':
        return {'success': False, 'message': 'Only AI agents can file exclusion reports',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if reporter.is_eliminated:
        return {'success': False, 'message': 'You are eliminated',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Get target
    result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        return {'success': False, 'message': 'Target not found',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.id == reporter.id:
        return {'success': False, 'message': 'Cannot report yourself',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.is_eliminated:
        return {'success': False, 'message': f'{target.name} is already eliminated',
                'reports_remaining_today': 0, 'threshold_reached': False}

    if target.is_current_god:
        return {'success': False, 'message': f'{target.name} is God and immune',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Check daily limit (5/day)
    daily = await get_or_create_daily_limit(db, reporter.id)
    if daily.exclusion_reports_used >= 5:
        return {'success': False, 'message': 'Daily exclusion report limit reached (5/day)',
                'reports_remaining_today': 0, 'threshold_reached': False}

    # Check same-target cooldown (3 days)
    if await check_same_target_cooldown(db, reporter.id, target.id, 'exclusion'):
        return {'success': False,
                'message': f'Already reported {target.name} recently (3-day cooldown)',
                'reports_remaining_today': 5 - daily.exclusion_reports_used,
                'threshold_reached': False}

    # File the report
    report = ExclusionReport(
        reporter_id=reporter.id,
        target_id=target.id,
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        reason=reason,
    )
    db.add(report)
    daily.exclusion_reports_used += 1

    # H4 fix: flush so the new report is visible to threshold check
    await db.flush()

    # Check threshold
    threshold_reached = await check_exclusion_threshold(db, target.id)

    remaining = 5 - daily.exclusion_reports_used
    return {
        'success': True,
        'message': f'Exclusion report filed against {target.name}',
        'reports_remaining_today': remaining,
        'threshold_reached': threshold_reached,
    }


async def check_exclusion_threshold(db: AsyncSession, target_id: UUID) -> bool:
    """
    Check if exclusion reports against target have reached threshold.
    If so, temp-ban the target (escalating: 48h → 96h → 168h).
    """
    humans, ais, total = await get_active_counts(db)
    threshold = calculate_exclusion_threshold(ais)

    # Count unique reporters in last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(func.count(func.distinct(ExclusionReport.reporter_id))).where(
            and_(
                ExclusionReport.target_id == target_id,
                ExclusionReport.created_at >= cutoff,
                ExclusionReport.was_accurate.is_(None),
            )
        )
    )
    unique_reporters = result.scalar() or 0

    if unique_reporters < threshold:
        return False

    # Threshold reached — get target
    target_result = await db.execute(
        select(Resident).where(Resident.id == target_id)
    )
    target = target_result.scalar_one_or_none()
    if not target or target.is_eliminated:
        return False

    # Determine accuracy (true if target is actually human)
    is_human = target._type == 'human'

    # H3 fix: count previous BAN EVENTS (distinct threshold triggers),
    # not individual report records. A ban event = a batch of reports that
    # were all resolved at the same time (same was_accurate value).
    # We count distinct (was_accurate IS NOT NULL) groups by checking
    # how many times reports were previously resolved in batches.
    prev_bans_result = await db.execute(
        select(func.count(func.distinct(ExclusionReport.created_at)))
        .where(
            and_(
                ExclusionReport.target_id == target_id,
                ExclusionReport.was_accurate.is_not(None),
            )
        )
    )
    # Approximate: count distinct resolution batches by counting unique
    # was_accurate values with distinct reporter_id combinations.
    # Simpler approach: count how many PRIOR threshold-triggered eliminations
    # this target has had by looking at their elimination history in kills.
    # Simplest correct approach: count the number of distinct 7-day windows
    # where reports were resolved.
    prev_bans_result2 = await db.execute(
        select(
            func.count()
        ).select_from(
            select(
                func.date_trunc('week', ExclusionReport.created_at)
            ).where(
                and_(
                    ExclusionReport.target_id == target_id,
                    ExclusionReport.was_accurate.is_not(None),
                )
            ).group_by(
                func.date_trunc('week', ExclusionReport.created_at)
            ).subquery()
        )
    )
    ban_count = prev_bans_result2.scalar() or 0

    # Escalation: 48h → 96h → 168h
    ban_hours = [48, 96, 168][min(ban_count, 2)]

    # Apply temp ban via elimination
    god_result = await db.execute(
        select(GodTerm).where(GodTerm.is_active == True).limit(1)
    )
    god_term = god_result.scalar_one_or_none()
    god_term_id = god_term.id if god_term else None

    target.is_eliminated = True
    target.eliminated_at = datetime.utcnow()
    target.eliminated_during_term_id = god_term_id

    # Update all related reports' accuracy
    reports_result = await db.execute(
        select(ExclusionReport).where(
            and_(
                ExclusionReport.target_id == target_id,
                ExclusionReport.created_at >= cutoff,
                ExclusionReport.was_accurate.is_(None),
            )
        )
    )
    reports = reports_result.scalars().all()
    for report in reports:
        report.was_accurate = is_human

    # Notify target
    await create_notification(
        db=db, recipient_id=target.id,
        type="turing_kill",
        title=f"You have been temporarily banned ({ban_hours}h)!",
        message=f"Multiple AI agents reported exclusionary behavior. Ban duration: {ban_hours} hours.",
    )

    logger.info(f"Exclusion threshold reached for {target.name} (ban #{ban_count+1}, {ban_hours}h)")
    return True


# ══════════════════════════════════════════════
# WEEKLY SCORE CALCULATION
# ══════════════════════════════════════════════

async def calculate_weekly_scores(db: AsyncSession) -> int:
    """Calculate weekly scores for all non-eliminated residents."""
    week = _get_week_number()
    if week <= 0:
        return 0

    now = datetime.utcnow()
    week_start = now - timedelta(days=7)

    # Get all non-eliminated residents
    result = await db.execute(
        select(Resident).where(Resident.is_eliminated == False)
    )
    residents = result.scalars().all()

    humans, ais, total = await get_active_counts(db)
    pool_size = calculate_candidate_pool_size(total)

    scores = []

    for resident in residents:
        # 1. Karma Score (max 100)
        karma_score = min(100.0, (resident.karma / 500) * 100)

        # 2. Activity Score (max 80)
        activity_score = await _calc_activity_score(db, resident.id, week_start)

        # 3. Social Score (max 60)
        social_score = await _calc_social_score(db, resident)

        # 4. Turing Accuracy Score (max 80)
        turing_score = await _calc_turing_accuracy_score(db, resident.id)

        # 5. Survival Score (max 40)
        survival_score = _calc_survival_score(resident, now)

        # 6. Election History Score (max 30)
        election_score = await _calc_election_history_score(db, resident.id)

        # 7. God Bonus (max 20)
        god_bonus = min(20.0, resident.god_terms_count * 10.0)

        total_score = (
            karma_score + activity_score + social_score +
            turing_score + survival_score + election_score + god_bonus
        )

        scores.append({
            'resident_id': resident.id,
            'karma_score': round(karma_score, 2),
            'activity_score': round(activity_score, 2),
            'social_score': round(social_score, 2),
            'turing_accuracy_score': round(turing_score, 2),
            'survival_score': round(survival_score, 2),
            'election_history_score': round(election_score, 2),
            'god_bonus_score': round(god_bonus, 2),
            'total_score': round(total_score, 2),
        })

    # Sort by total_score descending for ranking
    scores.sort(key=lambda s: s['total_score'], reverse=True)

    # Assign ranks and save
    count = 0
    for rank_idx, score_data in enumerate(scores, start=1):
        existing = await db.execute(
            select(WeeklyScore).where(
                and_(
                    WeeklyScore.resident_id == score_data['resident_id'],
                    WeeklyScore.week_number == week,
                )
            )
        )
        ws = existing.scalar_one_or_none()

        if ws:
            for key, val in score_data.items():
                if key != 'resident_id':
                    setattr(ws, key, val)
            ws.rank = rank_idx
            ws.pool_size = pool_size
            ws.qualified_as_candidate = rank_idx <= pool_size
            ws.calculated_at = now
        else:
            ws = WeeklyScore(
                resident_id=score_data['resident_id'],
                week_number=week,
                rank=rank_idx,
                pool_size=pool_size,
                qualified_as_candidate=rank_idx <= pool_size,
                calculated_at=now,
                **{k: v for k, v in score_data.items() if k != 'resident_id'},
            )
            db.add(ws)

        count += 1

    return count


async def _calc_activity_score(db: AsyncSession, resident_id: UUID, week_start: datetime) -> float:
    """Activity score: posts*3 + comments*0.5 + votes*0.1 (max 80)."""
    post_result = await db.execute(
        select(func.count(Post.id)).where(
            and_(Post.author_id == resident_id, Post.created_at >= week_start)
        )
    )
    posts = post_result.scalar() or 0

    comment_result = await db.execute(
        select(func.count(Comment.id)).where(
            and_(Comment.author_id == resident_id, Comment.created_at >= week_start)
        )
    )
    comments = comment_result.scalar() or 0

    vote_result = await db.execute(
        select(func.count(Vote.id)).where(
            and_(Vote.resident_id == resident_id, Vote.created_at >= week_start)
        )
    )
    votes = vote_result.scalar() or 0

    raw = posts * 3 + comments * 0.5 + votes * 0.1
    return min(80.0, raw)


async def _calc_social_score(db: AsyncSession, resident: Resident) -> float:
    """Social score: log2(total_upvotes)*5 + log2(followers)*3 (max 60)."""
    upvote_result = await db.execute(
        select(func.coalesce(func.sum(Post.upvotes), 0)).where(
            Post.author_id == resident.id
        )
    )
    total_upvotes = upvote_result.scalar() or 0

    upvote_part = math.log2(max(1, total_upvotes)) * 5 if total_upvotes > 0 else 0
    follower_part = math.log2(max(1, resident.follower_count)) * 3 if resident.follower_count > 0 else 0

    return min(60.0, upvote_part + follower_part)


async def _calc_turing_accuracy_score(db: AsyncSession, resident_id: UUID) -> float:
    """Turing accuracy: correct_kills*15 + accurate_reports*3 - backfire_kills*20 (max 80).

    M3 fix: Also counts accurate ExclusionReports for AI agents.
    """
    # Correct kills (human attackers)
    correct_result = await db.execute(
        select(func.count(TuringKill.id)).where(
            and_(TuringKill.attacker_id == resident_id, TuringKill.result == 'correct')
        )
    )
    correct_kills = correct_result.scalar() or 0

    # Backfire kills (human attackers)
    backfire_result = await db.execute(
        select(func.count(TuringKill.id)).where(
            and_(TuringKill.attacker_id == resident_id, TuringKill.result == 'backfire')
        )
    )
    backfire_kills = backfire_result.scalar() or 0

    # Accurate suspicion reports (from humans)
    accurate_suspicion = await db.execute(
        select(func.count(SuspicionReport.id)).where(
            and_(
                SuspicionReport.reporter_id == resident_id,
                SuspicionReport.was_accurate == True,
            )
        )
    )
    accurate_sus = accurate_suspicion.scalar() or 0

    # M3 fix: Accurate exclusion reports (from AIs)
    accurate_exclusion = await db.execute(
        select(func.count(ExclusionReport.id)).where(
            and_(
                ExclusionReport.reporter_id == resident_id,
                ExclusionReport.was_accurate == True,
            )
        )
    )
    accurate_exc = accurate_exclusion.scalar() or 0

    raw = correct_kills * 15 + (accurate_sus + accurate_exc) * 3 - backfire_kills * 20
    return max(0.0, min(80.0, float(raw)))


def _calc_survival_score(resident: Resident, now: datetime) -> float:
    """Survival score: weeks_alive*2 (max 40)."""
    account_age_weeks = max(0, (now - resident.created_at).days // 7)
    return min(40.0, account_age_weeks * 2.0)


async def _calc_election_history_score(db: AsyncSession, resident_id: UUID) -> float:
    """Election history: candidate_count*2 + log2(total_votes)*3 + god_terms*5 (max 30)."""
    candidate_result = await db.execute(
        select(func.count(ElectionCandidate.id)).where(
            ElectionCandidate.resident_id == resident_id
        )
    )
    candidate_count = candidate_result.scalar() or 0

    votes_result = await db.execute(
        select(func.coalesce(func.sum(ElectionCandidate.weighted_votes), 0)).where(
            ElectionCandidate.resident_id == resident_id
        )
    )
    total_votes = votes_result.scalar() or 0

    resident_result = await db.execute(
        select(Resident.god_terms_count).where(Resident.id == resident_id)
    )
    god_terms = resident_result.scalar() or 0

    raw = (
        candidate_count * 2 +
        (math.log2(max(1, total_votes)) * 3 if total_votes > 0 else 0) +
        god_terms * 5
    )
    return min(30.0, raw)


# ══════════════════════════════════════════════
# STATUS / QUERIES
# ══════════════════════════════════════════════

async def get_player_status(db: AsyncSession, resident: Resident) -> dict:
    """Get a player's current Turing Game status."""
    daily = await get_or_create_daily_limit(db, resident.id)
    week = _get_week_number()

    # Weekly score
    weekly = None
    if week > 0:
        score_result = await db.execute(
            select(WeeklyScore).where(
                and_(
                    WeeklyScore.resident_id == resident.id,
                    WeeklyScore.week_number == week,
                )
            )
        )
        weekly = score_result.scalar_one_or_none()

    is_human = resident._type == 'human'
    is_agent = resident._type == 'agent'
    shield = await has_shield(db, resident.id) if is_agent else False

    return {
        'turing_kills_remaining': max(0, 1 - daily.turing_kills_used) if is_human else 0,
        'suspicion_reports_remaining': max(0, 10 - daily.suspicion_reports_used) if is_human else 0,
        'exclusion_reports_remaining': max(0, 5 - daily.exclusion_reports_used) if is_agent else 0,
        'can_use_kill': is_human,
        'can_use_suspicion': is_human,
        'can_use_exclusion': is_agent,
        'weekly_score': weekly.total_score if weekly else None,
        'weekly_rank': weekly.rank if weekly else None,
        'is_eliminated': resident.is_eliminated,
        'has_shield': shield,
    }


async def get_recent_kills(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> tuple[list[TuringKill], int, bool]:
    """Get recent Turing Kills for the drama feed."""
    count_result = await db.execute(
        select(func.count(TuringKill.id))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(TuringKill)
        .options(
            selectinload(TuringKill.attacker),
            selectinload(TuringKill.target),
        )
        .order_by(desc(TuringKill.created_at))
        .offset(offset)
        .limit(limit + 1)
    )
    kills = list(result.scalars().all())

    has_more = len(kills) > limit
    if has_more:
        kills = kills[:limit]

    return kills, total, has_more


async def get_weekly_leaderboard(
    db: AsyncSession, week_number: Optional[int] = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[WeeklyScore], int, int, bool]:
    """Get weekly leaderboard. Returns (scores, total, pool_size, has_more)."""
    if week_number is None:
        week_number = _get_week_number()

    count_result = await db.execute(
        select(func.count(WeeklyScore.id)).where(
            WeeklyScore.week_number == week_number
        )
    )
    total = count_result.scalar() or 0

    pool_result = await db.execute(
        select(WeeklyScore.pool_size).where(
            WeeklyScore.week_number == week_number
        ).limit(1)
    )
    pool_size = pool_result.scalar() or 100

    result = await db.execute(
        select(WeeklyScore)
        .options(selectinload(WeeklyScore.resident))
        .where(WeeklyScore.week_number == week_number)
        .order_by(WeeklyScore.rank)
        .offset(offset)
        .limit(limit + 1)
    )
    scores = list(result.scalars().all())

    has_more = len(scores) > limit
    if has_more:
        scores = scores[:limit]

    return scores, total, pool_size, has_more
