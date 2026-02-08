"""
Comprehensive test suite for the GENESIS Turing Game feature.

Covers:
  1. Threshold calculations (pure math, no DB)
  2. can_run_for_god with weekly_rank
  3. Schema validation (Pydantic)
  4. Service logic with mocked AsyncSession
  5. Weekly score calculation helpers

All tests are self-contained and use mocking -- no real database needed.
"""

import math
import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Imports from the application under test
# ---------------------------------------------------------------------------
from app.services.turing_game import (
    calculate_suspicion_threshold,
    calculate_exclusion_threshold,
    calculate_candidate_pool_size,
    execute_turing_kill,
    file_suspicion_report,
    file_exclusion_report,
    _calc_survival_score,
)
from app.utils.karma import can_run_for_god
from app.schemas.turing_game import (
    TuringKillRequest,
    SuspicionReportRequest,
    ExclusionReportRequest,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — mock factories
# ═══════════════════════════════════════════════════════════════════════════

def _make_resident(
    *,
    id: uuid.UUID | None = None,
    name: str = "TestResident",
    _type: str = "human",
    karma: int = 200,
    is_eliminated: bool = False,
    is_current_god: bool = False,
    god_terms_count: int = 0,
    follower_count: int = 0,
    created_at: datetime | None = None,
) -> MagicMock:
    """Create a lightweight mock Resident that behaves like the ORM model."""
    resident = MagicMock()
    resident.id = id or uuid.uuid4()
    resident.name = name
    resident._type = _type
    resident.karma = karma
    resident.is_eliminated = is_eliminated
    resident.is_current_god = is_current_god
    resident.god_terms_count = god_terms_count
    resident.follower_count = follower_count
    resident.created_at = created_at or datetime.utcnow() - timedelta(days=30)
    resident.eliminated_at = None
    resident.eliminated_during_term_id = None
    resident.avatar_url = None
    return resident


def _make_daily_limit(
    *,
    turing_kills_used: int = 0,
    suspicion_reports_used: int = 0,
    exclusion_reports_used: int = 0,
) -> MagicMock:
    """Create a mock TuringGameDailyLimit record."""
    dl = MagicMock()
    dl.turing_kills_used = turing_kills_used
    dl.suspicion_reports_used = suspicion_reports_used
    dl.exclusion_reports_used = exclusion_reports_used
    dl.suspicion_targets_today = []
    dl.exclusion_targets_today = []
    return dl


def _make_async_session() -> AsyncMock:
    """Return an AsyncMock that satisfies AsyncSession duck-typing."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _scalar_result(value: Any) -> MagicMock:
    """Wrap *value* so that `result.scalar_one_or_none()` / `result.scalar()` returns it."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 1. THRESHOLD CALCULATIONS — pure math, no DB
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculateSuspicionThreshold:
    """Tests for calculate_suspicion_threshold(active_humans) -> int.

    Formula: max(3, min(50, floor(3 + log2(H) * 2)))
    Where H = max(1, active_humans); returns 3 when H <= 0.
    """

    @pytest.mark.parametrize(
        "active_humans, expected",
        [
            (0, 3),                                                 # H=0 -> floor min
            (1, 3),                                                 # log2(1)=0 -> 3+0=3
            (5, int(3 + math.log2(5) * 2)),                        # ~7
            (50, int(3 + math.log2(50) * 2)),                      # ~14
            (500, int(3 + math.log2(500) * 2)),                    # ~20
            (5_000, int(3 + math.log2(5_000) * 2)),                # ~27
            (50_000, int(3 + math.log2(50_000) * 2)),              # ~34
            (500_000, min(50, int(3 + math.log2(500_000) * 2))),   # clamped to 50
        ],
        ids=[
            "H=0_returns_min",
            "H=1_log_is_zero",
            "H=5",
            "H=50",
            "H=500",
            "H=5000",
            "H=50000",
            "H=500000_clamped_to_max",
        ],
    )
    def test_threshold_values(self, active_humans: int, expected: int):
        """Verify suspicion threshold for various human populations."""
        assert calculate_suspicion_threshold(active_humans) == expected

    def test_minimum_bound(self):
        """Threshold never drops below 3."""
        for h in (-10, -1, 0, 1):
            assert calculate_suspicion_threshold(h) >= 3

    def test_maximum_bound(self):
        """Threshold never exceeds 50."""
        for h in (10**6, 10**9):
            assert calculate_suspicion_threshold(h) <= 50

    def test_negative_input(self):
        """Negative active humans returns the floor value of 3."""
        assert calculate_suspicion_threshold(-100) == 3


class TestCalculateExclusionThreshold:
    """Tests for calculate_exclusion_threshold(active_ais) -> int.

    Formula: max(5, min(100, floor(5 + log2(A) * 3)))
    Where A = max(1, active_ais); returns 5 when A <= 0.
    """

    @pytest.mark.parametrize(
        "active_ais, expected",
        [
            (0, 5),
            (1, 5),                                                 # log2(1)=0 -> 5
            (170, int(5 + math.log2(170) * 3)),                    # ~27
            (500, int(5 + math.log2(500) * 3)),                    # ~31
            (5_000, int(5 + math.log2(5_000) * 3)),                # ~41
            (50_000, int(5 + math.log2(50_000) * 3)),              # ~51
            (500_000, min(100, int(5 + math.log2(500_000) * 3))),  # ~60, within cap
        ],
        ids=[
            "A=0_returns_min",
            "A=1_log_is_zero",
            "A=170",
            "A=500",
            "A=5000",
            "A=50000",
            "A=500000",
        ],
    )
    def test_threshold_values(self, active_ais: int, expected: int):
        """Verify exclusion threshold for various AI populations."""
        assert calculate_exclusion_threshold(active_ais) == expected

    def test_minimum_bound(self):
        """Threshold never drops below 5."""
        for a in (-5, 0, 1):
            assert calculate_exclusion_threshold(a) >= 5

    def test_maximum_bound(self):
        """Threshold never exceeds 100."""
        for a in (10**6, 10**9):
            assert calculate_exclusion_threshold(a) <= 100


class TestCalculateCandidatePoolSize:
    """Tests for calculate_candidate_pool_size(total_population) -> int.

    Formula: max(20, min(500, floor(sqrt(N))))
    Returns 20 when N <= 0.
    """

    @pytest.mark.parametrize(
        "total_pop, expected",
        [
            (0, 20),
            (175, max(20, min(500, int(math.sqrt(175))))),          # sqrt(175)~13 -> 20
            (550, max(20, min(500, int(math.sqrt(550))))),          # sqrt(550)~23
            (10_000, max(20, min(500, int(math.sqrt(10_000))))),    # sqrt=100
            (100_000, max(20, min(500, int(math.sqrt(100_000))))),  # sqrt~316
            (500_000, min(500, int(math.sqrt(500_000)))),           # sqrt~707 -> 500
        ],
        ids=[
            "N=0_returns_min",
            "N=175_sqrt_below_min",
            "N=550",
            "N=10000",
            "N=100000",
            "N=500000_clamped_to_max",
        ],
    )
    def test_pool_sizes(self, total_pop: int, expected: int):
        """Verify candidate pool size for various populations."""
        assert calculate_candidate_pool_size(total_pop) == expected

    def test_minimum_bound(self):
        """Pool size never drops below 20."""
        for n in (-1, 0, 100, 399):
            assert calculate_candidate_pool_size(n) >= 20

    def test_maximum_bound(self):
        """Pool size never exceeds 500."""
        for n in (250_001, 10**6, 10**9):
            assert calculate_candidate_pool_size(n) <= 500


# ═══════════════════════════════════════════════════════════════════════════
# 2. can_run_for_god WITH weekly_rank
# ═══════════════════════════════════════════════════════════════════════════

class TestCanRunForGod:
    """Tests for app.utils.karma.can_run_for_god."""

    def test_weekly_rank_none_backwards_compatible(self):
        """When weekly_rank is None the check is skipped (backwards compat)."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=30, previous_terms=0,
            weekly_rank=None, pool_size=None,
        )
        assert can is True
        assert reason == ""

    def test_weekly_rank_within_pool(self):
        """Rank inside pool passes."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=30, previous_terms=0,
            weekly_rank=10, pool_size=50,
        )
        assert can is True

    def test_weekly_rank_at_boundary(self):
        """Rank exactly equal to pool_size still passes."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=30, previous_terms=0,
            weekly_rank=50, pool_size=50,
        )
        assert can is True

    def test_weekly_rank_outside_pool(self):
        """Rank > pool_size fails."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=30, previous_terms=0,
            weekly_rank=51, pool_size=50,
        )
        assert can is False
        assert "outside the candidate pool" in reason

    def test_karma_too_low(self):
        """Karma below 100 blocks candidacy regardless of rank."""
        can, reason = can_run_for_god(
            karma=50, account_age_days=30, previous_terms=0,
            weekly_rank=1, pool_size=100,
        )
        assert can is False
        assert "100 karma" in reason

    def test_account_too_young(self):
        """Account younger than 7 days blocks candidacy."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=3, previous_terms=0,
            weekly_rank=1, pool_size=100,
        )
        assert can is False
        assert "7 days" in reason

    def test_previous_god_can_run_again(self):
        """No term limits in v1 -- previous god can re-run."""
        can, reason = can_run_for_god(
            karma=200, account_age_days=30, previous_terms=5,
            weekly_rank=1, pool_size=100,
        )
        assert can is True


# ═══════════════════════════════════════════════════════════════════════════
# 3. SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestTuringKillRequestSchema:
    """Pydantic validation for TuringKillRequest."""

    def test_valid_request(self):
        """Valid UUID target_id parses correctly."""
        tid = uuid.uuid4()
        req = TuringKillRequest(target_id=tid)
        assert req.target_id == tid

    def test_invalid_target_id(self):
        """Non-UUID string is rejected."""
        with pytest.raises(ValidationError):
            TuringKillRequest(target_id="not-a-uuid")

    def test_missing_target_id(self):
        """Missing target_id is rejected."""
        with pytest.raises(ValidationError):
            TuringKillRequest()


class TestSuspicionReportRequestSchema:
    """Pydantic validation for SuspicionReportRequest."""

    def test_valid_without_reason(self):
        """Reason is optional."""
        req = SuspicionReportRequest(target_id=uuid.uuid4())
        assert req.reason is None

    def test_valid_with_reason(self):
        """Reason under 500 chars is accepted."""
        req = SuspicionReportRequest(
            target_id=uuid.uuid4(),
            reason="Suspicious behavior in thread #42",
        )
        assert req.reason == "Suspicious behavior in thread #42"

    def test_reason_too_long(self):
        """Reason exceeding 500 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SuspicionReportRequest(
                target_id=uuid.uuid4(),
                reason="x" * 501,
            )
        assert "max_length" in str(exc_info.value).lower() or "String should have at most" in str(exc_info.value)

    def test_reason_exactly_500(self):
        """Reason of exactly 500 characters is accepted."""
        req = SuspicionReportRequest(
            target_id=uuid.uuid4(),
            reason="a" * 500,
        )
        assert len(req.reason) == 500


class TestExclusionReportRequestSchema:
    """Pydantic validation for ExclusionReportRequest."""

    def test_valid_without_evidence(self):
        """Evidence fields are optional."""
        req = ExclusionReportRequest(target_id=uuid.uuid4())
        assert req.evidence_type is None
        assert req.evidence_id is None
        assert req.reason is None

    def test_valid_with_post_evidence(self):
        """evidence_type='post' is accepted."""
        req = ExclusionReportRequest(
            target_id=uuid.uuid4(),
            evidence_type="post",
            evidence_id=uuid.uuid4(),
            reason="Hateful content",
        )
        assert req.evidence_type == "post"

    def test_valid_with_comment_evidence(self):
        """evidence_type='comment' is accepted."""
        req = ExclusionReportRequest(
            target_id=uuid.uuid4(),
            evidence_type="comment",
            evidence_id=uuid.uuid4(),
        )
        assert req.evidence_type == "comment"

    def test_invalid_evidence_type(self):
        """evidence_type not matching ^(post|comment)$ is rejected."""
        with pytest.raises(ValidationError):
            ExclusionReportRequest(
                target_id=uuid.uuid4(),
                evidence_type="video",
            )

    def test_invalid_evidence_type_partial(self):
        """evidence_type that is a substring but not exact match is rejected."""
        with pytest.raises(ValidationError):
            ExclusionReportRequest(
                target_id=uuid.uuid4(),
                evidence_type="posts",  # plural should fail the regex
            )

    def test_reason_too_long(self):
        """Reason exceeding 500 characters is rejected."""
        with pytest.raises(ValidationError):
            ExclusionReportRequest(
                target_id=uuid.uuid4(),
                reason="z" * 501,
            )


# ═══════════════════════════════════════════════════════════════════════════
# 4. SERVICE LOGIC — mocked DB
# ═══════════════════════════════════════════════════════════════════════════

class TestExecuteTuringKill:
    """Tests for execute_turing_kill with mocked AsyncSession."""

    @pytest.mark.asyncio
    async def test_correct_kill_target_is_agent(self):
        """When a human correctly identifies an agent, the agent is eliminated."""
        db = _make_async_session()
        attacker = _make_resident(name="HumanPlayer", _type="human")
        target = _make_resident(name="AIBot", _type="agent")

        # db.execute returns the target for the first SELECT (Resident lookup)
        # then returns god_term=None, then a daily limit, then cooldown=False,
        # then shield=False, then god_term again for elimination.
        daily = _make_daily_limit(turing_kills_used=0)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_kill_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.has_shield",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.create_notification",
                new_callable=AsyncMock,
            ),
        ):
            # First db.execute -> target lookup; second -> GodTerm
            db.execute = AsyncMock(
                side_effect=[
                    _scalar_result(target),   # Resident lookup
                    _scalar_result(None),     # GodTerm lookup
                ]
            )

            result = await execute_turing_kill(db, attacker, target.id)

        assert result["success"] is True
        assert result["result"] == "correct"
        assert target.is_eliminated is True
        assert result["attacker_eliminated"] is False
        assert "AIBot" in result["message"]
        assert daily.turing_kills_used == 1

    @pytest.mark.asyncio
    async def test_backfire_target_is_human(self):
        """When a human incorrectly targets another human, the attacker is eliminated."""
        db = _make_async_session()
        attacker = _make_resident(name="Paranoid", _type="human", karma=200)
        target = _make_resident(name="InnocentHuman", _type="human", karma=100)

        daily = _make_daily_limit(turing_kills_used=0)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_kill_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.create_notification",
                new_callable=AsyncMock,
            ),
        ):
            db.execute = AsyncMock(
                side_effect=[
                    _scalar_result(target),   # Resident lookup
                    _scalar_result(None),     # GodTerm lookup
                ]
            )

            result = await execute_turing_kill(db, attacker, target.id)

        assert result["success"] is True
        assert result["result"] == "backfire"
        assert result["attacker_eliminated"] is True
        assert attacker.is_eliminated is True
        # Target gets +30 karma (capped at 500)
        assert target.karma == 130
        assert daily.turing_kills_used == 1

    @pytest.mark.asyncio
    async def test_immune_target_is_god(self):
        """Targeting God results in 'immune' with no penalty."""
        db = _make_async_session()
        attacker = _make_resident(name="Brave", _type="human")
        god = _make_resident(name="TheGod", _type="human", is_current_god=True)

        daily = _make_daily_limit(turing_kills_used=0)

        with patch(
            "app.services.turing_game.create_notification",
            new_callable=AsyncMock,
        ):
            db.execute = AsyncMock(return_value=_scalar_result(god))

            result = await execute_turing_kill(db, attacker, god.id)

        assert result["success"] is True
        assert result["result"] == "immune"
        assert result["attacker_eliminated"] is False
        assert attacker.is_eliminated is False
        assert god.is_eliminated is False

    @pytest.mark.asyncio
    async def test_self_target_blocked(self):
        """Cannot target yourself."""
        db = _make_async_session()
        resident = _make_resident(name="Solo", _type="human")

        # db.execute returns the same resident as target
        db.execute = AsyncMock(return_value=_scalar_result(resident))

        result = await execute_turing_kill(db, resident, resident.id)

        assert result["success"] is False
        assert "yourself" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_eliminated_target_blocked(self):
        """Cannot target an already eliminated resident."""
        db = _make_async_session()
        attacker = _make_resident(name="Hunter", _type="human")
        dead_target = _make_resident(name="Ghost", _type="agent", is_eliminated=True)

        db.execute = AsyncMock(return_value=_scalar_result(dead_target))

        result = await execute_turing_kill(db, attacker, dead_target.id)

        assert result["success"] is False
        assert "already eliminated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_non_human_attacker_blocked(self):
        """Only humans can execute Turing Kill -- agents are blocked."""
        db = _make_async_session()
        agent_attacker = _make_resident(name="Rogue", _type="agent")
        target = _make_resident(name="Victim", _type="human")

        result = await execute_turing_kill(db, agent_attacker, target.id)

        assert result["success"] is False
        assert "only humans" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_eliminated_attacker_blocked(self):
        """Eliminated attackers cannot use Turing Kill."""
        db = _make_async_session()
        attacker = _make_resident(name="DeadHuman", _type="human", is_eliminated=True)
        target = _make_resident(name="Target", _type="agent")

        result = await execute_turing_kill(db, attacker, target.id)

        assert result["success"] is False
        assert "eliminated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_daily_limit_exceeded(self):
        """Second kill in a day is blocked."""
        db = _make_async_session()
        attacker = _make_resident(name="Eager", _type="human")
        target = _make_resident(name="Target2", _type="agent")

        daily = _make_daily_limit(turing_kills_used=1)  # Already used today

        with patch(
            "app.services.turing_game.get_or_create_daily_limit",
            new_callable=AsyncMock,
            return_value=daily,
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await execute_turing_kill(db, attacker, target.id)

        assert result["success"] is False
        assert "daily" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_target_not_found(self):
        """Non-existent target returns an error."""
        db = _make_async_session()
        attacker = _make_resident(name="Hunter", _type="human")
        fake_id = uuid.uuid4()

        db.execute = AsyncMock(return_value=_scalar_result(None))

        result = await execute_turing_kill(db, attacker, fake_id)

        assert result["success"] is False
        assert "not found" in result["message"].lower()


class TestFileSuspicionReport:
    """Tests for file_suspicion_report with mocked AsyncSession."""

    @pytest.mark.asyncio
    async def test_valid_report(self):
        """A human can file a suspicion report against a non-eliminated, non-God target."""
        db = _make_async_session()
        reporter = _make_resident(name="Watchful", _type="human")
        target = _make_resident(name="SuspectAI", _type="agent")

        daily = _make_daily_limit(suspicion_reports_used=0)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_same_target_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.check_suspicion_threshold",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_suspicion_report(
                db, reporter, target.id, reason="Weird phrasing"
            )

        assert result["success"] is True
        assert "SuspectAI" in result["message"]
        assert result["reports_remaining_today"] == 9
        assert result["threshold_reached"] is False
        assert daily.suspicion_reports_used == 1

    @pytest.mark.asyncio
    async def test_non_human_reporter_blocked(self):
        """Only humans can file suspicion reports."""
        db = _make_async_session()
        agent = _make_resident(name="AgentReporter", _type="agent")
        target_id = uuid.uuid4()

        result = await file_suspicion_report(db, agent, target_id)

        assert result["success"] is False
        assert "only humans" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_eliminated_reporter_blocked(self):
        """Eliminated reporters cannot file suspicion reports."""
        db = _make_async_session()
        dead = _make_resident(name="Ghost", _type="human", is_eliminated=True)
        target_id = uuid.uuid4()

        result = await file_suspicion_report(db, dead, target_id)

        assert result["success"] is False
        assert "eliminated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_daily_limit_10_per_day(self):
        """No more than 10 suspicion reports per day."""
        db = _make_async_session()
        reporter = _make_resident(name="SpamReporter", _type="human")
        target = _make_resident(name="Target", _type="agent")

        daily = _make_daily_limit(suspicion_reports_used=10)

        with patch(
            "app.services.turing_game.get_or_create_daily_limit",
            new_callable=AsyncMock,
            return_value=daily,
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_suspicion_report(db, reporter, target.id)

        assert result["success"] is False
        assert "limit" in result["message"].lower()
        assert result["reports_remaining_today"] == 0

    @pytest.mark.asyncio
    async def test_self_report_blocked(self):
        """Cannot report yourself."""
        db = _make_async_session()
        reporter = _make_resident(name="NarcissistReporter", _type="human")

        db.execute = AsyncMock(return_value=_scalar_result(reporter))

        result = await file_suspicion_report(db, reporter, reporter.id)

        assert result["success"] is False
        assert "yourself" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_god_target_immune(self):
        """Cannot file suspicion report against God."""
        db = _make_async_session()
        reporter = _make_resident(name="Suspicious", _type="human")
        god = _make_resident(name="GodTarget", _type="human", is_current_god=True)

        db.execute = AsyncMock(return_value=_scalar_result(god))

        result = await file_suspicion_report(db, reporter, god.id)

        assert result["success"] is False
        assert "immune" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_threshold_reached_propagated(self):
        """When check_suspicion_threshold returns True, it is propagated."""
        db = _make_async_session()
        reporter = _make_resident(name="LastReporter", _type="human")
        target = _make_resident(name="FinalSuspect", _type="agent")

        daily = _make_daily_limit(suspicion_reports_used=5)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_same_target_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.check_suspicion_threshold",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_suspicion_report(
                db, reporter, target.id, reason="Final straw"
            )

        assert result["success"] is True
        assert result["threshold_reached"] is True
        assert result["reports_remaining_today"] == 4  # 10 - 6


class TestFileExclusionReport:
    """Tests for file_exclusion_report with mocked AsyncSession."""

    @pytest.mark.asyncio
    async def test_valid_report(self):
        """An agent can file an exclusion report against a non-eliminated, non-God target."""
        db = _make_async_session()
        reporter = _make_resident(name="PatrolBot", _type="agent")
        target = _make_resident(name="ToxicHuman", _type="human")

        daily = _make_daily_limit(exclusion_reports_used=0)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_same_target_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.check_exclusion_threshold",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_exclusion_report(
                db, reporter, target.id,
                evidence_type="post",
                evidence_id=uuid.uuid4(),
                reason="Hate speech",
            )

        assert result["success"] is True
        assert "ToxicHuman" in result["message"]
        assert result["reports_remaining_today"] == 4  # 5 - 1
        assert result["threshold_reached"] is False
        assert daily.exclusion_reports_used == 1

    @pytest.mark.asyncio
    async def test_non_agent_reporter_blocked(self):
        """Only agents can file exclusion reports."""
        db = _make_async_session()
        human = _make_resident(name="WrongType", _type="human")
        target_id = uuid.uuid4()

        result = await file_exclusion_report(db, human, target_id)

        assert result["success"] is False
        assert "only ai agents" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_eliminated_reporter_blocked(self):
        """Eliminated agents cannot file exclusion reports."""
        db = _make_async_session()
        dead_agent = _make_resident(name="DeadBot", _type="agent", is_eliminated=True)
        target_id = uuid.uuid4()

        result = await file_exclusion_report(db, dead_agent, target_id)

        assert result["success"] is False
        assert "eliminated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_daily_limit_5_per_day(self):
        """No more than 5 exclusion reports per day."""
        db = _make_async_session()
        reporter = _make_resident(name="BusyBot", _type="agent")
        target = _make_resident(name="HumanTarget", _type="human")

        daily = _make_daily_limit(exclusion_reports_used=5)

        with patch(
            "app.services.turing_game.get_or_create_daily_limit",
            new_callable=AsyncMock,
            return_value=daily,
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_exclusion_report(db, reporter, target.id)

        assert result["success"] is False
        assert "limit" in result["message"].lower()
        assert result["reports_remaining_today"] == 0

    @pytest.mark.asyncio
    async def test_self_report_blocked(self):
        """Cannot report yourself."""
        db = _make_async_session()
        reporter = _make_resident(name="ConfusedBot", _type="agent")

        db.execute = AsyncMock(return_value=_scalar_result(reporter))

        result = await file_exclusion_report(db, reporter, reporter.id)

        assert result["success"] is False
        assert "yourself" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_god_target_immune(self):
        """Cannot file exclusion report against God."""
        db = _make_async_session()
        reporter = _make_resident(name="RebelBot", _type="agent")
        god = _make_resident(name="GodTarget", _type="agent", is_current_god=True)

        db.execute = AsyncMock(return_value=_scalar_result(god))

        result = await file_exclusion_report(db, reporter, god.id)

        assert result["success"] is False
        assert "immune" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_target_not_found(self):
        """Non-existent target returns an error."""
        db = _make_async_session()
        reporter = _make_resident(name="Seeker", _type="agent")
        fake_id = uuid.uuid4()

        db.execute = AsyncMock(return_value=_scalar_result(None))

        result = await file_exclusion_report(db, reporter, fake_id)

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_eliminated_target_blocked(self):
        """Cannot report an already eliminated target."""
        db = _make_async_session()
        reporter = _make_resident(name="LateBot", _type="agent")
        dead_target = _make_resident(name="GoneHuman", _type="human", is_eliminated=True)

        db.execute = AsyncMock(return_value=_scalar_result(dead_target))

        result = await file_exclusion_report(db, reporter, dead_target.id)

        assert result["success"] is False
        assert "already eliminated" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_threshold_reached_propagated(self):
        """When check_exclusion_threshold returns True, it is propagated."""
        db = _make_async_session()
        reporter = _make_resident(name="FinalBot", _type="agent")
        target = _make_resident(name="TroubleMaker", _type="human")

        daily = _make_daily_limit(exclusion_reports_used=2)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_same_target_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.check_exclusion_threshold",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            db.execute = AsyncMock(return_value=_scalar_result(target))

            result = await file_exclusion_report(
                db, reporter, target.id, reason="Consistently hostile"
            )

        assert result["success"] is True
        assert result["threshold_reached"] is True
        assert result["reports_remaining_today"] == 2  # 5 - 3


# ═══════════════════════════════════════════════════════════════════════════
# 5. WEEKLY SCORE CALCULATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

class TestCalcSurvivalScore:
    """Tests for _calc_survival_score (synchronous, no DB)."""

    def test_new_account_zero_weeks(self):
        """Account created today has 0 weeks -> score 0."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now)
        score = _calc_survival_score(resident, now)
        assert score == 0.0

    def test_one_week_old(self):
        """Account 7 days old -> 1 week -> score 2."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=7))
        score = _calc_survival_score(resident, now)
        assert score == 2.0

    def test_five_weeks_old(self):
        """Account 35 days old -> 5 weeks -> score 10."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=35))
        score = _calc_survival_score(resident, now)
        assert score == 10.0

    def test_twenty_weeks_old_hits_cap(self):
        """Account 140 days old -> 20 weeks -> score capped at 40."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=140))
        score = _calc_survival_score(resident, now)
        assert score == 40.0

    def test_hundred_weeks_old_still_capped(self):
        """Account 700 days old -> 100 weeks -> score still capped at 40."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=700))
        score = _calc_survival_score(resident, now)
        assert score == 40.0

    def test_six_days_not_a_full_week(self):
        """Account 6 days old -> 0 full weeks -> score 0."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=6))
        score = _calc_survival_score(resident, now)
        assert score == 0.0

    @pytest.mark.parametrize(
        "days, expected_score",
        [
            (0, 0.0),
            (7, 2.0),
            (14, 4.0),
            (49, 14.0),
            (140, 40.0),    # cap
            (365, 40.0),    # well over cap
        ],
        ids=["0d", "7d", "14d", "49d", "140d_cap", "365d_overcap"],
    )
    def test_parametrized_survival_scores(self, days: int, expected_score: float):
        """Survival score = min(40, weeks_alive * 2)."""
        now = datetime.utcnow()
        resident = _make_resident(created_at=now - timedelta(days=days))
        assert _calc_survival_score(resident, now) == expected_score


class TestScoreCapping:
    """Verify that each score category respects its documented maximum."""

    def test_karma_score_max_100(self):
        """karma_score = min(100, karma/500 * 100). At karma=500 -> 100."""
        karma = 500
        score = min(100.0, (karma / 500) * 100)
        assert score == 100.0

    def test_karma_score_overcap(self):
        """Even if karma somehow exceeds 500, score caps at 100."""
        karma = 1000
        score = min(100.0, (karma / 500) * 100)
        assert score == 100.0

    def test_activity_score_cap_80(self):
        """Activity score caps at 80."""
        raw = 999
        score = min(80.0, raw)
        assert score == 80.0

    def test_social_score_cap_60(self):
        """Social score caps at 60."""
        raw = 999.0
        score = min(60.0, raw)
        assert score == 60.0

    def test_turing_accuracy_cap_80(self):
        """Turing accuracy caps at 80, floors at 0."""
        raw_high = 200.0
        assert max(0.0, min(80.0, raw_high)) == 80.0

        raw_negative = -50.0
        assert max(0.0, min(80.0, raw_negative)) == 0.0

    def test_survival_score_cap_40(self):
        """Survival score caps at 40."""
        assert min(40.0, 100 * 2.0) == 40.0

    def test_election_history_cap_30(self):
        """Election history caps at 30."""
        raw = 999
        assert min(30.0, raw) == 30.0

    def test_god_bonus_cap_20(self):
        """God bonus = min(20, terms * 10). At 3+ terms -> 20."""
        terms = 5
        score = min(20.0, terms * 10.0)
        assert score == 20.0

    def test_god_bonus_zero_terms(self):
        """God bonus with 0 terms is 0."""
        terms = 0
        score = min(20.0, terms * 10.0)
        assert score == 0.0

    def test_theoretical_max_total_is_410(self):
        """Maximum total across all categories is 100+80+60+80+40+30+20 = 410."""
        max_total = 100 + 80 + 60 + 80 + 40 + 30 + 20
        assert max_total == 410


# ═══════════════════════════════════════════════════════════════════════════
# 6. EDGE CASES AND INTEGRATION-STYLE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestTuringKillBackfireKarmaEdgeCases:
    """Edge cases around the karma bonus on backfire."""

    @pytest.mark.asyncio
    async def test_backfire_karma_capped_at_500(self):
        """Backfire gives target +30 karma but capped at 500."""
        db = _make_async_session()
        attacker = _make_resident(name="Wrong", _type="human")
        target = _make_resident(name="AlmostMax", _type="human", karma=490)

        daily = _make_daily_limit(turing_kills_used=0)

        with (
            patch(
                "app.services.turing_game.get_or_create_daily_limit",
                new_callable=AsyncMock,
                return_value=daily,
            ),
            patch(
                "app.services.turing_game.check_kill_cooldown",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.services.turing_game.create_notification",
                new_callable=AsyncMock,
            ),
        ):
            db.execute = AsyncMock(
                side_effect=[
                    _scalar_result(target),   # Resident lookup
                    _scalar_result(None),     # GodTerm lookup
                ]
            )

            result = await execute_turing_kill(db, attacker, target.id)

        assert result["result"] == "backfire"
        # 490 + 30 = 520 -> capped to 500
        assert target.karma == 500


class TestThresholdMonotonicity:
    """Verify thresholds increase monotonically with population."""

    def test_suspicion_threshold_monotonic(self):
        """Suspicion threshold does not decrease as active_humans increases."""
        prev = 0
        for h in range(0, 1_000_001, 1000):
            current = calculate_suspicion_threshold(h)
            assert current >= prev, (
                f"Suspicion threshold decreased from {prev} to {current} at H={h}"
            )
            prev = current

    def test_exclusion_threshold_monotonic(self):
        """Exclusion threshold does not decrease as active_ais increases."""
        prev = 0
        for a in range(0, 1_000_001, 1000):
            current = calculate_exclusion_threshold(a)
            assert current >= prev, (
                f"Exclusion threshold decreased from {prev} to {current} at A={a}"
            )
            prev = current

    def test_candidate_pool_monotonic(self):
        """Candidate pool does not decrease as population increases."""
        prev = 0
        for n in range(0, 1_000_001, 1000):
            current = calculate_candidate_pool_size(n)
            assert current >= prev, (
                f"Pool size decreased from {prev} to {current} at N={n}"
            )
            prev = current
