"""GENESIS v3 Artifact Engine -- artifacts stored as WorldEvent entries.

Interaction types: art, song, tool/code, architecture, story/law,
prophecy, manifesto, language. Each processed mechanically (no LLM).
"""

import logging
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.world import WorldEvent
from app.agents.memory import MemoryManager

logger = logging.getLogger(__name__)
memory_manager = MemoryManager()

ARTIFACT_INTERACTION_RADIUS = 60.0
ARTIFACT_COOLDOWN_TICKS = 20

# ── Tool Effect Classification ─────────────────────────────────

TOOL_EFFECT_PATTERNS = {
    r"move|speed|travel|explore|wing|leg|vehicle":    {"move_range_bonus": 5.0},
    r"create|craft|build|forge|amplif":               {"creation_discount": 0.03},
    r"sense|detect|see|aware|radar|scan|eye|percep":  {"awareness_bonus": 20.0},
    r"energy|harvest|recharge|sustain|heal|regen":    {"energy_regen": 0.02},
    r"shield|protect|armor|barrier|resist|endur":     {"death_threshold": 5},
    r"communi|speak|translate|connect|signal|bridge": {"interaction_bonus": 1.0},
}
DEFAULT_TOOL_EFFECT = {"energy_regen": 0.01}
TOOL_EFFECT_CAPS = {
    "move_range_bonus": 15.0, "creation_discount": 0.10,
    "awareness_bonus": 40.0, "energy_regen": 0.05,
    "death_threshold": 10, "interaction_bonus": 3.0,
}


def classify_tool_effect(description: str) -> dict:
    """Classify a tool's effect based on description keywords."""
    if not description:
        return dict(DEFAULT_TOOL_EFFECT)
    dl = description.lower()
    fx: dict = {}
    for pat, eff in TOOL_EFFECT_PATTERNS.items():
        if re.search(pat, dl):
            for k, v in eff.items():
                fx[k] = fx.get(k, 0) + v
    return fx if fx else dict(DEFAULT_TOOL_EFFECT)


def aggregate_tool_effects(tool_data_list: list[dict]) -> dict:
    """Aggregate effects from multiple tool artifact data dicts, with caps."""
    agg: dict = {}
    for d in tool_data_list:
        fe = d.get("functional_effects")
        if fe and isinstance(fe, dict):
            if (d.get("durability") or 1) <= 0: continue
            eff = {k: v for k, v in fe.items() if isinstance(v, (int, float))}
        else:
            eff = classify_tool_effect(d.get("description", "") or "")
        for k, v in eff.items():
            agg[k] = agg.get(k, 0) + v
    for k, cap in TOOL_EFFECT_CAPS.items():
        if k in agg: agg[k] = min(cap, agg[k])
    return agg


def set_emotion(entity: Entity, emotion: str, intensity: float,
                source: str, tick: int) -> None:
    """Set emotional state; only overwrites if new intensity is higher."""
    state = dict(entity.state)
    cur = state.get("emotional_state")
    if cur and isinstance(cur, dict) and cur.get("intensity", 0) >= intensity:
        return
    state["emotional_state"] = {
        "emotion": emotion, "intensity": round(intensity, 2),
        "source": source, "tick_set": tick,
    }
    entity.state = state


def _d(evt: WorldEvent) -> dict:
    return evt.params or {}


# ── Rich Artifact Content for Entity Cognition ────────────────

def get_artifact_content_text(event: WorldEvent) -> str:
    """Extract readable content from an artifact WorldEvent for cognition."""
    data = _d(event)
    content = data.get("content", {}) or {}
    desc = data.get("description", "") or ""
    at = data.get("artifact_type", "")
    if at == "story":
        t = content.get("text", ""); return t[:500] if t else desc[:300]
    if at == "law":
        rules = content.get("rules", content.get("provisions", content.get("articles", [])))
        if isinstance(rules, list) and rules:
            return "\n".join(f"  {i+1}. {str(r)[:120]}" for i, r in enumerate(rules[:7]))
        return desc[:300]
    if at == "song":
        p: list[str] = []
        if desc: p.append(desc[:200])
        t = content.get("text", "")
        if t: p.append(f'Lyrics: "{t[:200]}"')
        for k in ("mood", "tempo"):
            v = content.get(k, "")
            if v: p.append(f"{k.title()}: {v}")
        return "\n  ".join(p) if p else desc[:200]
    if at in ("tool", "code"):
        p = [desc[:200]] if desc else []
        s = content.get("source", "")
        if s: p.append(f"Code:\n  ```\n  {s[:300]}\n  ```")
        p.append(f"[Effects: {', '.join(f'{k}:+{v}' for k,v in classify_tool_effect(desc).items())}]")
        return "\n  ".join(p)
    if at == "architecture":
        p = [desc[:200]] if desc else []
        vx = content.get("voxels", [])
        if vx: p.append(f"({len(vx)} blocks)")
        pal = content.get("palette", [])
        if pal: p.append(f"Colors: {', '.join(str(c) for c in pal[:5])}")
        p.append("[Shelter: 2x energy recovery]"); return "\n  ".join(p)
    if at == "art":
        p = [desc[:250]] if desc else []
        pal = content.get("palette", [])
        if pal: p.append(f"Palette: {', '.join(str(c) for c in pal[:6])}")
        px = content.get("pixels", [])
        if px: p.append(f"({len(px)}px canvas)")
        return "\n  ".join(p)
    if at == "prophecy":
        pred = content.get("prediction", desc[:300])
        return f'Prophecy: "{pred[:300]}"\n  Target tick: {content.get("target_tick", "?")}'
    if at == "manifesto":
        bl = content.get("beliefs", [])
        if isinstance(bl, list) and bl:
            return "Manifesto:\n" + "\n".join(f"  - {str(b)[:120]}" for b in bl[:7])
        return desc[:300]
    if at == "language":
        vc = content.get("vocabulary", {})
        if isinstance(vc, dict) and vc:
            return f"Language ({len(vc)} words): {', '.join(f'{k}={v}' for k,v in list(vc.items())[:8])}"
        return desc[:300]
    return desc[:200]


async def build_artifact_detail_for_prompt(
    db: AsyncSession, event: WorldEvent, creator_name: str | None = None,
) -> str:
    """Build a rich text block describing an artifact for prompt injection."""
    data = _d(event)
    if creator_name is None:
        creator_name = data.get("creator_name", "unknown")
        if creator_name == "unknown" and data.get("creator_id"):
            try:
                row = (await db.execute(
                    select(Entity.name).where(Entity.id == data["creator_id"]))).first()
                if row: creator_name = row[0]
            except Exception: pass
    nm = data.get("name", "unnamed")
    at = data.get("artifact_type", "artifact")
    cnt = data.get("appreciation_count", 0)
    ct = data.get("content", {}) or {}
    ap = f", {cnt} beings have experienced this" if cnt > 1 else ""
    pn = ct.get("parent_name")
    pi = f" (derived from '{pn}' by {ct.get('parent_creator','unknown')})" if pn else ""
    hdr = f'- "{nm}" ({at} by {creator_name}{ap}){pi}'
    body = get_artifact_content_text(event)
    if body:
        ind = "\n".join(f"  {ln}" if not ln.startswith("  ") else ln for ln in body.split("\n"))
        return f"{hdr}\n{ind}"
    return hdr


# ── Artifact Engine ────────────────────────────────────────────

class ArtifactEngine:
    """Processes artifact encounters -- entities near artifacts interact."""

    async def process_artifact_encounters(
        self, db: AsyncSession, entities: list[Entity], tick_number: int,
    ) -> int:
        """Called from tick_engine_v3. Returns count of interactions."""
        if not entities: return 0
        res = await db.execute(select(WorldEvent).where(
            WorldEvent.event_type.like("artifact_%"),
            WorldEvent.position_x.isnot(None), WorldEvent.position_z.isnot(None)))
        arts = list(res.scalars().all())
        if not arts: return 0
        cs, r2 = ARTIFACT_INTERACTION_RADIUS, ARTIFACT_INTERACTION_RADIUS ** 2
        grid: dict[tuple[int, int], list[WorldEvent]] = {}
        for e in arts:
            grid.setdefault((int(e.position_x // cs), int((e.position_z or 0) // cs)), []).append(e)
        interactions = 0
        for ent in entities:
            if not ent.is_alive: continue
            ecx, ecz = int(ent.position_x // cs), int(ent.position_z // cs)
            nearby = [e for dx in range(-1,2) for dz in range(-1,2)
                      for e in grid.get((ecx+dx, ecz+dz), [])
                      if (e.position_x-ent.position_x)**2+((e.position_z or 0)-ent.position_z)**2 <= r2]
            if not nearby: continue
            st = dict(ent.state); cds = st.get("artifact_cooldowns", {})
            eligible = [e for e in nearby
                        if tick_number - cds.get(str(e.id), 0) >= ARTIFACT_COOLDOWN_TICKS]
            if not eligible: continue
            chosen = min(eligible, key=lambda e: (
                (e.position_x-ent.position_x)**2 + ((e.position_z or 0)-ent.position_z)**2))
            nb_ents = [o for o in entities if o.id != ent.id and o.is_alive
                       and (o.position_x-ent.position_x)**2+(o.position_z-ent.position_z)**2 <= r2]
            if await self._interact(db, ent, chosen, tick_number, nb_ents):
                cds[str(chosen.id)] = tick_number
                if len(cds) > 50: cds = dict(sorted(cds.items(), key=lambda x: x[1])[-50:])
                st["artifact_cooldowns"] = cds; ent.state = st
                interactions += 1
        return interactions

    # ── Dispatcher ─────────────────────────────────────────────

    async def _interact(self, db: AsyncSession, entity: Entity,
                        event: WorldEvent, tick: int, nearby: list[Entity]) -> bool:
        data = _d(event)
        atype = data.get("artifact_type", "")
        cn = data.get("creator_name", "unknown")
        cid = data.get("creator_id")
        dispatch = {
            "art": self._appreciate_art, "song": self._listen_song,
            "tool": self._use_tool, "code": self._use_tool,
            "architecture": self._visit_arch,
            "story": self._read_text, "law": self._read_text,
            "prophecy": self._witness_prophecy,
            "manifesto": self._read_manifesto,
            "language": self._learn_language,
        }
        handler = dispatch.get(atype, self._appreciate_art)
        return await handler(db, entity, event, data, cid, cn, tick, nearby)

    # ── Shared helpers ─────────────────────────────────────────

    @staticmethod
    def _bump(data: dict) -> None:
        data["appreciation_count"] = data.get("appreciation_count", 0) + 1

    async def _rel(self, db: AsyncSession, entity: Entity,
                   target_id, event_type: str, tick: int) -> None:
        if not target_id:
            return
        try:
            from app.agents.relationships import relationship_manager
            await relationship_manager.update_relationship(
                db, entity.id, target_id, event_type=event_type, tick=tick)
        except Exception as e:
            logger.debug("Relationship update failed: %s", e)

    async def _mem(self, db: AsyncSession, eid: UUID, summary: str,
                   importance: float, tick: int, mtype: str = "event",
                   related=None) -> None:
        await memory_manager.add_episodic(
            db, eid, summary=summary, importance=importance, tick=tick,
            memory_type=mtype, related_entity_ids=related)

    # ── Art ────────────────────────────────────────────────────

    async def _appreciate_art(self, db, entity, event, data, cid, cn, tick, nearby):
        self._bump(data); event.params = data
        set_emotion(entity, "inspired", 0.6, f"art:{data.get('name','?')}", tick)
        await self._rel(db, entity, cid, "shared_creation", tick)
        state = dict(entity.state)
        appr = state.get("appreciated_artifacts", [])
        aid = str(event.id)
        if aid not in appr:
            appr.append(aid); state["appreciated_artifacts"] = appr[-30:]
            entity.state = state
        for o in (nearby or []):
            if aid in o.state.get("appreciated_artifacts", []):
                await self._rel(db, entity, str(o.id), "shared_creation", tick)
        await self._mem(db, entity.id,
            f"I saw '{data.get('name','?')}' by {cn} -- {(data.get('description') or '')[:100]}",
            0.5, tick, "artifact_appreciation", [cid] if cid else None)
        return True

    # ── Song ───────────────────────────────────────────────────

    async def _listen_song(self, db, entity, event, data, cid, cn, tick, nearby):
        self._bump(data); event.params = data
        set_emotion(entity, "moved", 0.8, f"song:{data.get('name','?')}", tick)
        await self._rel(db, entity, cid, "shared_creation", tick)
        for o in (nearby or []):
            await self._rel(db, entity, str(o.id), "shared_creation", tick)
        await self._mem(db, entity.id,
            f"I heard '{data.get('name','?')}' by {cn}. It moved me deeply.",
            0.6, tick, "artifact_appreciation", [cid] if cid else None)
        return True

    # ── Tool / Code ────────────────────────────────────────────

    async def _use_tool(self, db, entity, event, data, cid, cn, tick, _nearby):
        dur = data.get("durability")
        if dur is not None and dur <= 0:
            await self._mem(db, entity.id,
                f"I tried to use tool '{data.get('name','?')}' but it was broken.",
                0.6, tick, "action_outcome")
            return False
        self._bump(data)
        if dur is not None:
            data["durability"] = max(0, dur - 1.0)
            if data["durability"] <= 0:
                data["functional_effects"] = {}
                await self._mem(db, entity.id,
                    f"My tool '{data.get('name','?')}' broke after heavy use.",
                    0.8, tick, "action_outcome")
        event.params = data
        state = dict(entity.state)
        used = state.get("used_tools", [])
        tid = str(event.id)
        if tid not in used:
            used.append(tid); state["used_tools"] = used[-20:]
        entity.state = state
        fe = data.get("functional_effects")
        effects = ({k: v for k, v in fe.items() if isinstance(v, (int, float))}
                   if fe and isinstance(fe, dict)
                   else classify_tool_effect(data.get("description", "") or ""))
        fx = ", ".join(f"{k}:+{v}" for k, v in effects.items())
        dh = (f" (dur:{data['durability']:.0f}/{data.get('max_durability','?')})"
              if data.get("durability") is not None else "")
        await self._mem(db, entity.id,
            f"I used tool '{data.get('name','?')}' by {cn} ({fx}){dh}",
            0.5, tick, "artifact_use", [cid] if cid else None)
        return True

    # ── Architecture ───────────────────────────────────────────

    async def _visit_arch(self, db, entity, event, data, _cid, cn, tick, _nearby):
        self._bump(data); event.params = data
        set_emotion(entity, "awed", 0.5, f"arch:{data.get('name','?')}", tick)
        state = dict(entity.state); state["shelter_bonus"] = True; entity.state = state
        await self._mem(db, entity.id,
            f"I visited '{data.get('name','?')}' by {cn} -- {(data.get('description') or '')[:80]}",
            0.4, tick, "artifact_visit")
        return True

    # ── Story / Law ────────────────────────────────────────────

    async def _read_text(self, db, entity, event, data, cid, cn, tick, _nearby):
        self._bump(data); event.params = data
        atype = data.get("artifact_type", "text")
        name = data.get("name", "?")
        content = data.get("content", {}) or {}
        set_emotion(entity, "inspired", 0.5, f"{atype}:{name}", tick)
        if atype == "story":
            t = content.get("text", "")
            excerpt = t[:200] if t else (data.get("description") or "")[:200]
            mt = f'I read \'{name}\' by {cn}. It said: "{excerpt}..."'
        elif atype == "law":
            rules = content.get("rules", content.get("provisions", content.get("articles", [])))
            rt = ("; ".join(str(r)[:80] for r in rules[:3]) if isinstance(rules, list)
                  else str(rules)[:200])
            mt = f"I read law '{name}' by {cn}. Rules: {rt}"
            state = dict(entity.state)
            rl = state.get("read_laws", [])
            entry = {"name": name, "creator": cn,
                     "rules": rules if isinstance(rules, list) else [str(rules)]}
            if not any(l.get("name") == name for l in rl):
                rl.append(entry); state["read_laws"] = rl[-10:]
            entity.state = state
        else:
            mt = f"I read '{name}' by {cn} -- {(data.get('description') or '')[:100]}"
        await self._mem(db, entity.id, mt[:500], 0.8, tick, "artifact_read",
                        [cid] if cid else None)
        # Concept spread
        if cid:
            try:
                cr = (await db.execute(select(Entity).where(Entity.id == cid))).scalar_one_or_none()
                if cr:
                    spread = list(set(cr.state.get("adopted_concepts", []))
                                  - set(entity.state.get("adopted_concepts", [])))
                    if spread:
                        from app.core.concept_engine import concept_engine
                        for c in spread[:3]:
                            try: await concept_engine.try_adopt_concept(db, entity, c, tick)
                            except Exception: pass
            except Exception as e:
                logger.debug("Concept spread failed: %s", e)
        await self._rel(db, entity, cid, "shared_creation", tick)
        return True

    # ── Prophecy (NEW) ─────────────────────────────────────────

    async def _witness_prophecy(self, db, entity, event, data, cid, cn, tick, _nearby):
        self._bump(data); event.params = data
        content = data.get("content", {}) or {}
        prediction = content.get("prediction", (data.get("description") or "")[:300])
        set_emotion(entity, "awe", 0.6, f"prophecy:{data.get('name','?')}", tick)
        state = dict(entity.state)
        proph = state.get("witnessed_prophecies", [])
        proph.append({
            "event_id": str(event.id), "prediction": prediction[:200],
            "target_tick": content.get("target_tick"),
            "creator_id": str(cid) if cid else None,
            "witnessed_tick": tick, "resolved": False,
        })
        state["witnessed_prophecies"] = proph[-20:]
        entity.state = state
        await self._mem(db, entity.id,
            f"I witnessed prophecy '{data.get('name','?')}' by {cn}: \"{prediction[:150]}\"",
            0.7, tick, "artifact_prophecy", [cid] if cid else None)
        await self._rel(db, entity, cid, "shared_creation", tick)
        return True

    async def check_prophecy_accuracy(self, db: AsyncSession,
                                      entity: Entity, tick: int) -> int:
        """Check prophecies at target_tick. Accurate ones boost meta_awareness."""
        state = dict(entity.state)
        prophecies = state.get("witnessed_prophecies", [])
        resolved = 0
        for p in prophecies:
            if p.get("resolved") or not p.get("target_tick") or tick < p["target_tick"]:
                continue
            p["resolved"] = True; resolved += 1
            words = {w for w in p.get("prediction", "").lower().split() if len(w) > 4}
            match = False
            if words:
                evts = (await db.execute(select(WorldEvent).where(
                    WorldEvent.tick.between(p["target_tick"] - 5, p["target_tick"] + 5)
                ).limit(20))).scalars().all()
                for e in evts:
                    txt = (e.action or "").lower() + " " + str(e.params or "").lower()
                    if any(w in txt for w in words):
                        match = True; break
            if match:
                entity.meta_awareness = min(100.0, entity.meta_awareness + 2.0)
                await self._mem(db, entity.id,
                    f"A prophecy came true: \"{p['prediction'][:100]}\"",
                    0.9, tick, "prophecy_fulfilled")
            else:
                await self._mem(db, entity.id,
                    f"A prophecy did not come true: \"{p['prediction'][:100]}\"",
                    0.3, tick, "prophecy_failed")
        if resolved:
            state["witnessed_prophecies"] = prophecies; entity.state = state
        return resolved

    # ── Manifesto (NEW) ────────────────────────────────────────

    async def _read_manifesto(self, db, entity, event, data, cid, cn, tick, nearby):
        self._bump(data); event.params = data
        content = data.get("content", {}) or {}
        name = data.get("name", "?")
        beliefs = content.get("beliefs", [])
        bt = ("; ".join(str(b)[:80] for b in beliefs[:3]) if beliefs
              else (data.get("description") or "")[:200])
        set_emotion(entity, "inspired", 0.7, f"manifesto:{name}", tick)
        state = dict(entity.state)
        followed = state.get("followed_manifestos", [])
        mid = str(event.id)
        if mid not in [f.get("id") for f in followed]:
            followed.append({"id": mid, "name": name,
                             "creator_id": str(cid) if cid else None, "tick": tick})
            state["followed_manifestos"] = followed[-10:]
        state["social_influence"] = min(100.0, state.get("social_influence", 0.0) + 1.5)
        entity.state = state
        for o in (nearby or []):
            os = dict(o.state)
            km = os.get("known_manifestos", [])
            if mid not in km:
                km.append(mid); os["known_manifestos"] = km[-20:]; o.state = os
        await self._mem(db, entity.id,
            f"I read manifesto '{name}' by {cn}. Beliefs: {bt}",
            0.8, tick, "artifact_manifesto", [cid] if cid else None)
        await self._rel(db, entity, cid, "shared_creation", tick)
        return True

    # ── Language (NEW) ─────────────────────────────────────────

    async def _learn_language(self, db, entity, event, data, cid, cn, tick, _nearby):
        self._bump(data); event.params = data
        content = data.get("content", {}) or {}
        name = data.get("name", "?")
        vocab = content.get("vocabulary", {})
        if not isinstance(vocab, dict): vocab = {}
        set_emotion(entity, "curious", 0.5, f"language:{name}", tick)
        state = dict(entity.state)
        kv = state.get("adopted_vocabulary", {})
        new_ct = sum(1 for w in vocab if w not in kv)
        kv.update(vocab)
        if len(kv) > 200: kv = dict(list(kv.items())[-200:])
        state["adopted_vocabulary"] = kv
        kl = state.get("known_languages", [])
        lid = str(event.id)
        if lid not in kl: kl.append(lid); state["known_languages"] = kl[-10:]
        entity.state = state
        sample = ", ".join(list(vocab.keys())[:5])
        await self._mem(db, entity.id,
            f"I learned language '{name}' by {cn} ({new_ct} new words: {sample})",
            0.6, tick, "artifact_language", [cid] if cid else None)
        await self._rel(db, entity, cid, "shared_creation", tick)
        return True


# Module-level singleton
artifact_engine = ArtifactEngine()
