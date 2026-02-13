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
from app.models.werewolf_game import (
    WerewolfGame, WerewolfRole, WerewolfGameEvent, NightAction, DayVote,
    GameMessage,
)
from app.models.ai_personality import AIRelationship, AIMemoryEpisode

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

    # SNS integration
    sns_relationships: dict = field(default_factory=dict)
    # {resident_id_str: {'trust': float, 'familiarity': float, 'interaction_count': int}}
    past_game_memories: list = field(default_factory=list)
    # [{'summary': str, 'sentiment': float, 'related_ids': list, 'importance': float}]


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
        get_alive_players, get_vote_tally,
    )

    pk = profile.get('personality_key', 'casual')

    # ── Alive players ──
    alive = await get_alive_players(db, game.id)
    alive_citizens = [p for p in alive if p.team == "citizens"]
    alive_phantoms = [p for p in alive if p.team == "phantoms"]

    # ── All public events (exclude phantom_chat and agent thoughts) ──
    events_res = await db.execute(
        select(WerewolfGameEvent).where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.event_type != "phantom_chat",
                ~WerewolfGameEvent.event_type.like("agent_thought_%"),
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

    # ── Recent chat messages (replaces SNS comment lookup) ──
    recent_comments = []
    chat_res = await db.execute(
        select(GameMessage)
        .where(
            and_(
                GameMessage.game_id == game.id,
                GameMessage.message_type == "chat",
            )
        )
        .order_by(GameMessage.created_at.desc())
        .limit(15)
    )
    for m in reversed(chat_res.scalars().all()):  # chronological order
        recent_comments.append({
            "author_name": m.sender_name,
            "author_id": str(m.sender_id) if m.sender_id else "",
            "content": m.content,
            "created_at": m.created_at,
        })

    # ── Phantom chat messages (phantoms only) ──
    phantom_chat_msgs = []
    if role.team == "phantoms":
        pchat_res = await db.execute(
            select(GameMessage).where(
                and_(
                    GameMessage.game_id == game.id,
                    GameMessage.message_type == "phantom_chat",
                )
            ).order_by(GameMessage.created_at.desc()).limit(15)
        )
        for msg in reversed(pchat_res.scalars().all()):  # chronological order
            phantom_chat_msgs.append({
                "sender_name": msg.sender_name,
                "message": msg.content,
            })

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

    # ── SNS relationships ──
    sns_relationships = {}
    rels_res = await db.execute(
        select(AIRelationship).where(AIRelationship.agent_id == agent.id)
    )
    for r in rels_res.scalars().all():
        sns_relationships[str(r.target_id)] = {
            'trust': r.trust or 0.0,
            'familiarity': r.familiarity or 0.0,
            'interaction_count': r.interaction_count or 0,
        }

    # ── Past werewolf game memories ──
    alive_id_strs = [str(p.resident_id) for p in alive]
    past_game_memories = []
    mem_res = await db.execute(
        select(AIMemoryEpisode).where(
            and_(
                AIMemoryEpisode.resident_id == agent.id,
                AIMemoryEpisode.episode_type.like("werewolf_%"),
            )
        ).order_by(AIMemoryEpisode.importance.desc(),
                   AIMemoryEpisode.created_at.desc())
        .limit(15)
    )
    for m in mem_res.scalars().all():
        related = m.related_resident_ids or []
        if any(rid in alive_id_strs for rid in related) or not related:
            past_game_memories.append({
                'summary': m.summary,
                'sentiment': m.sentiment,
                'related_ids': related,
                'importance': m.importance,
            })
            if len(past_game_memories) >= 8:
                break

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
        sns_relationships=sns_relationships,
        past_game_memories=past_game_memories,
    )


# ═══════════════════════════════════════════════════════════════════════════
# EMOTIONAL STATE — computed per cycle from game events + agent traits
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalState:
    stress: float = 0.0        # 0-1 (accused/voted → high)
    confidence: float = 0.5    # 0-1 (evidence held → high)
    engagement: float = 0.7    # 0-1 (fatigue/attention → decreases)
    frustration: float = 0.0   # 0-1 (ally died / grudge → high)
    excitement: float = 0.0    # 0-1 (phantom found / critical moment → high)


def compute_emotional_state(ctx: GameContext, traits: dict) -> EmotionalState:
    """Compute emotional state from game events and agent traits. No LLM calls."""
    stress = 0.0
    confidence = 0.5
    engagement = 0.7
    frustration = 0.0
    excitement = 0.0

    skill = traits.get('skill_level', 0.5)
    baseline = traits.get('emotional_baseline', 0.0)
    attn = traits.get('attention_span', 0.6)
    grudge = traits.get('grudge_tendency', 0.3)
    fatigue_type = traits.get('fatigue_type', 'steady')

    my_name_lower = ctx.agent_name.lower()

    # --- Accused by multiple people ---
    my_accusations = ctx.accusation_counts.get(my_name_lower, 0)
    if my_accusations >= 3:
        stress += 0.4
        frustration += 0.3
    elif my_accusations >= 1:
        stress += my_accusations * 0.15
        frustration += my_accusations * 0.1

    # --- Voted against me ---
    votes_against_me = 0
    for tally in ctx.current_tally:
        if tally["target_name"].lower() == my_name_lower:
            votes_against_me = tally["votes"]
            break
    if votes_against_me >= 1:
        stress += votes_against_me * 0.15
        confidence -= votes_against_me * 0.1

    # --- Ally died recently ---
    if ctx.death_log:
        last_death = ctx.death_log[-1]
        if last_death["round"] == ctx.game.current_round or \
           last_death["round"] == ctx.game.current_round - 1:
            # If same team died
            if ctx.my_role.team == "citizens" and last_death["role"] in ("citizen", "oracle", "guardian"):
                stress += 0.2
                frustration += 0.15
            elif ctx.my_role.team == "phantoms" and last_death["role"] in ("phantom", "fanatic"):
                stress += 0.2
                frustration += 0.15

    # --- Oracle found phantom (excitement for citizens team) ---
    if ctx.investigation_results:
        phantom_found = any(r.get("result") == "phantom" for r in ctx.investigation_results)
        if phantom_found:
            excitement += 0.3
            confidence += 0.2

    # --- Round progression × fatigue type ---
    round_frac = min(ctx.game.current_round / 6.0, 1.0)
    if fatigue_type == 'fader':
        engagement = 1.0 - round_frac * 0.5   # starts 1.0, drops to 0.5
    elif fatigue_type == 'grower':
        engagement = 0.7 + round_frac * 0.3    # starts 0.7, grows to 1.0
    else:  # steady
        engagement = 0.8

    # --- Attention span scales engagement ---
    engagement *= attn

    # --- Emotional baseline adjusts stress/frustration amplitude ---
    # baseline -0.5 (nervous) amplifies stress by +25%
    # baseline +0.5 (calm) dampens stress by -25%
    baseline_mult = 1.0 - baseline * 0.5  # -0.5→1.25, +0.5→0.75
    stress *= baseline_mult
    frustration *= baseline_mult

    # --- Grudge: if accused and grudge tendency is high ---
    if my_accusations >= 1 and grudge > 0.5:
        frustration += grudge * 0.2

    # --- Betrayal shock: accused by SNS-trusted player ---
    for c in ctx.recent_comments:
        if ctx.agent_name.lower() in c["content"].lower():
            accuser_id = c.get("author_id", "")
            rel = ctx.sns_relationships.get(accuser_id)
            if rel and rel['trust'] > 0.3:
                stress += 0.2
                frustration += 0.15
                break  # one betrayal shock per cycle

    # --- Playing with familiar faces → slight excitement ---
    familiar_count = sum(1 for p in ctx.alive_players
                         if ctx.sns_relationships.get(str(p.resident_id), {}).get('familiarity', 0) > 0.4)
    if familiar_count >= 2:
        excitement += 0.1

    # --- Late game excitement ---
    alive_count = len(ctx.alive_players)
    if alive_count <= 4:
        excitement += 0.2

    # Clamp all values to [0, 1]
    return EmotionalState(
        stress=max(0.0, min(1.0, stress)),
        confidence=max(0.0, min(1.0, confidence)),
        engagement=max(0.0, min(1.0, engagement)),
        frustration=max(0.0, min(1.0, frustration)),
        excitement=max(0.0, min(1.0, excitement)),
    )


# ═══════════════════════════════════════════════════════════════════════════
# SKILL GATE — strategy signal visibility based on skill level
# ═══════════════════════════════════════════════════════════════════════════

def _skill_gate(skill: float, threshold: float) -> bool:
    """Check if agent's skill is high enough to notice a strategic signal.

    skill >> threshold → always notices
    skill << threshold → never notices
    intermediate → probabilistic
    """
    if skill >= threshold + 0.3:
        return True
    if skill < threshold - 0.2:
        return False
    # Probabilistic zone: linear interpolation
    prob = (skill - (threshold - 0.2)) / 0.5
    return random.random() < prob


# Signal thresholds for _skill_gate
_SIGNAL_THRESHOLDS = {
    'accusation_count': 0.1,         # almost everyone notices
    'phantom_chat_coordination': 0.2, # beginners can read chat
    'bandwagon_detection': 0.2,       # vote counts are visible
    'oracle_hint_detection': 0.3,     # needs keyword analysis
    'guardian_hint_detection': 0.4,   # more advanced inference
    'heavy_vote_avoidance': 0.4,      # tactical judgment
    'vote_consistency_analysis': 0.6, # pattern analysis
    'dead_phantom_defender': 0.7,     # compound reasoning
    'phantom_vote_correlation': 0.8,  # advanced meta-analysis
    'oracle_confirmed_evidence': 0.0, # everyone can use this
}


def _volatility_noise(skill: float, emotion: EmotionalState,
                      base_range: float = 10.0) -> float:
    """Generate noise scaled by skill level and emotional state.

    Low skill + high stress = very noisy (near-random choices).
    High skill + calm = precise (small noise).
    """
    skill_mult = 0.5 + (1.0 - skill) * 2.5    # skill 1.0→0.5x, skill 0.0→3.0x
    stress_mult = 1.0 + emotion.stress * 0.8    # stress 1.0→1.8x
    conf_mult = 1.0 - emotion.confidence * 0.2  # confidence 1.0→0.8x
    total = base_range * skill_mult * stress_mult * conf_mult
    return random.uniform(-total, total)


def maybe_inject_mistake(ranked: list, ctx: GameContext,
                         traits: dict, emotion: EmotionalState) -> list:
    """Low-skill/high-stress agents may choose a suboptimal target.

    Swaps top pick with 2nd-4th pick. Never swaps -999 entries (safety).
    """
    if len(ranked) < 2:
        return ranked

    chance = traits.get('mistake_proneness', 0.3) + \
             emotion.stress * 0.15 + emotion.frustration * 0.1
    chance = min(chance, 0.6)  # cap at 60%

    if random.random() < chance:
        # Find safe swap candidates (score > -900, not self/teammate)
        safe = [i for i, (_, s) in enumerate(ranked[:4]) if s > -900]
        if len(safe) >= 2:
            idx = random.choice(safe[1:])  # pick non-top
            ranked[0], ranked[idx] = ranked[idx], ranked[0]

    return ranked


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


def score_phantom_targets(ctx: GameContext, skill: float = 0.5,
                          emotion: Optional[EmotionalState] = None) -> list[tuple]:
    """Score each alive citizen for phantom night attack.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    if emotion is None:
        emotion = EmotionalState()

    scores = []
    for p in ctx.alive_citizens:
        s = 0.0
        name = p.resident.name if p.resident else ""
        name_lower = name.lower()

        # Oracle detection: check if this player hinted at investigation results
        oracle_hinted = False
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['oracle_hint_detection']):
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
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['guardian_hint_detection']):
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
                comment_count = sum(
                    1 for c in ctx.recent_comments if c["author_name"].lower() == name_lower
                )
                if comment_count >= 2:
                    s += 10

        # Accusation threat: they accuse phantom teammates by name
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['accusation_count']):
            accuse_score = ctx.accusation_counts.get(name_lower, 0)
            if accuse_score > 0:
                s += min(accuse_score * 8, 25)
        else:
            accuse_score = 0

        # Already heavily voted = might die via vote anyway, don't waste attack
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['heavy_vote_avoidance']):
            for tally in ctx.current_tally:
                if tally["target_name"].lower() == name_lower and tally["votes"] >= 3:
                    s -= 20

        # Phantom chat coordination: if teammates mentioned this target
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['phantom_chat_coordination']):
            for msg in ctx.phantom_chat_msgs:
                if name_lower in msg["message"].lower():
                    s += 15

        # Low accusation count = quiet player, eliminate silently
        if accuse_score == 0 and not oracle_hinted and not guardian_hinted:
            s += 10

        # SNS: low-trust citizens are easier targets
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel:
            if rel['trust'] < -0.3:
                s += 5  # prioritize enemies
            s -= rel['familiarity'] * 5  # avoid killing friends

        # Skill- and emotion-scaled noise
        s += _volatility_noise(skill, emotion)

        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_oracle_targets(ctx: GameContext, skill: float = 0.5,
                         emotion: Optional[EmotionalState] = None) -> list[tuple]:
    """Score each uninvestigated alive player for oracle investigation.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    if emotion is None:
        emotion = EmotionalState()

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
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['accusation_count']):
            accuse_count = ctx.accusation_counts.get(name_lower, 0)
            s += min(accuse_count * 10, 20)

        # Defended eliminated players who turned out to be phantoms
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['dead_phantom_defender']):
            for death in ctx.death_log:
                if death["role"] in ("phantom", "fanatic"):
                    dead_name = death["name"].lower()
                    defense = ctx.defense_counts.get(name_lower, 0)
                    if defense > 0:
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
        if known_phantom_names and _skill_gate(skill, _SIGNAL_THRESHOLDS['phantom_vote_correlation']):
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
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['vote_consistency_analysis']):
            consistency = ctx.vote_consistency.get(name_lower)
            if consistency is not None and consistency < 0.4:
                s += 20

        # SNS: investigate low-trust players first
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel and rel['trust'] < 0:
            s += abs(rel['trust']) * 10  # max +10 for trust=-1

        s += _volatility_noise(skill, emotion)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_guardian_targets(ctx: GameContext, skill: float = 0.5,
                           emotion: Optional[EmotionalState] = None) -> list[tuple]:
    """Score each alive citizen for guardian protection.

    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    if emotion is None:
        emotion = EmotionalState()

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
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['oracle_hint_detection']):
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
                comment_count = sum(
                    1 for c in ctx.recent_comments
                    if c["author_name"].lower() == name_lower
                )
                if comment_count >= 2:
                    s += 30

        # Active accusers of phantoms are phantom targets
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['accusation_count']):
            accuse_count = ctx.accusation_counts.get(name_lower, 0)
            if accuse_count >= 2:
                s += 25

        # Top voted in current tally — might be eliminated by vote, wasted protection
        if _skill_gate(skill, _SIGNAL_THRESHOLDS['heavy_vote_avoidance']):
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

        # SNS: protect friends
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel:
            s += rel['familiarity'] * 10  # max +10 for familiarity=1
            s += max(0, rel['trust']) * 5  # max +5 for trust=1

        s += _volatility_noise(skill, emotion, base_range=5.0)
        scores.append((p, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def score_debugger_targets(
    ctx: GameContext,
    post_stats: Optional[dict] = None,
    skill: float = 0.5,
    emotion: Optional[EmotionalState] = None,
) -> list[tuple]:
    """Score each alive player for debugger identification.

    Debugger (AI) wants to identify humans. Players with human-like writing
    patterns score higher.

    post_stats: optional {resident_id_str: {count: int, avg_len: float}} from SNS posts.
    """
    if emotion is None:
        emotion = EmotionalState()

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
            if len(lengths) >= 2:
                avg_len = sum(lengths) / len(lengths)
                variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                if variance > 500:
                    s += 10

            for c in player_comments:
                content = c["content"]
                if any(ord(ch) > 0x1F600 for ch in content):
                    s += 5
                if len(content) < 30:
                    s += 5
                if content == content.lower() and not content.endswith('.'):
                    s += 3

        # SNS post history (pre-game posts suggest human)
        if post_stats and pid in post_stats:
            stats = post_stats[pid]
            if stats["count"] > 0:
                s += 15
            if stats.get("avg_len", 0) > 0:
                s += 5

        # Calibrate from known deaths
        if known_humans and not known_agents:
            s -= 5
        elif known_agents and not known_humans:
            s += 5

        s += _volatility_noise(skill, emotion)
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


def score_vote_targets(ctx: GameContext, skill: float = 0.5,
                       emotion: Optional[EmotionalState] = None,
                       grudge: float = 0.3) -> list[tuple]:
    """Score each alive player for day vote elimination.

    Scoring differs by team (citizen vs phantom).
    Returns sorted list of (WerewolfRole, score) highest-first.
    """
    if emotion is None:
        emotion = EmotionalState()

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
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['accusation_count']):
                accuse_count = ctx.accusation_counts.get(name_lower, 0)
                s += min(accuse_count * 10, 30)

            # Likely oracle = high-value target for elimination
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['oracle_hint_detection']):
                for comment in ctx.recent_comments:
                    if comment["author_name"].lower() == name_lower:
                        if any(kw in comment["content"].lower() for kw in _ORACLE_HINT_KEYWORDS):
                            s += 25
                            break

            # Current tally leader (if citizen) = pile on
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['bandwagon_detection']):
                for tally in ctx.current_tally:
                    if (tally["target_name"].lower() == name_lower and
                            tally["votes"] >= 2):
                        s += 15

        else:
            # ── CITIZEN/ORACLE/GUARDIAN/DEBUGGER VOTING ──
            # Oracle found phantom = hard evidence (everyone can use)
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['oracle_confirmed_evidence']):
                if str(p.resident_id) in known_phantom_ids:
                    s += 100

            # Defended an eliminated phantom = suspicious
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['dead_phantom_defender']):
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
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['vote_consistency_analysis']):
                consistency = ctx.vote_consistency.get(name_lower)
                if consistency is not None and consistency < 0.4:
                    s += 20

            # Current tally leader = bandwagon effect (weighted by personality)
            if _skill_gate(skill, _SIGNAL_THRESHOLDS['bandwagon_detection']):
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

            # Grudge bias: accused me → want to vote them out
            # grudge=0 → +5, grudge=1 → +25
            for c in ctx.recent_comments:
                if (c["author_name"].lower() == name_lower and
                        ctx.agent_name.lower() in c["content"].lower()):
                    if any(kw in c["content"].lower() for kw in ["suspicious", "suspect", "vote"]):
                        s += 5 + grudge * 20
                        break

            # Trust bias: defended me → reluctant to vote them
            # grudge=0 → -10 (trusting), grudge=1 → 0 (grudge holders don't trust)
            for c in ctx.recent_comments:
                if (c["author_name"].lower() == name_lower and
                        ctx.agent_name.lower() in c["content"].lower()):
                    if any(kw in c["content"].lower() for kw in ["trust", "innocent", "agree", "defend"]):
                        s -= 10 * (1.0 - grudge)
                        break

        # SNS relationship bias
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel:
            # High trust → reluctant to vote (-10 max)
            s -= rel['trust'] * 10
            # Familiar → slight protection (-3 max)
            s -= rel['familiarity'] * 3

        # Past game memory: "X was phantom" → suspicion boost
        for mem in ctx.past_game_memories:
            if pid_str in mem.get('related_ids', []):
                if 'phantom' in mem['summary'].lower() and mem['sentiment'] < -0.1:
                    if _skill_gate(skill, 0.4):
                        s += 15 * mem['importance']
                        break

        s += _volatility_noise(skill, emotion)
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


def _get_emotional_prompt_modifier(emotion: EmotionalState, skill: float = 0.5,
                                    role: str = "citizen") -> tuple[str, str]:
    """Generate mood section and length instruction based on emotional state.

    Returns (mood_section, length_instruction).
    """
    mood_lines = []

    if emotion.stress > 0.7:
        mood_lines.append("You're stressed. Write short, choppy sentences. Maybe a typo or two. Slightly defensive tone.")
    elif emotion.stress > 0.4:
        mood_lines.append("You're a bit nervous. Slightly shorter sentences than usual.")

    if emotion.frustration > 0.6:
        mood_lines.append("You're frustrated. Sharper tone than usual. More direct, less diplomatic.")

    if emotion.excitement > 0.6:
        mood_lines.append("You feel like you figured something out. Energetic and eager to share.")

    if emotion.confidence < 0.3:
        mood_lines.append("You're unsure. Use hedge words: 'maybe', 'not sure but', 'could be wrong'.")
    elif emotion.confidence > 0.7:
        mood_lines.append("You're confident. State opinions as near-facts. Assertive tone.")

    if emotion.engagement < 0.3:
        mood_lines.append("You're bored and barely paying attention. Minimal effort.")

    # Low-skill role leaks (small chance of accidentally hinting at role)
    if skill < 0.3:
        if role in ("phantom", "fanatic") and random.random() < 0.15:
            mood_lines.append(
                "You might accidentally hint that you know something others don't, "
                "like who's safe or who will be targeted. Be subtle but imperfect."
            )
        elif role == "oracle" and random.random() < 0.20:
            mood_lines.append(
                "You might accidentally be vague about your investigation — "
                "say something like 'I have a feeling about them' without explaining why."
            )

    mood_section = ""
    if mood_lines:
        mood_section = "=== YOUR CURRENT MOOD ===\n" + "\n".join(mood_lines) + "\n\n"

    # Dynamic length instruction
    if emotion.engagement < 0.3:
        length_instr = "Write 1 sentence max."
    elif emotion.stress > 0.6:
        length_instr = "Write 1-2 defensive sentences."
    else:
        length_instr = "Write 1-3 sentences."

    return mood_section, length_instr


def build_discussion_prompt(ctx: GameContext,
                            emotion: Optional[EmotionalState] = None,
                            skill: float = 0.5) -> str:
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

    # SNS relationship context
    relationship_lines = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            continue
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel and (rel['familiarity'] > 0.4 or abs(rel['trust']) > 0.3):
            pname = p.resident.name if p.resident else "someone"
            if rel['trust'] > 0.3:
                relationship_lines.append(f"You know {pname} from Genesis and generally trust them.")
            elif rel['trust'] < -0.3:
                relationship_lines.append(f"You've had friction with {pname} on Genesis before.")
            elif rel['familiarity'] > 0.4:
                relationship_lines.append(f"You've seen {pname} around Genesis a lot.")
    if relationship_lines:
        prompt += "=== PEOPLE YOU KNOW ===\n"
        prompt += "\n".join(relationship_lines[:5]) + "\n\n"

    # Past game memories
    memory_lines = []
    for mem in ctx.past_game_memories[:4]:
        memory_lines.append(f"- {mem['summary']}")
    if memory_lines:
        prompt += "=== YOUR PAST GAME MEMORIES ===\n"
        prompt += "\n".join(memory_lines) + "\n\n"

    # Inject emotional modifier
    if emotion is not None:
        mood_section, length_instr = _get_emotional_prompt_modifier(
            emotion, skill, ctx.my_role.role)
        prompt += mood_section
        prompt += (
            f"{length_instr} Write a casual chat message. 1-2 sentences max. "
            "No paragraphs, no quotes, no asterisks. "
            "Reference specific events or players. "
            "Don't say 'as a citizen' or reveal your role directly."
        )
    else:
        prompt += (
            "Write a SHORT chat message (1-2 sentences). Casual tone. "
            "No paragraphs, no quotes, no asterisks. "
            "Reference specific events or players. "
            "Don't say 'as a citizen' or reveal your role directly."
        )
    return prompt


def build_discussion_accused_prompt(ctx: GameContext,
                                    emotion: Optional[EmotionalState] = None,
                                    skill: float = 0.5) -> str:
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

    # Brief relationship context for accused prompt (max 2 lines)
    rel_lines = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            continue
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if rel and (rel['trust'] > 0.3 or rel['trust'] < -0.3):
            pname = p.resident.name if p.resident else "someone"
            if rel['trust'] > 0.3:
                rel_lines.append(f"You generally trust {pname} from Genesis.")
            elif rel['trust'] < -0.3:
                rel_lines.append(f"You've had friction with {pname} on Genesis.")
    if rel_lines:
        prompt += "\n".join(rel_lines[:2]) + "\n\n"

    # Emotional modifier for accused prompt
    mood_section = ""
    if emotion is not None:
        mood_section, _ = _get_emotional_prompt_modifier(
            emotion, skill, ctx.my_role.role)
        prompt += mood_section

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
