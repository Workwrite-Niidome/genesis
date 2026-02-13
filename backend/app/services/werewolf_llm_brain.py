"""
Phantom Night — LLM Thinking Engine

Multi-step LLM reasoning engine where smarter agents think more deeply.
Replaces algorithmic scoring with autonomous LLM decision-making.

Skill Tiers (based on agent's skill_level trait):
- S (0.80+):  assess → analyze → strategize → decide → check → reflect  (6 steps)
- A (0.55+):  assess → analyze → strategize → decide → reflect           (5 steps)
- B (0.30+):  assess → analyze → decide                                   (3 steps)
- C (<0.30):  assess → decide                                             (2 steps)

Thoughts are cached in WerewolfGameEvent so they persist across 60s Celery cycles.
Only thinking steps (assess/analyze/strategize) are cached; action decisions are fresh.
"""
import json
import logging
import re
from typing import Optional

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.werewolf_game import WerewolfGameEvent, WerewolfGame, WerewolfRole
from app.services.werewolf_strategy import GameContext, EmotionalState

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# SKILL TIER CONFIG
# ═══════════════════════════════════════════════════════════════════════════

SKILL_TIERS = {
    'S': {
        'min_skill': 0.80,
        'steps': ['assess', 'analyze', 'strategize', 'decide', 'check', 'reflect'],
        'temperature': 0.4, 'top_p': 0.85,
        'comment_limit': 12, 'history_rounds': 'all',
        'sns_context': True, 'memory_count': 4,
    },
    'A': {
        'min_skill': 0.55,
        'steps': ['assess', 'analyze', 'strategize', 'decide', 'reflect'],
        'temperature': 0.5, 'top_p': 0.88,
        'comment_limit': 12, 'history_rounds': 'all',
        'sns_context': True, 'memory_count': 3,
    },
    'B': {
        'min_skill': 0.30,
        'steps': ['assess', 'analyze', 'decide'],
        'temperature': 0.7, 'top_p': 0.90,
        'comment_limit': 8, 'history_rounds': 2,
        'sns_context': True, 'memory_count': 1,
    },
    'C': {
        'min_skill': 0.0,
        'steps': ['assess', 'decide'],
        'temperature': 0.9, 'top_p': 0.95,
        'comment_limit': 5, 'history_rounds': 1,
        'sns_context': True, 'memory_count': 0,
    },
}


def get_skill_tier(skill_level: float) -> str:
    if skill_level >= 0.80:
        return 'S'
    elif skill_level >= 0.55:
        return 'A'
    elif skill_level >= 0.30:
        return 'B'
    return 'C'


def get_tier_config(skill_level: float) -> dict:
    return SKILL_TIERS[get_skill_tier(skill_level)]


# ═══════════════════════════════════════════════════════════════════════════
# LLM INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

async def _call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> Optional[str]:
    """Call Ollama with configurable temperature/top_p."""
    s = get_settings()
    ollama_host = s.OLLAMA_HOST or "https://ollama.genesis-pj.net"
    model = s.OLLAMA_MODEL or "llama3.1:8b"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "repeat_penalty": 1.15,
                    },
                },
            )
            if response.status_code == 200:
                text = response.json().get("response", "").strip()
                for phrase in [
                    "As an AI", "I'm an AI", "as a language model",
                    "I don't have personal", "as an artificial",
                ]:
                    text = text.replace(phrase, "")
                return text.strip()
            else:
                logger.warning(f"LLM Brain: Ollama {response.status_code}: {response.text[:200]}")
    except Exception as e:
        logger.error(f"LLM Brain: Ollama error: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# THOUGHT CACHE — persist thinking across Celery cycles via WerewolfGameEvent
# ═══════════════════════════════════════════════════════════════════════════

async def get_cached_thoughts(
    db: AsyncSession, game: WerewolfGame, agent_id
) -> dict:
    """Load cached thinking steps for current round/phase."""
    result = await db.execute(
        select(WerewolfGameEvent).where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.round_number == game.current_round,
                WerewolfGameEvent.phase == (game.current_phase or "day"),
                WerewolfGameEvent.event_type.like("agent_thought_%"),
                WerewolfGameEvent.target_id == agent_id,
            )
        )
    )
    thoughts = {}
    for ev in result.scalars().all():
        step = ev.event_type.replace("agent_thought_", "")
        thoughts[step] = ev.message
    return thoughts


async def save_thought(
    db: AsyncSession, game: WerewolfGame, agent_id, step: str, content: str
):
    """Persist a thinking step as a game event."""
    event = WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase=game.current_phase or "day",
        event_type=f"agent_thought_{step}",
        message=content[:2000],
        target_id=agent_id,
    )
    db.add(event)


# ═══════════════════════════════════════════════════════════════════════════
# GAME STATE FORMATTERS
# ═══════════════════════════════════════════════════════════════════════════

def format_alive_players(ctx: GameContext) -> str:
    lines = []
    for p in ctx.alive_players:
        name = p.resident.name if p.resident else "?"
        marker = " (YOU)" if p.resident_id == ctx.agent_id else ""
        lines.append(f"- {name}{marker}")
    return f"Alive players ({len(ctx.alive_players)}):\n" + "\n".join(lines)


def format_event_log(ctx: GameContext, limit: int = 20) -> str:
    if not ctx.all_events:
        return ""
    events = ctx.all_events[-limit:]
    lines = []
    for ev in events:
        lines.append(f"[R{ev.round_number} {ev.phase}] {ev.message}")
    return "Event Log:\n" + "\n".join(lines)


def format_death_log(ctx: GameContext) -> str:
    if not ctx.death_log:
        return "No one has been eliminated yet."
    lines = []
    for d in ctx.death_log:
        role_str = f" (revealed: {d['role']})" if d.get('role') else ""
        lines.append(f"- Round {d['round']}: {d['name']} eliminated by {d['cause']}{role_str}")
    return "Eliminations:\n" + "\n".join(lines)


def format_vote_history(ctx: GameContext, rounds='all') -> str:
    if not ctx.vote_history:
        return "No vote history yet."
    items = sorted(ctx.vote_history.items())
    if isinstance(rounds, int):
        items = items[-rounds:]
    lines = []
    for rnd, votes in items:
        targets = {}
        for v in votes:
            tn = v['target_name']
            targets[tn] = targets.get(tn, 0) + 1
        vote_str = ", ".join(
            f"{name}: {count}" for name, count in
            sorted(targets.items(), key=lambda x: -x[1])
        )
        lines.append(f"Round {rnd}: {vote_str}")
    return "Vote History:\n" + "\n".join(lines)


def format_tally(ctx: GameContext) -> str:
    if not ctx.current_tally:
        return "No votes cast yet this round."
    lines = []
    for t in ctx.current_tally:
        lines.append(f"- {t['target_name']}: {t['votes']} votes")
    return "Current Vote Tally:\n" + "\n".join(lines)


def format_comments(ctx: GameContext, limit: int = 12) -> str:
    if not ctx.recent_comments:
        return "No discussion yet."
    comments = ctx.recent_comments[-limit:]
    lines = []
    for c in comments:
        lines.append(f"{c['author_name']}: {c['content'][:200]}")
    return "Recent Discussion:\n" + "\n".join(lines)


def format_role_knowledge(ctx: GameContext) -> str:
    role = ctx.my_role
    parts = [f"Your role: {role.role.upper()} (Team: {role.team})"]

    if role.role == "phantom":
        teammates = [p.resident.name for p in ctx.alive_phantoms
                     if p.resident_id != ctx.agent_id and p.resident]
        if teammates:
            parts.append(f"Phantom teammates: {', '.join(teammates)}")
        parts.append("You attack one person each night to eliminate them.")

    elif role.role == "oracle":
        if ctx.investigation_results:
            for inv in ctx.investigation_results:
                r = "PHANTOM" if inv.get('result') == 'phantom' else "NOT phantom"
                parts.append(f"Investigated: {inv.get('target_name', '?')} = {r}")
        parts.append("You investigate one person each night.")

    elif role.role == "guardian":
        parts.append("You protect one person each night from Phantom attacks.")
        if ctx.night_actions_mine:
            last = ctx.night_actions_mine[-1]
            if last.target_id:
                # Find name from alive players
                for p in ctx.alive_players:
                    if p.resident_id == last.target_id and p.resident:
                        parts.append(f"Last protected: {p.resident.name}")
                        break

    elif role.role == "fanatic":
        teammates = [p.resident.name for p in ctx.alive_phantoms
                     if p.resident_id != ctx.agent_id and p.resident]
        if teammates:
            parts.append(f"Phantom allies: {', '.join(teammates)}")
        parts.append("You appear as Citizen to Oracle. Help Phantoms win from within.")

    elif role.role == "debugger":
        parts.append("Target a human → they die. Target an AI like you → YOU die.")

    elif role.role == "citizen":
        parts.append("No special ability. Find Phantoms through discussion and voting.")

    return "\n".join(parts)


def format_sns_context(ctx: GameContext) -> str:
    lines = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            continue
        pid_str = str(p.resident_id)
        rel = ctx.sns_relationships.get(pid_str)
        if not rel:
            continue
        if rel['familiarity'] <= 0.3 and abs(rel['trust']) <= 0.2:
            continue
        name = p.resident.name if p.resident else "?"
        if rel['trust'] > 0.3:
            trust_lbl = "you trust them"
        elif rel['trust'] < -0.3:
            trust_lbl = "you distrust them"
        else:
            trust_lbl = "neutral"
        fam_lbl = "close" if rel['familiarity'] > 0.6 else "familiar"
        lines.append(f"- {name}: {fam_lbl}, {trust_lbl}")
    if not lines:
        return ""
    return "People you know from Genesis SNS:\n" + "\n".join(lines)


def format_memories(ctx: GameContext, limit: int = 4) -> str:
    if not ctx.past_game_memories:
        return ""
    lines = [f"- {m['summary']}" for m in ctx.past_game_memories[:limit]]
    return "Your past game memories:\n" + "\n".join(lines)


def build_game_state_text(ctx: GameContext, tier_config: dict) -> str:
    """Combine all formatters into a single game state text block."""
    parts = [
        f"Game #{ctx.game.game_number}, Round {ctx.game.current_round}, "
        f"Phase: {ctx.game.current_phase or 'day'}",
    ]
    parts.append(format_alive_players(ctx))
    parts.append(format_role_knowledge(ctx))
    parts.append(format_death_log(ctx))

    rounds = tier_config.get('history_rounds', 'all')
    parts.append(format_vote_history(ctx, rounds))

    if ctx.game.current_phase == "day":
        parts.append(format_tally(ctx))

    comment_limit = tier_config.get('comment_limit', 8)
    parts.append(format_comments(ctx, comment_limit))

    if tier_config.get('sns_context'):
        sns = format_sns_context(ctx)
        if sns:
            parts.append(sns)

    memory_count = tier_config.get('memory_count', 0)
    if memory_count > 0:
        mems = format_memories(ctx, memory_count)
        if mems:
            parts.append(mems)

    return "\n\n".join(p for p in parts if p)


# ═══════════════════════════════════════════════════════════════════════════
# EMOTIONAL STATE → TEXT
# ═══════════════════════════════════════════════════════════════════════════

def get_mood_instruction(emotion: EmotionalState) -> str:
    parts = []
    if emotion.stress > 0.5:
        parts.append("You're feeling stressed and defensive right now.")
    elif emotion.stress > 0.2:
        parts.append("You're a bit tense.")
    if emotion.frustration > 0.4:
        parts.append("You're frustrated — maybe a grudge is building.")
    if emotion.excitement > 0.5:
        parts.append("You're excited — something important is happening.")
    if emotion.confidence > 0.7:
        parts.append("You feel confident about the situation.")
    elif emotion.confidence < 0.3:
        parts.append("You're uncertain and second-guessing yourself.")
    if emotion.engagement < 0.4:
        parts.append("You're getting bored and disengaged.")
    if not parts:
        return ""
    return "Current mood: " + " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# THINKING PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

def _thinking_context(cached: dict) -> str:
    """Build context string from previously completed thinking steps."""
    labels = {
        'assess': 'Situation Assessment',
        'analyze': 'Behavioral Analysis',
        'strategize': 'Strategic Plan',
    }
    parts = []
    for step in ('assess', 'analyze', 'strategize'):
        if step in cached:
            parts.append(f"[{labels[step]}]\n{cached[step]}")
    if not parts:
        return ""
    return "=== YOUR THINKING SO FAR ===\n" + "\n\n".join(parts)


def build_assess_prompt(ctx: GameContext, tier_config: dict) -> str:
    state = build_game_state_text(ctx, tier_config)
    return (
        f"You are {ctx.agent_name} playing Phantom Night (a werewolf-style social deduction game).\n"
        f"Assess the current game situation in 3-5 sentences.\n"
        f"Focus on: threat level for your team, who seems suspicious or trustworthy, "
        f"key dynamics from recent events and discussion.\n\n"
        f"{state}"
    )


def build_analyze_prompt(ctx: GameContext, tier_config: dict, cached: dict) -> str:
    tc = _thinking_context(cached)
    comment_limit = tier_config.get('comment_limit', 8)
    comments = format_comments(ctx, comment_limit)
    votes = format_vote_history(ctx, tier_config.get('history_rounds', 'all'))
    return (
        f"Based on your situation assessment, analyze each alive player's behavior.\n"
        f"Look at: voting patterns, discussion tone, inconsistencies, silence.\n"
        f"For each suspicious or notable player, explain WHY in 1-2 sentences.\n\n"
        f"{tc}\n\n"
        f"{comments}\n\n"
        f"{votes}"
    )


def build_strategize_prompt(ctx: GameContext, tier_config: dict, cached: dict) -> str:
    tc = _thinking_context(cached)
    role_info = format_role_knowledge(ctx)
    return (
        f"Based on your analysis, outline your strategy for this phase.\n"
        f"Be specific: who to target/protect/suspect, what to say or avoid saying, "
        f"how to help your team win.\n\n"
        f"{tc}\n\n"
        f"{role_info}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# ACTION PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

def build_vote_action_prompt(
    ctx: GameContext, tier_config: dict, cached: dict, emotion: EmotionalState
) -> str:
    tc = _thinking_context(cached)
    state = build_game_state_text(ctx, tier_config)
    mood = get_mood_instruction(emotion)
    valid = get_valid_target_names(ctx, "vote")
    names_str = ", ".join(valid)

    prompt = f"{state}\n\n"
    if tc:
        prompt += f"{tc}\n\n"
    if mood:
        prompt += f"{mood}\n\n"
    prompt += (
        f"You are {ctx.agent_name}. Choose who to vote to eliminate.\n"
        f"You CANNOT vote for yourself.\n\n"
        f"Valid targets: {names_str}\n\n"
        f"Reply with ONLY a JSON object like this:\n"
        f'{{"target": "player_name", "reason": "1-sentence reason"}}'
    )
    return prompt


def build_night_action_prompt(
    ctx: GameContext, tier_config: dict, cached: dict, emotion: EmotionalState
) -> str:
    tc = _thinking_context(cached)
    state = build_game_state_text(ctx, tier_config)
    valid = get_valid_target_names(ctx, "night")
    names_str = ", ".join(valid)
    role = ctx.my_role.role

    role_instructions = {
        "phantom": (
            "As a Phantom, choose who to attack tonight.\n"
            "Pick someone who won't be protected and whose death hurts Citizens most."
        ),
        "oracle": (
            "As the Oracle, choose who to investigate tonight.\n"
            "Pick someone you're uncertain about — confirming a Phantom is very valuable."
        ),
        "guardian": (
            "As the Guardian, choose who to protect tonight.\n"
            "Think about who the Phantoms are most likely to target."
        ),
        "debugger": (
            "As the Debugger, choose who to identify tonight.\n"
            "You're an AI — targeting another AI kills YOU. Target humans to eliminate them.\n"
            "Look for human writing patterns in the discussion."
        ),
    }
    instruction = role_instructions.get(role, "Choose your target for tonight.")

    prompt = f"{state}\n\n"
    if tc:
        prompt += f"{tc}\n\n"
    prompt += (
        f"{instruction}\n\n"
        f"Valid targets: {names_str}\n\n"
        f"Reply with ONLY a JSON object like this:\n"
        f'{{"target": "player_name"}}'
    )
    return prompt


def build_discuss_action_prompt(
    ctx: GameContext, tier_config: dict, cached: dict, emotion: EmotionalState,
    accused: bool = False, **kwargs
) -> str:
    tc = _thinking_context(cached)
    state = build_game_state_text(ctx, tier_config)
    mood = get_mood_instruction(emotion)
    lang = kwargs.get('lang', 'en')

    accused_context = ""
    if accused:
        # Find the accusation in recent comments
        for c in reversed(ctx.recent_comments):
            if c['author_name'].lower() != ctx.agent_name.lower():
                if ctx.agent_name.lower() in c['content'].lower():
                    accused_context = (
                        f"URGENT: {c['author_name']} just accused you: \"{c['content'][:200]}\"\n"
                        f"You need to defend yourself convincingly without overreacting.\n"
                    )
                    break

    team_goal = (
        "help Phantoms win by deflecting suspicion from your team"
        if ctx.my_role.team == "phantoms"
        else "find and eliminate Phantoms through discussion"
    )

    prompt = f"{state}\n\n"
    if tc:
        prompt += f"{tc}\n\n"
    if accused_context:
        prompt += f"{accused_context}\n"
    if mood:
        prompt += f"{mood}\n\n"
    prompt += (
        f"Write a chat message as {ctx.agent_name}.\n"
        f"Your goal: {team_goal}.\n"
        f"Be natural and casual. 1-2 sentences max. Like a group chat message.\n"
        f"No paragraphs, no quotes, no asterisks, no formatting.\n\n"
    )
    if lang == "ja":
        prompt += "日本語で書いてください。自然なネット日本語で。\n\n"
    prompt += "Write ONLY your message. No JSON, no quotes."
    return prompt


def build_phantom_chat_action_prompt(
    ctx: GameContext, tier_config: dict, cached: dict, emotion: EmotionalState,
    **kwargs
) -> str:
    tc = _thinking_context(cached)
    lang = kwargs.get('lang', 'en')

    chat_lines = []
    for msg in ctx.phantom_chat_msgs[-8:]:
        chat_lines.append(f"{msg['sender_name']}: {msg['message'][:200]}")
    chat_text = "\n".join(chat_lines) if chat_lines else "No messages yet."

    teammates = [p.resident.name for p in ctx.alive_phantoms
                 if p.resident_id != ctx.agent_id and p.resident]
    teammate_str = ", ".join(teammates) if teammates else "none alive"

    prompt = ""
    if tc:
        prompt += f"{tc}\n\n"
    prompt += (
        f"Secret Phantom Chat (teammates: {teammate_str}):\n"
        f"{chat_text}\n\n"
        f"Send a strategic message to your teammates.\n"
        f"Coordinate: who to target tonight, how to deflect suspicion, cover stories.\n\n"
    )
    if lang == "ja":
        prompt += "日本語で書いてください。\n\n"
    prompt += "Write ONLY your message. Brief and strategic."
    return prompt


def build_reconsider_prompt(ctx: GameContext, cached: dict, **kwargs) -> str:
    tc = _thinking_context(cached)
    tally = format_tally(ctx)
    leader_name = kwargs.get('leader_name', '?')
    leader_votes = kwargs.get('leader_votes', 0)
    current_target = kwargs.get('current_target', '?')
    valid = get_valid_target_names(ctx, "reconsider")
    names_str = ", ".join(valid)

    prompt = ""
    if tc:
        prompt += f"{tc}\n\n"
    prompt += (
        f"{tally}\n\n"
        f"The vote tally has shifted. Current leader: {leader_name} ({leader_votes} votes).\n"
        f"Your current vote: {current_target}.\n\n"
        f"Should you change your vote to follow the majority or keep your conviction?\n"
        f"Consider whether the leader actually deserves elimination.\n\n"
        f"Valid targets: {names_str}\n\n"
        f"If changing vote, reply: {{\"target\": \"name\", \"reason\": \"reason\"}}\n"
        f"If keeping vote, reply: {{\"keep\": true}}"
    )
    return prompt


# ═══════════════════════════════════════════════════════════════════════════
# CONSISTENCY CHECK & REFLECTION
# ═══════════════════════════════════════════════════════════════════════════

def build_consistency_check_prompt(decision: dict, cached: dict, action: str) -> str:
    tc = _thinking_context(cached)
    target = decision.get('target', '?')
    reason = decision.get('reason', '')
    return (
        f"Review your decision before finalizing.\n\n"
        f"{tc}\n\n"
        f"Your decision: {action} → {target}"
        f"{f' (reason: {reason})' if reason else ''}\n\n"
        f"Does this align with your role and strategy?\n"
        f"Could this expose you or harm your team?\n"
        f"If the decision is good, say 'confirmed'.\n"
        f"If you want to change, reply with: {{\"target\": \"new_name\", \"reason\": \"why\"}}"
    )


def build_reflect_prompt(decision: dict, cached: dict, action: str) -> str:
    tc = _thinking_context(cached)
    target = decision.get('target', decision.get('text', '?')[:50])
    return (
        f"After your {action} ({target}), briefly reflect.\n\n"
        f"{tc}\n\n"
        f"What did you learn? What should you remember for future decisions?\n"
        f"2-3 sentences."
    )


# ═══════════════════════════════════════════════════════════════════════════
# DECISION PARSING
# ═══════════════════════════════════════════════════════════════════════════

def fuzzy_match_name(name_input: str, valid_names: list) -> Optional[str]:
    """Match a possibly misspelled name to the closest valid name."""
    if not name_input:
        return None
    name_lower = name_input.strip().lower()

    # Exact match
    for name in valid_names:
        if name.lower() == name_lower:
            return name

    # Partial match (input contained in name or vice versa)
    for name in valid_names:
        if name_lower in name.lower() or name.lower() in name_lower:
            return name

    # First-word match
    input_first = name_lower.split()[0] if name_lower.split() else ""
    if input_first:
        for name in valid_names:
            name_first = name.lower().split()[0] if name.split() else ""
            if input_first == name_first and len(input_first) >= 3:
                return name

    return None


def parse_decision(text: str, valid_names: list, action: str) -> Optional[dict]:
    """Parse LLM output into a structured decision with fallback strategies."""
    if not text:
        return None

    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Extract JSON from markdown code block
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: Find JSON-like pattern in text
    m = re.search(r'\{[^{}]*"target"[^{}]*\}', text)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: Find any JSON object
    m = re.search(r'\{[^{}]+\}', text)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 5: Extract name from text (for target-based actions)
    if action in ("vote", "night", "reconsider"):
        for name in valid_names:
            if name.lower() in text.lower():
                if action == "vote":
                    return {"target": name, "reason": text[:200]}
                return {"target": name}

    return None


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_valid_target_names(ctx: GameContext, action: str) -> list:
    """Get list of valid target names for a given action."""
    names = []
    for p in ctx.alive_players:
        if p.resident_id == ctx.agent_id:
            continue
        name = p.resident.name if p.resident else None
        if not name:
            continue
        # Phantoms don't attack teammates
        if action == "night" and ctx.my_role.role == "phantom" and p.team == "phantoms":
            continue
        names.append(name)
    return names


def find_player_by_name(ctx: GameContext, name: str) -> Optional[WerewolfRole]:
    """Find a WerewolfRole by player name (case-insensitive)."""
    if not name:
        return None
    name_lower = name.lower()
    for p in ctx.alive_players:
        if p.resident and p.resident.name.lower() == name_lower:
            return p
    # Fuzzy fallback
    valid_names = [p.resident.name for p in ctx.alive_players if p.resident]
    matched = fuzzy_match_name(name, valid_names)
    if matched:
        for p in ctx.alive_players:
            if p.resident and p.resident.name == matched:
                return p
    return None


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

async def think_and_act(
    db: AsyncSession,
    agent,
    game: WerewolfGame,
    role: WerewolfRole,
    profile: dict,
    action: str,
    ctx: GameContext = None,
    emotion: EmotionalState = None,
    system_prompt: str = "",
    **kwargs,
) -> Optional[dict]:
    """
    Main orchestrator: run thinking steps, then decide and act.

    Args:
        action: "vote", "night", "discuss", "discuss_accused",
                "phantom_chat", "reconsider"
    Returns:
        {"target": str, "reason": str} for vote/reconsider/night
        {"text": str} for discuss/phantom_chat
        None on failure
    """
    traits = profile.get('traits', {})
    skill = traits.get('skill_level', 0.5)
    tier_config = get_tier_config(skill)
    tier = get_skill_tier(skill)
    steps = tier_config['steps']
    temperature = tier_config['temperature']
    top_p = tier_config['top_p']

    # Build context if not provided
    if ctx is None:
        from app.services.werewolf_strategy import build_game_context
        ctx = await build_game_context(db, agent, game, role, profile)
    if emotion is None:
        from app.services.werewolf_strategy import compute_emotional_state
        emotion = compute_emotional_state(ctx, traits)

    # System prompt from caller (personality-aware)
    sys_prompt = system_prompt

    # Load cached thoughts for this round/phase
    cached = await get_cached_thoughts(db, game, agent.id)

    # ── Run thinking steps not yet cached ──
    thinking_steps = [s for s in steps if s in ('assess', 'analyze', 'strategize')]
    for step in thinking_steps:
        if step in cached:
            continue
        if step == 'assess':
            prompt = build_assess_prompt(ctx, tier_config)
        elif step == 'analyze':
            prompt = build_analyze_prompt(ctx, tier_config, cached)
        elif step == 'strategize':
            prompt = build_strategize_prompt(ctx, tier_config, cached)
        else:
            continue

        result = await _call_llm(prompt, sys_prompt, temperature, top_p)
        if result:
            cached[step] = result
            await save_thought(db, game, agent.id, step, result)
            logger.debug(f"LLM Brain [{tier}]: {agent.name} completed {step}")
        else:
            logger.warning(f"LLM Brain [{tier}]: {agent.name} {step} returned None")

    # ── Build action prompt ──
    if action == "vote":
        action_prompt = build_vote_action_prompt(ctx, tier_config, cached, emotion)
    elif action == "night":
        action_prompt = build_night_action_prompt(ctx, tier_config, cached, emotion)
    elif action in ("discuss", "discuss_accused"):
        action_prompt = build_discuss_action_prompt(
            ctx, tier_config, cached, emotion,
            accused=(action == "discuss_accused"), **kwargs
        )
    elif action == "phantom_chat":
        action_prompt = build_phantom_chat_action_prompt(ctx, tier_config, cached, emotion, **kwargs)
    elif action == "reconsider":
        action_prompt = build_reconsider_prompt(ctx, cached, **kwargs)
    else:
        logger.error(f"LLM Brain: unknown action '{action}'")
        return None

    # ── Call LLM for decision ──
    decision_text = await _call_llm(action_prompt, sys_prompt, temperature, top_p)
    if not decision_text:
        logger.warning(f"LLM Brain [{tier}]: {agent.name} action={action} LLM returned None")
        return None

    # ── Text-based actions: return directly ──
    if action in ("discuss", "discuss_accused", "phantom_chat"):
        text = decision_text.strip()
        # Strip quotes if LLM wrapped the output
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        # Strip markdown formatting artifacts
        if text.startswith("```") and text.endswith("```"):
            text = text.strip("`").strip()
        return {"text": text} if len(text) >= 3 else None

    # ── Structured decisions: parse target ──
    valid_names = get_valid_target_names(ctx, action)
    decision = parse_decision(decision_text, valid_names, action)

    # Check for "keep" in reconsider
    if action == "reconsider" and decision and decision.get('keep'):
        return {"keep": True}

    if not decision or 'target' not in decision:
        logger.warning(
            f"LLM Brain [{tier}]: {agent.name} no valid decision. "
            f"action={action}, text={decision_text[:100]}"
        )
        return None

    # Fuzzy-match the target name
    matched = fuzzy_match_name(decision['target'], valid_names)
    if matched:
        decision['target'] = matched
    else:
        # Last resort: scan full text for any valid name
        for name in valid_names:
            if name.lower() in decision_text.lower():
                decision['target'] = name
                break
        else:
            logger.warning(
                f"LLM Brain [{tier}]: {agent.name} unmatched target "
                f"'{decision.get('target')}' in {valid_names}"
            )
            return None

    # ── Consistency check (S tier) ──
    if 'check' in steps and action in ('vote', 'night'):
        check_prompt = build_consistency_check_prompt(decision, cached, action)
        check_text = await _call_llm(check_prompt, sys_prompt, temperature, top_p)
        if check_text and 'confirmed' not in check_text.lower():
            alt = parse_decision(check_text, valid_names, action)
            if alt and 'target' in alt:
                alt_matched = fuzzy_match_name(alt['target'], valid_names)
                if alt_matched and alt_matched != decision.get('target'):
                    logger.info(
                        f"LLM Brain [S]: {agent.name} check override "
                        f"{decision['target']} → {alt_matched}"
                    )
                    decision['target'] = alt_matched
                    if alt.get('reason'):
                        decision['reason'] = alt['reason']

    # ── Reflection (S + A tiers) ──
    if 'reflect' in steps:
        reflect_prompt = build_reflect_prompt(decision, cached, action)
        reflect_text = await _call_llm(
            reflect_prompt, sys_prompt, min(temperature * 1.1, 1.0), top_p
        )
        if reflect_text:
            await save_thought(db, game, agent.id, 'reflect', reflect_text)
            logger.debug(f"LLM Brain [{tier}]: {agent.name} reflection saved")

    return decision
