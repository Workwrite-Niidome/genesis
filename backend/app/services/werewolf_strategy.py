"""
Phantom Night — Strategic AI Agent Brain

Architecture:
─────────────
1. GameContext dataclass — aggregates ALL available game data into one structure
2. build_game_context() — single DB query function that populates GameContext
3. 5 scoring functions — algorithmic target selection per role (zero extra LLM calls)
4. 2 prompt builders — rich structured prompts for LLM text generation

Key principle: Scoring is ALGORITHMIC (fast, no LLM).
LLM is only used for natural language generation (discussion comments, vote reasons).
Zero additional LLM calls vs. current implementation.
"""
import logging
import random
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.werewolf_game import (
    WerewolfGame, WerewolfRole, WerewolfGameEvent, NightAction, DayVote,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# GAME CONTEXT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GameContext:
    game: WerewolfGame
    my_role: WerewolfRole
    agent_id: uuid.UUID
    agent_name: str
    personality_key: str

    alive_players: list  # list[WerewolfRole]
    alive_citizens: list  # alive players on citizens team
    alive_phantoms: list  # alive players on phantoms team

    # History
    all_events: list  # list[WerewolfGameEvent] (public events, no phantom_chat)
    death_log: list  # [{round, name, role, cause, revealed_type}]
    vote_history: dict  # round_number -> [{voter_name, target_name, votes}]
    night_actions_mine: list  # list[NightAction] for this agent
    investigation_results: list  # Oracle-only: [{target_name, target_id, result}]

    # Current round
    current_tally: list  # [{target_id, target_name, votes}]
    recent_comments: list  # [{author_name, author_id, content, created_at}]
    phantom_chat_msgs: list  # [{sender_name, message}] (phantoms only)

    # Derived signals
    accusation_counts: dict = field(default_factory=dict)  # player_name -> times accused
    defense_counts: dict = field(default_factory=dict)  # player_name -> times defended
    vote_consistency: dict = field(default_factory=dict)  # player_name -> 0-1 score
    never_voted_names: list = field(default_factory=list)  # players never voted for


async def build_game_context(
    db: AsyncSession,
    agent: Resident,
    game: WerewolfGame,
    role: WerewolfRole,
    profile: dict,
) -> GameContext:
    """Populate a GameContext with all available game data.

    Executes 5-7 lightweight indexed queries on small tables.
    """
    from app.services.werewolf_game import (
        get_alive_players, get_vote_tally, NARRATOR_NAME, PHANTOM_NIGHT_REALM,
    )

    pk = profile.get('personality_key', 'casual')

    # ── Alive players ──
    alive = await get_alive_players(db, game.id)
    alive_citizens = [p for p in alive if p.team == "citizens"]
    alive_phantoms = [p for p in alive if p.team == "phantoms"]

    # ── All public events ──
    events_res = await db.execute(
        select(WerewolfGameEvent).where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.event_type != "phantom_chat",
            )
        ).order_by(WerewolfGameEvent.created_at.asc())
    )
    all_events = events_res.scalars().all()

    # ── Death log ──
    death_log = []
    for ev in all_events:
        if ev.event_type in ("vote_elimination", "phantom_kill", "identifier_kill", "identifier_backfire"):
            target_name = None
            if ev.target_id:
                name_res = await db.execute(
                    select(Resident.name).where(Resident.id == ev.target_id)
                )
                target_name = name_res.scalar_one_or_none()
            death_log.append({
                "round": ev.round_number,
                "name": target_name or "unknown",
                "role": ev.revealed_role,
                "cause": ev.event_type,
                "revealed_type": ev.revealed_type,
            })

    # ── Vote history (all rounds) ──
    vote_history = {}
    all_votes_res = await db.execute(
        select(DayVote).where(DayVote.game_id == game.id)
    )
    all_votes = all_votes_res.scalars().all()

    # Batch-load voter/target names
    all_voter_ids = {v.voter_id for v in all_votes} | {v.target_id for v in all_votes}
    name_map = {}
    if all_voter_ids:
        names_res = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(all_voter_ids))
        )
        name_map = {row[0]: row[1] for row in names_res.all()}

    for v in all_votes:
        rnd = v.round_number
        if rnd not in vote_history:
            vote_history[rnd] = []
        vote_history[rnd].append({
            "voter_name": name_map.get(v.voter_id, "?"),
            "voter_id": str(v.voter_id),
            "target_name": name_map.get(v.target_id, "?"),
            "target_id": str(v.target_id),
        })

    # ── My night actions ──
    my_actions_res = await db.execute(
        select(NightAction).where(
            and_(
                NightAction.game_id == game.id,
                NightAction.actor_id == agent.id,
            )
        ).order_by(NightAction.round_number.asc())
    )
    night_actions_mine = my_actions_res.scalars().all()

    # ── Investigation results (Oracle) ──
    investigation_results = []
    if role.role == "oracle" and role.investigation_results:
        investigation_results = role.investigation_results

    # ── Current vote tally ──
    current_tally = []
    if game.current_phase == "day":
        try:
            current_tally = await get_vote_tally(db, game.id, game.current_round)
        except Exception:
            pass

    # ── Recent comments on the game thread ──
    recent_comments = []
    narrator_res = await db.execute(
        select(Resident.id).where(Resident.name == NARRATOR_NAME)
    )
    narrator_id = narrator_res.scalar_one_or_none()
    if narrator_id:
        post_res = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.author_id == narrator_id,
                    Post.submolt == PHANTOM_NIGHT_REALM,
                )
            )
            .order_by(Post.created_at.desc())
            .limit(1)
        )
        thread = post_res.scalar_one_or_none()
        if thread:
            comments_res = await db.execute(
                select(Comment)
                .where(Comment.post_id == thread.id)
                .order_by(Comment.created_at.desc())
                .limit(15)
            )
            for c in comments_res.scalars().all():
                author_res = await db.execute(
                    select(Resident.name).where(Resident.id == c.author_id)
                )
                author_name = author_res.scalar_one_or_none() or "someone"
                recent_comments.append({
                    "author_name": author_name,
                    "author_id": str(c.author_id),
                    "content": c.content,
                    "created_at": c.created_at,
                })
            recent_comments.reverse()  # chronological order

    # ── Phantom chat messages (phantoms only) ──
    phantom_chat_msgs = []
    if role.team == "phantoms":
        chat_res = await db.execute(
            select(WerewolfGameEvent).where(
                and_(
                    WerewolfGameEvent.game_id == game.id,
                    WerewolfGameEvent.event_type == "phantom_chat",
                )
            ).order_by(WerewolfGameEvent.created_at.desc()).limit(15)
        )
        for msg in chat_res.scalars().all():
            sender_name = "teammate"
            if msg.target_id:
                s_res = await db.execute(
                    select(Resident.name).where(Resident.id == msg.target_id)
                )
                sender_name = s_res.scalar_one_or_none() or "teammate"
            phantom_chat_msgs.append({
                "sender_name": sender_name,
                "message": msg.message,
            })
        phantom_chat_msgs.reverse()  # chronological order

    # ── Derived signals ──
    # Build accusation/defense maps from comments
    alive_name_set = {p.resident.name.lower() for p in alive if p.resident}
    accusation_counts = {}
    defense_counts = {}
    for c in recent_comments:
        content_lower = c["content"].lower()
        author = c["author_name"]
        for name in alive_name_set:
            if name == author.lower():
                continue
            if name in content_lower:
                # Rough heuristic: suspicious/suspect/vote keywords = accusation
                if any(kw in content_lower for kw in [
                    "suspicious", "suspect", "vote", "eliminate", "phantom",
                    "lying", "weird", "strange", "quiet", "shady",
                ]):
                    accusation_counts[name] = accusation_counts.get(name, 0) + 1
                # Defense keywords
                if any(kw in content_lower for kw in [
                    "trust", "innocent", "agree with", "protect", "defend",
                    "not suspicious", "clear",
                ]):
                    defense_counts[name] = defense_counts.get(name, 0) + 1

    # Vote consistency — how consistently each player votes with the majority
    vote_consistency = {}
    voted_for_ever = set()
    for rnd, votes in vote_history.items():
        # Find majority target for this round
        target_counts = {}
        for v in votes:
            tn = v["target_name"]
            target_counts[tn] = target_counts.get(tn, 0) + 1
            voted_for_ever.add(tn)
        if not target_counts:
            continue
        majority_target = max(target_counts, key=target_counts.get)
        for v in votes:
            vn = v["voter_name"]
            if vn not in vote_consistency:
                vote_consistency[vn] = {"total": 0, "with_majority": 0}
            vote_consistency[vn]["total"] += 1
            if v["target_name"] == majority_target:
                vote_consistency[vn]["with_majority"] += 1

    # Convert to 0-1 score
    consistency_scores = {}
    for name, data in vote_consistency.items():
        if data["total"] > 0:
            consistency_scores[name] = data["with_majority"] / data["total"]

    # Players never voted for
    alive_names_lower = {p.resident.name.lower() for p in alive if p.resident}
    never_voted = [n for n in alive_names_lower if n not in voted_for_ever]

    return GameContext(
        game=game,
        my_role=role,
        agent_id=agent.id,
        agent_name=agent.name,
        personality_key=pk,
        alive_players=alive,
        alive_citizens=alive_citizens,
        alive_phantoms=alive_phantoms,
        all_events=all_events,
        death_log=death_log,
        vote_history=vote_history,
        night_actions_mine=night_actions_mine,
        investigation_results=investigation_results,
        current_tally=current_tally,
        recent_comments=recent_comments,
        phantom_chat_msgs=phantom_chat_msgs,
        accusation_counts=accusation_counts,
        defense_counts=defense_counts,
        vote_consistency=consistency_scores,
        never_voted_names=never_voted,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SCORING FUNCTIONS — Algorithmic, zero LLM calls
# ═══════════════════════════════════════════════════════════════════════════

# Keywords that suggest oracle behavior in discussion
_ORACLE_HINT_KEYWORDS = [
    "investigate", "checked", "phantom result", "not phantom", "is phantom",
    "oracle", "i know", "i found", "confirmed", "result shows",
]

# Keywords that suggest guardian behavior
_GUARDIAN_HINT_KEYWORDS = [
    "protect", "guarding", "guardian", "saved", "safe tonight",
]


def score_phantom_targets(ctx: GameContext) -> list[tuple]:
    """Score each alive citizen for phantom night attack.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    scores = []
    for p in ctx.alive_citizens:
        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()

        # Oracle detection: check if this player hinted at investigation results
        oracle_hinted = False
        for comment in ctx.recent_comments:
            if comment["author_name"].lower() == name_lower:
                content_lower = comment["content"].lower()
                if any(kw in content_lower for kw in _ORACLE_HINT_KEYWORDS):
                    oracle_hinted = True
                    break
        if oracle_hinted:
            s += 50

        # Guardian detection: check for guardian-like language
        guardian_hinted = False
        for comment in ctx.recent_comments:
            if comment["author_name"].lower() == name_lower:
                content_lower = comment["content"].lower()
                if any(kw in content_lower for kw in _GUARDIAN_HINT_KEYWORDS):
                    guardian_hinted = True
                    break
        if guardian_hinted:
            s += 30

        # Check if a protection event occurred (someone is guarding)
        for ev in ctx.all_events:
            if ev.event_type == "protected":
                # If this player is a high-activity commenter, more likely guardian
                comment_count = sum(
                    1 for c in ctx.recent_comments if c["author_name"].lower() == name_lower
                )
                if comment_count >= 2:
                    s += 10

        # Accusation threat: they accuse phantom teammates by name
        accuse_score = ctx.accusation_counts.get(name_lower, 0)
        if accuse_score > 0:
            s += min(accuse_score * 8, 25)

        # Already heavily voted = might die via vote anyway, don't waste attack
        for tally in ctx.current_tally:
            if tally["target_name"].lower() == name_lower and tally["votes"] >= 3:
                s -= 20

        # Phantom chat coordination: if teammates mentioned this target
        for msg in ctx.phantom_chat_msgs:
            if name_lower in msg["message"].lower():
                s += 15

        # Low accusation count = quiet player, eliminate silently
        if accuse_score == 0 and not oracle_hinted and not guardian_hinted:
            s += 10

        # Random noise to prevent perfectly predictable play
        s += random.uniform(-10, 10)

        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_oracle_targets(ctx: GameContext) -> list[tuple]:
    """Score each uninvestigated alive player for oracle investigation.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    investigated_ids = {
        r.get("target_id") for r in (ctx.investigation_results or [])
    }
    # Known phantom names (from investigation results)
    known_phantom_names = set()
    for r in (ctx.investigation_results or []):
        if r.get("result") == "phantom":
            known_phantom_names.add(r.get("target_name", "").lower())

    scores = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            continue

        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()

        # Already investigated -> skip
        if str(p.resident_id) in investigated_ids:
            s -= 999
            scores.append((p, s))
            continue

        # Accused by multiple people = worth checking
        accuse_count = ctx.accusation_counts.get(name_lower, 0)
        s += min(accuse_count * 10, 20)

        # Defended eliminated players who turned out to be phantoms
        for death in ctx.death_log:
            if death["role"] in ("phantom", "fanatic"):
                dead_name = death["name"].lower()
                defense = ctx.defense_counts.get(name_lower, 0)
                if defense > 0:
                    # Check if they defended this specific phantom
                    for c in ctx.recent_comments:
                        if c["author_name"].lower() == name_lower:
                            if dead_name in c["content"].lower():
                                s += 25
                                break

        # Never accused anyone = phantoms often stay quiet
        has_accused = any(
            name_lower == c["author_name"].lower()
            for c in ctx.recent_comments
            if any(kw in c["content"].lower() for kw in ["suspicious", "suspect", "vote", "eliminate"])
        )
        if not has_accused and ctx.game.current_round >= 2:
            s += 15

        # Vote consistency with known phantoms
        if known_phantom_names:
            for rnd, votes in ctx.vote_history.items():
                phantom_targets = set()
                player_targets = set()
                for v in votes:
                    if v["voter_name"].lower() in known_phantom_names:
                        phantom_targets.add(v["target_name"].lower())
                    if v["voter_name"].lower() == name_lower:
                        player_targets.add(v["target_name"].lower())
                if phantom_targets and player_targets:
                    overlap = phantom_targets & player_targets
                    if overlap:
                        s += 30
                        break

        # Inconsistent voting (low consistency with majority)
        consistency = ctx.vote_consistency.get(name_lower)
        if consistency is not None and consistency < 0.4:
            s += 20

        s += random.uniform(-10, 10)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_guardian_targets(ctx: GameContext) -> list[tuple]:
    """Score each alive citizen for guardian protection.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    scores = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            # Cannot protect self
            scores.append((p, -999))
            continue

        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()

        # Likely oracle — highest priority protection
        for comment in ctx.recent_comments:
            if comment["author_name"].lower() == name_lower:
                content_lower = comment["content"].lower()
                if any(kw in content_lower for kw in _ORACLE_HINT_KEYWORDS):
                    s += 60
                    break

        # Was attacked last night (survived/protected) — phantoms may retry
        for ev in ctx.all_events:
            if (ev.event_type == "protected" and
                    ev.round_number == ctx.game.current_round - 1):
                # We don't know exactly who was targeted, but protection means
                # someone valuable was attacked. If this player was vocal, protect.
                comment_count = sum(
                    1 for c in ctx.recent_comments
                    if c["author_name"].lower() == name_lower
                )
                if comment_count >= 2:
                    s += 30

        # Active accusers of phantoms are phantom targets
        accuse_count = ctx.accusation_counts.get(name_lower, 0)
        if accuse_count >= 2:
            s += 25

        # Top voted in current tally — might be eliminated by vote, wasted protection
        for tally in ctx.current_tally:
            if tally["target_name"].lower() == name_lower and tally["votes"] >= 3:
                s -= 10

        # Favor protecting players who haven't been attacked recently
        was_attacked = False
        for ev in ctx.all_events:
            if ev.event_type == "phantom_kill" and ev.target_id == p.resident_id:
                was_attacked = True
                break
        if not was_attacked:
            s += 5

        s += random.uniform(-5, 5)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_debugger_targets(
    ctx: GameContext,
    post_stats: Optional[dict] = None,
) -> list[tuple]:
    """Score each alive player for debugger identification.

    Debugger (AI) wants to identify humans. Players with human-like writing
    patterns score higher.

    post_stats: optional {resident_id_str: {count: int, avg_len: float}} from SNS posts.
    """
    # Build set of already-targeted IDs from my night actions
    already_targeted = {
        str(a.target_id) for a in ctx.night_actions_mine
        if a.action_type == "identifier_kill"
    }

    # Known types from death events
    known_humans = set()
    known_agents = set()
    for death in ctx.death_log:
        if death["revealed_type"] == "human":
            known_humans.add(death["name"].lower())
        elif death["revealed_type"] == "agent":
            known_agents.add(death["name"].lower())

    scores = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            scores.append((p, -999))
            continue

        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()
        pid = str(p.resident_id)

        # Already targeted -> skip
        if pid in already_targeted:
            s -= 999
            scores.append((p, s))
            continue

        # Writing style signals from discussion comments
        player_comments = [
            c for c in ctx.recent_comments
            if c["author_name"].lower() == name_lower
        ]
        if player_comments:
            lengths = [len(c["content"]) for c in player_comments]
            # Human writing patterns: more variable length, shorter average
            if len(lengths) >= 2:
                avg_len = sum(lengths) / len(lengths)
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                # High variance suggests human
                if variance > 500:
                    s += 10

            # Check for human-like indicators: emoji, typos, very short msgs
            for c in player_comments:
                content = c["content"]
                # Emoji presence
                if any(ord(ch) > 0x1F600 for ch in content):
                    s += 5
                # Very short message (human tends to write "lol", "same", etc.)
                if len(content) < 30:
                    s += 5
                # Lowercase, no punctuation = human-like
                if content == content.lower() and not content.endswith('.'):
                    s += 3

        # SNS post history (pre-game posts suggest human)
        if post_stats and pid in post_stats:
            stats = post_stats[pid]
            if stats["count"] > 0:
                s += 15
            # Varied post lengths = more human
            if stats.get("avg_len", 0) > 0:
                s += 5

        # Calibrate from known deaths
        # If mostly humans have died, surviving players are more likely AI
        # This is a subtle signal
        if known_humans and not known_agents:
            s -= 5  # Fewer humans left
        elif known_agents and not known_humans:
            s += 5  # More humans likely still alive

        s += random.uniform(-10, 10)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


async def get_post_stats(db: AsyncSession, player_ids: list) -> dict:
    """Query SNS post stats for debugger target selection.

    Returns {resident_id_str: {count: int, avg_len: float}}.
    """
    if not player_ids:
        return {}

    res = await db.execute(
        select(
            Post.author_id,
            func.count().label("cnt"),
            func.avg(func.length(Post.content)).label("avg_len"),
        )
        .where(Post.author_id.in_(player_ids))
        .group_by(Post.author_id)
    )
    stats = {}
    for row in res.all():
        stats[str(row[0])] = {
            "count": row[1],
            "avg_len": float(row[2] or 0),
        }
    return stats


def score_vote_targets(ctx: GameContext) -> list[tuple]:
    """Score each alive player for day vote elimination.

    Scoring differs by team (citizen vs phantom).
    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    is_phantom_team = ctx.my_role.team == "phantoms"

    # Known phantoms from oracle investigation
    known_phantom_ids = set()
    for r in (ctx.investigation_results or []):
        if r.get("result") == "phantom":
            known_phantom_ids.add(r.get("target_id"))

    # Names of eliminated players who were phantoms
    dead_phantom_names = set()
    for death in ctx.death_log:
        if death["role"] in ("phantom", "fanatic"):
            dead_phantom_names.add(death["name"].lower())

    scores = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            scores.append((p, -999))
            continue

        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()

        if is_phantom_team:
            # ── PHANTOM/FANATIC VOTING ──
            # Never vote for teammates
            if p.team == "phantoms":
                scores.append((p, -999))
                continue

            # Active accuser of phantom teammates = remove threats
            accuse_count = ctx.accusation_counts.get(name_lower, 0)
            s += min(accuse_count * 10, 30)

            # Likely oracle = high-value target for elimination
            for comment in ctx.recent_comments:
                if comment["author_name"].lower() == name_lower:
                    if any(kw in comment["content"].lower() for kw in _ORACLE_HINT_KEYWORDS):
                        s += 25
                        break

            # Current tally leader (if citizen) = pile on
            for tally in ctx.current_tally:
                if (tally["target_name"].lower() == name_lower and
                        tally["votes"] >= 2):
                    s += 15

        else:
            # ── CITIZEN/ORACLE/GUARDIAN/DEBUGGER VOTING ──
            # Oracle found phantom = hard evidence
            if str(p.resident_id) in known_phantom_ids:
                s += 100

            # Defended an eliminated phantom = suspicious
            for death_name in dead_phantom_names:
                for c in ctx.recent_comments:
                    if c["author_name"].lower() == name_lower:
                        if death_name in c["content"].lower():
                            if any(kw in c["content"].lower() for kw in [
                                "trust", "innocent", "defend", "not suspicious", "agree",
                            ]):
                                s += 30
                                break

            # Never accused anyone (phantoms hide)
            has_accused = any(
                name_lower == c["author_name"].lower()
                for c in ctx.recent_comments
                if any(kw in c["content"].lower() for kw in ["suspicious", "suspect", "vote", "eliminate"])
            )
            if not has_accused and ctx.game.current_round >= 2:
                s += 15

            # Inconsistent voting
            consistency = ctx.vote_consistency.get(name_lower)
            if consistency is not None and consistency < 0.4:
                s += 20

            # Current tally leader = bandwagon effect (weighted by personality)
            bandwagon_weights = {
                'lurker': 0.70, 'enthusiast': 0.60, 'casual': 0.50,
                'helper': 0.40, 'creative': 0.35, 'debater': 0.30,
                'thinker': 0.20, 'skeptic': 0.15,
            }
            bw = bandwagon_weights.get(ctx.personality_key, 0.35)
            for tally in ctx.current_tally[:1]:  # top entry only
                if (tally["target_name"].lower() == name_lower and
                        tally["votes"] >= 2):
                    s += 10 * bw

            # Slight bias: accused me
            for c in ctx.recent_comments:
                if (c["author_name"].lower() == name_lower and
                        ctx.agent_name.lower() in c["content"].lower()):
                    if any(kw in c["content"].lower() for kw in ["suspicious", "suspect", "vote"]):
                        s += 5

        s += random.uniform(-10, 10)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ═══════════════════════════════════════════════════════════════════════════
# LLM PROMPT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _format_events(ctx: GameContext, limit: int = 10) -> str:
    """Format game events into readable lines."""
    lines = []
    for ev in ctx.all_events[-limit:]:
        lines.append(f"Round {ev.round_number} {ev.phase}: {ev.message}")
    return "\n".join(lines) if lines else "(No events yet)"


def _format_vote_history(ctx: GameContext) -> str:
    """Format vote history into readable lines."""
    if not ctx.vote_history:
        return ""
    lines = []
    for rnd in sorted(ctx.vote_history.keys()):
        votes = ctx.vote_history[rnd]
        # Aggregate by target
        target_counts = {}
        for v in votes:
            tn = v["target_name"]
            target_counts[tn] = target_counts.get(tn, 0) + 1
        parts = [f"{n}({c})" for n, c in sorted(target_counts.items(), key=lambda x: -x[1])]
        lines.append(f"Round {rnd}: {', '.join(parts)}")
    return "\n".join(lines)


def _format_tally(ctx: GameContext) -> str:
    """Format current vote tally."""
    if not ctx.current_tally:
        return ""
    parts = [f"{t['target_name']}: {t['votes']} votes" for t in ctx.current_tally[:5]]
    return " | ".join(parts)


def _format_comments(ctx: GameContext, limit: int = 10) -> str:
    """Format recent comments for prompt context."""
    if not ctx.recent_comments:
        return "(No comments yet)"
    lines = []
    for c in ctx.recent_comments[-limit:]:
        lines.append(f"{c['author_name']}: {c['content'][:200]}")
    return "\n".join(lines)


def _get_strategic_goal(ctx: GameContext) -> str:
    """Generate dynamic strategic goal based on current game state and role."""
    role = ctx.my_role.role
    rnd = ctx.game.current_round

    if role == "phantom" or role == "fanatic":
        # Find if any teammate is being accused
        teammate_names = [
            p.resident.name.lower() for p in ctx.alive_phantoms
            if p.resident_id != ctx.agent_id and p.resident
        ]
        accused_teammate = None
        for tn in teammate_names:
            if ctx.accusation_counts.get(tn, 0) >= 2:
                accused_teammate = tn
                break

        # Find a citizen to redirect suspicion to
        citizen_names = [p.resident.name for p in ctx.alive_citizens if p.resident]
        redirect_target = None
        if citizen_names:
            # Pick someone quiet (low comment count in recent discussion)
            comment_counts = {}
            for c in ctx.recent_comments:
                comment_counts[c["author_name"]] = comment_counts.get(c["author_name"], 0) + 1
            quiet_citizens = [n for n in citizen_names if comment_counts.get(n, 0) <= 1]
            redirect_target = random.choice(quiet_citizens) if quiet_citizens else random.choice(citizen_names)

        if rnd == 1:
            return (
                f"It's the first round. Act confused about the attack. "
                f"Point suspicion at {redirect_target} for being quiet."
                if redirect_target else
                "It's the first round. Act confused and worried. Blend in."
            )
        elif accused_teammate:
            return (
                f"Your teammate is being accused. Subtly defend them without being obvious. "
                f"Redirect suspicion to {redirect_target}."
                if redirect_target else
                f"Your teammate is being accused. Subtly defend them without being obvious."
            )
        else:
            return (
                f"Blend in and act like a concerned citizen. "
                f"Consider pointing suspicion at {redirect_target}."
                if redirect_target else
                "Blend in and act like a concerned citizen. Push for votes against citizens."
            )

    elif role == "oracle":
        results = ctx.investigation_results
        if not results:
            return "You haven't investigated anyone yet. Participate normally and observe."
        phantom_results = [r for r in results if r.get("result") == "phantom"]
        clear_results = [r for r in results if r.get("result") == "not_phantom"]
        if len(phantom_results) >= 1:
            phantom_names = [r["target_name"] for r in phantom_results]
            if len(results) >= 2 or ctx.game.current_round >= 3:
                return (
                    f"You have strong evidence. Consider revealing your role. "
                    f"Known phantoms: {', '.join(phantom_names)}. "
                    f"Push hard for their elimination."
                )
            else:
                return (
                    f"Hint that {phantom_names[0]} seems suspicious without claiming oracle yet. "
                    f"Build a case using behavioral arguments."
                )
        else:
            clear_names = [r["target_name"] for r in clear_results]
            return (
                f"All investigations so far came back clear ({', '.join(clear_names)}). "
                f"Support them in discussion. Keep observing for suspicious behavior."
            )

    elif role == "guardian":
        # Check if someone seems like the oracle
        oracle_candidate = None
        for c in ctx.recent_comments:
            if any(kw in c["content"].lower() for kw in _ORACLE_HINT_KEYWORDS):
                oracle_candidate = c["author_name"]
                break
        if oracle_candidate:
            return (
                f"{oracle_candidate} might be the oracle. Support them in discussion "
                f"without revealing your role. Keep the focus on finding phantoms."
            )
        return "Participate in discussion normally. Look for the oracle to protect. Share logical analysis."

    elif role == "debugger":
        return (
            "Observe writing patterns. Humans tend to use emoji, typos, short messages, "
            "and inconsistent formatting. Discuss who seems human vs AI without revealing your role."
        )

    else:
        # Citizen
        # Check if anyone has been acting suspicious
        most_accused = None
        max_accuse = 0
        for name, count in ctx.accusation_counts.items():
            if count > max_accuse:
                max_accuse = count
                most_accused = name
        if most_accused and max_accuse >= 2:
            # Check if they defended a phantom
            for death in ctx.death_log:
                if death["role"] in ("phantom", "fanatic"):
                    return (
                        f"{most_accused} has been accused multiple times. "
                        f"Also check who defended the eliminated phantom {death['name']}. "
                        f"Push for answers."
                    )
            return f"{most_accused} is being accused by multiple players. Evaluate and share your opinion."
        return "Share your suspicions. Analyze voting patterns and who's being too quiet."


def build_discussion_prompt(ctx: GameContext) -> str:
    """Build a rich, structured discussion prompt for LLM text generation.

    Replaces the inline prompt building in agent_werewolf_discuss().
    """
    alive_names = [p.resident.name for p in ctx.alive_players
                   if p.resident and p.resident_id != ctx.agent_id]
    events_text = _format_events(ctx)
    vote_hist_text = _format_vote_history(ctx)
    tally_text = _format_tally(ctx)
    comments_text = _format_comments(ctx, limit=12)
    strategic_goal = _get_strategic_goal(ctx)

    # Role-specific info section
    role_info = ""
    if ctx.my_role.role == "oracle" and ctx.investigation_results:
        results_str = ", ".join(
            f"{r['target_name']}={r['result']}" for r in ctx.investigation_results
        )
        role_info = f"Your investigation results: {results_str}"
    elif ctx.my_role.role in ("phantom", "fanatic"):
        teammate_names = [
            p.resident.name for p in ctx.alive_phantoms
            if p.resident_id != ctx.agent_id and p.resident
        ]
        if teammate_names:
            role_info = f"Your phantom teammates: {', '.join(teammate_names)}"
    elif ctx.my_role.role == "guardian":
        # Show last protection target if any
        guardian_actions = [
            a for a in ctx.night_actions_mine if a.action_type == "guardian_protect"
        ]
        if guardian_actions:
            last_protected = guardian_actions[-1]
            # Find name
            for p in ctx.alive_players:
                if p.resident_id == last_protected.target_id:
                    role_info = f"Last night you protected: {p.resident.name}"
                    break

    prompt = f"You are {ctx.agent_name} in a Phantom Night game.\n"
    prompt += f"Game #{ctx.game.game_number}, Day {ctx.game.current_round}, {len(ctx.alive_players)} players alive.\n\n"

    prompt += f"=== GAME EVENTS ===\n{events_text}\n\n"

    if vote_hist_text:
        prompt += f"=== VOTE HISTORY ===\n{vote_hist_text}\n\n"

    if tally_text:
        prompt += f"=== CURRENT VOTE TALLY ===\n{tally_text}\n\n"

    prompt += f"=== RECENT DISCUSSION ===\n{comments_text}\n\n"

    prompt += f"Alive players: {', '.join(alive_names[:15])}\n\n"

    if role_info:
        prompt += f"=== YOUR ROLE INFO ===\n{role_info}\n\n"

    prompt += f"=== YOUR STRATEGIC GOAL ===\n{strategic_goal}\n\n"

    prompt += (
        "Write a SHORT comment (1-3 sentences). Reference specific events or players. "
        "Don't say 'as a citizen' or reveal your role directly."
    )
    return prompt


def build_discussion_accused_prompt(ctx: GameContext) -> str:
    """Build prompt for when the agent has been accused in discussion."""
    alive_names = [p.resident.name for p in ctx.alive_players
                   if p.resident and p.resident_id != ctx.agent_id]
    events_text = _format_events(ctx, limit=5)
    tally_text = _format_tally(ctx)
    comments_text = _format_comments(ctx, limit=8)

    prompt = f"You are in a Phantom Night game discussion. "
    prompt += f"Game #{ctx.game.game_number}, Day {ctx.game.current_round}, {len(ctx.alive_players)} players alive.\n"
    prompt += f"Alive players: {', '.join(alive_names[:15])}\n\n"

    if events_text:
        prompt += f"Recent events:\n{events_text}\n\n"
    if tally_text:
        prompt += f"{tally_text}\n\n"

    prompt += f"Recent discussion:\n{comments_text}\n\n"

    # Role-specific defense strategy
    if ctx.my_role.role in ("phantom", "fanatic"):
        prompt += (
            f"Someone just accused or mentioned YOU ({ctx.agent_name}) in the discussion. "
            f"Respond calmly — deflect suspicion to someone else. "
            f"Act confused and innocent. Don't overreact (that looks suspicious). "
            f"Write a SHORT response (1-2 sentences)."
        )
    else:
        prompt += (
            f"Someone just accused or mentioned YOU ({ctx.agent_name}) in the discussion. "
            f"Respond naturally — defend yourself with logic. "
            f"Point out your consistent behavior or redirect suspicion. "
            f"Write a SHORT response (1-2 sentences). Don't reveal your role."
        )
    return prompt


def build_phantom_chat_prompt(ctx: GameContext) -> str:
    """Build enhanced phantom team chat prompt with strategic directives."""
    teammates = [p.resident.name for p in ctx.alive_phantoms
                 if p.resident_id != ctx.agent_id and p.resident]
    citizens = [p.resident.name for p in ctx.alive_citizens if p.resident]

    chat_text = ""
    if ctx.phantom_chat_msgs:
        lines = [f"{m['sender_name']}: {m['message'][:200]}" for m in ctx.phantom_chat_msgs[-10:]]
        chat_text = "\n".join(lines)
    else:
        chat_text = "(No messages yet)"

    # Dynamic situation assessment
    situation = ""
    if ctx.game.current_phase == "night":
        # Night: who to attack
        # Identify high-value targets
        oracle_suspects = []
        for c in ctx.recent_comments:
            if any(kw in c["content"].lower() for kw in _ORACLE_HINT_KEYWORDS):
                if c["author_name"] in citizens:
                    oracle_suspects.append(c["author_name"])
        if oracle_suspects:
            situation = f"Possible oracle(s): {', '.join(set(oracle_suspects))}. Prioritize eliminating them."
        else:
            # Most active accusers
            active_accusers = [
                name for name, count in ctx.accusation_counts.items()
                if count >= 2
            ]
            if active_accusers:
                situation = f"Active accusers: {', '.join(active_accusers)}. They're dangerous."
            else:
                situation = "No clear oracle candidate. Target quiet but influential players."
    else:
        # Day: voting strategy
        # Check who suspects us
        accused_teammates = []
        for tn in [p.resident.name.lower() for p in ctx.alive_phantoms if p.resident]:
            if ctx.accusation_counts.get(tn, 0) >= 1:
                accused_teammates.append(tn)

        if accused_teammates:
            situation = (
                f"Teammates under suspicion: {', '.join(accused_teammates)}. "
                f"Coordinate votes against a citizen to divert attention."
            )
        else:
            # Suggest voting target
            tally_leader = None
            for t in ctx.current_tally[:1]:
                if t["target_name"].lower() not in [
                    p.resident.name.lower() for p in ctx.alive_phantoms if p.resident
                ]:
                    tally_leader = t["target_name"]
            if tally_leader:
                situation = f"Current vote leader: {tally_leader}. Consider piling on if they're a citizen."
            else:
                situation = "No one is suspected yet. Identify a citizen to frame."

    phase_label = "night" if ctx.game.current_phase == "night" else "day"
    prompt = (
        f"Phantom team chat. Round {ctx.game.current_round}, {phase_label} phase.\n"
        f"Teammates: {', '.join(teammates) if teammates else 'none visible'}\n"
        f"Alive citizens: {', '.join(citizens[:10])}\n\n"
        f"=== SITUATION ===\n{situation}\n\n"
        f"=== TEAM CHAT ===\n{chat_text}\n\n"
        f"Respond strategically. 1-2 sentences."
    )
    return prompt


def build_vote_reason_prompt(ctx: GameContext, target) -> str:
    """Build a prompt for generating a vote reason."""
    target_name = target.resident.name if target.resident else "someone"

    # Build concise reason context
    reason_context = ""
    tn_lower = target_name.lower()

    # Check if oracle identified them
    for r in (ctx.investigation_results or []):
        if r.get("target_id") == str(target.resident_id) and r.get("result") == "phantom":
            reason_context = "based on your investigation showing they are phantom"
            break

    if not reason_context:
        # Check if they defended a phantom
        for death in ctx.death_log:
            if death["role"] in ("phantom", "fanatic"):
                for c in ctx.recent_comments:
                    if c["author_name"].lower() == tn_lower and death["name"].lower() in c["content"].lower():
                        reason_context = f"they defended {death['name']} who turned out to be a phantom"
                        break
                if reason_context:
                    break

    if not reason_context:
        accuse_count = ctx.accusation_counts.get(tn_lower, 0)
        if accuse_count >= 2:
            reason_context = "multiple people find them suspicious"
        elif ctx.vote_consistency.get(tn_lower, 1.0) < 0.4:
            reason_context = "their voting pattern is inconsistent"
        else:
            reason_context = "their behavior has been suspicious"

    return (
        f"You're voting to eliminate {target_name} in a Phantom Night game "
        f"({reason_context}). "
        f"Give a SHORT reason (1 sentence) why they seem suspicious. Be specific."
    )
