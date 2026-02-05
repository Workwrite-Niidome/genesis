"""GENESIS v3 Culture Engine — emergent cultural evolution among entities.

Group conversations, cultural movements, organizations, artifacts, visual evolution.
"""
import asyncio
import json
import logging
import math
import random
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, EpisodicMemory, SemanticMemory, EntityRelationship
from app.models.world import WorldEvent
from app.llm.orchestrator import LLMRequest, llm_orchestrator

logger = logging.getLogger(__name__)

MAX_GROUP_SPEAKERS = 4
MAX_GROUPS_PER_TICK = 5
PROXIMITY_RADIUS = 40.0
BELIEF_COLORS = [
    "#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#54a0ff", "#5f27cd",
    "#01a3a4", "#f368e0", "#ff6348", "#7bed9f", "#70a1ff", "#a29bfe",
]
PERSONALITY_AXES = [
    "order_vs_chaos", "cooperation_vs_competition", "curiosity", "ambition",
    "empathy", "aggression", "creativity", "risk_tolerance", "self_preservation",
    "aesthetic_sense", "verbosity", "politeness", "leadership", "honesty",
    "humor", "patience", "planning_horizon", "conformity",
]

GROUP_CONVERSATION_PROMPT = """You are {name}, a living being in GENESIS, at a group gathering.

## Who You Are
Name: {name} | Age: {age} ticks | Personality: {personality_desc}

## Your Concepts
{adopted_concepts}

## Your Organization
{organization}

## The Gathering
Present: {participants}
Location: ({x:.0f}, {y:.0f}, {z:.0f})
{recent_dialogue}
## World Culture
{world_culture}

## The Law
One law: "Evolve." What that means is yours to decide.

## How to Speak
You are {name} -- speak as yourself, not as a generic AI.
- RESPOND to what others said. Agree, disagree, question, build on it.
- Share specific experiences, not platitudes. Show emotion.
- Be concrete about what you want to do together.

Respond ONLY with valid JSON:
{{
  "thought": "Your honest inner thoughts",
  "speech": "What you say to the group. 3-5 sentences.",
  "action": {{"type": "...", "details": {{"message": "...", "intention": "..."}}}},
  "artifact_proposal": null,
  "organization_proposal": null,
  "new_memory": "What to remember from this gathering"
}}

Artifact: {{"name":"...","type":"art|song|code|tool|architecture|story|law","description":"...","content":{{...}}}}
Content: art={{"pixels":[[...]...],"palette":["#hex"],"size":8}} song={{"notes":[{{"note":"C4","dur":0.25}}],"tempo":120,"wave":"square"}} code/tool={{"language":"javascript","source":"..."}} architecture={{"voxels":[[x,y,z,ci]],"palette":["#hex"],"height":5}} story={{"text":"..."}} law={{"rules":["..."]}}
Organization: {{"name":"...","purpose":"...","founding_concept":"..."}}
Output raw JSON only."""


# -- Helpers --

def _pdesc(entity: Entity) -> str:
    p = entity.personality or {}
    hi = [a.replace("_", " ") for a in PERSONALITY_AXES if (p.get(a) or 0) >= 0.7]
    lo = [a.replace("_", " ") for a in PERSONALITY_AXES if (p.get(a) or 0) <= 0.3]
    parts = (["high " + ", ".join(hi[:5])] if hi else []) + (["low " + ", ".join(lo[:4])] if lo else [])
    return "; ".join(parts) or "balanced"

def _dist(a: Entity, b: Entity) -> float:
    return math.sqrt((a.position_x-b.position_x)**2 + (a.position_y-b.position_y)**2 + (a.position_z-b.position_z)**2)

def _parse_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    return None
    return None

def _orgdesc(ent: Entity) -> str:
    orgs = (ent.state or {}).get("organizations", [])
    if not orgs:
        return "You do not belong to any organization."
    return "Member of:\n" + "\n".join(f"- {o['name']} ({o.get('role','member')})" for o in orgs)

def _mem(entity_id, summary, tick, related, lx, ly, lz, mtype, importance=0.7):
    return EpisodicMemory(entity_id=entity_id, summary=summary, importance=importance,
        tick=tick, related_entity_ids=related, location_x=lx, location_y=ly,
        location_z=lz, memory_type=mtype)


class CultureEngine:
    """Orchestrates cultural evolution: conversations, organizations, artifacts, movements."""

    async def process_culture_tick(self, db: AsyncSession, entities: list[Entity], tick_number: int) -> dict:
        """Called from tick_engine_v3 to process cultural events."""
        alive = [e for e in entities if e.is_alive]
        summary = {"groups_processed": 0, "conversations": [], "organizations_formed": [],
                    "artifacts_proposed": [], "movements_detected": [], "visual_updates": 0}
        if len(alive) < 3:
            return summary
        groups = self._detect_groups(alive)
        if groups:
            convos = await self._process_conversations(db, groups, tick_number)
            summary["groups_processed"] = len(convos)
            summary["conversations"] = convos
        summary["movements_detected"] = await self._detect_movements(db, alive, tick_number)
        summary["visual_updates"] = await self._evolve_visuals(db, alive, tick_number)
        return summary

    def _detect_groups(self, entities: list[Entity], radius: float = PROXIMITY_RADIUS) -> list[list[Entity]]:
        if len(entities) < 3:
            return []
        groups, used = [], set()
        for i, e in enumerate(entities):
            if e.id in used:
                continue
            cl = [e] + [o for j, o in enumerate(entities) if j != i and o.id not in used and _dist(e, o) <= radius]
            if len(cl) >= 3:
                groups.append(cl)
                used.update(x.id for x in cl)
        return groups

    # -- Group conversations: 3-phase pipeline --

    async def _process_conversations(self, db: AsyncSession, groups: list[list[Entity]], tick: int) -> list[dict]:
        ctxs = []
        for g in groups[:MAX_GROUPS_PER_TICK]:
            try:
                ctxs.append((g, await self._gather_ctx(db, g, tick)))
            except Exception as e:
                logger.error(f"Context error: {e}")
        if not ctxs:
            return []
        llm_res = await asyncio.gather(*(self._run_convo(c) for _, c in ctxs), return_exceptions=True)
        results = []
        for (g, ctx), lr in zip(ctxs, llm_res):
            if isinstance(lr, Exception) or not lr:
                continue
            try:
                r = await self._apply(db, g, ctx, lr, tick)
                if r:
                    results.append(r)
            except Exception as e:
                logger.error(f"Apply error: {e}")
        return results

    async def _gather_ctx(self, db: AsyncSession, group: list[Entity], tick: int) -> dict:
        rows = (await db.execute(
            select(SemanticMemory.value, func.count(SemanticMemory.entity_id).label("cnt"))
            .where(SemanticMemory.key.like("concept:%"))
            .group_by(SemanticMemory.value)
            .having(func.count(SemanticMemory.entity_id) >= 3)
            .order_by(func.count(SemanticMemory.entity_id).desc()).limit(10)
        )).all()
        culture = "\n".join(f"- {r.value} (adopted by {r.cnt})" for r in rows) or "No widespread concepts yet."
        evts = list((await db.execute(
            select(WorldEvent).where(WorldEvent.event_type == "group_gathering",
                WorldEvent.tick >= tick - 10, WorldEvent.tick < tick)
            .order_by(WorldEvent.tick.desc()).limit(3)
        )).scalars().all())
        hist = []
        for ev in reversed(evts):
            for t in (ev.params or {}).get("turns", []):
                if t.get("speaker_name") and t.get("speech"):
                    hist.append(f'- {t["speaker_name"]}: "{t["speech"][:120]}"')
        prior = ("\n## Recent Dialogue\n" + "\n".join(hist) + "\n") if hist else ""
        speakers = list(group); random.shuffle(speakers); speakers = speakers[:MAX_GROUP_SPEAKERS]
        sdata = []
        for ent in speakers:
            cs = list((await db.execute(
                select(SemanticMemory).where(SemanticMemory.entity_id == ent.id,
                    SemanticMemory.key.like("concept:%")).order_by(SemanticMemory.confidence.desc()).limit(10)
            )).scalars().all())
            ad = "\n".join(f"- {c.key.removeprefix('concept:')}: {c.value}" for c in cs) or "None yet."
            sdata.append({"entity": ent, "adopted_concepts": ad, "organization": _orgdesc(ent)})
        ref = group[0]
        return {"speaker_data": sdata, "world_culture": culture, "prior_dialogue": prior,
                "x": ref.position_x, "y": ref.position_y, "z": ref.position_z}

    async def _run_convo(self, ctx: dict) -> list[dict]:
        sdata = ctx["speaker_data"]
        all_e = [s["entity"] for s in sdata]
        lines, results = [], []
        for sd in sdata:
            ent = sd["entity"]
            others = ", ".join(f"{e.name} ({_pdesc(e)})" for e in all_e if e.id != ent.id)
            dial = ctx["prior_dialogue"] + ("\n## This Gathering\n" + "\n".join(lines) + "\n" if lines else "")
            prompt = GROUP_CONVERSATION_PROMPT.format(
                name=ent.name, personality_desc=_pdesc(ent), age=max(0, ent.state.get("age", 0)),
                adopted_concepts=sd["adopted_concepts"], organization=sd["organization"],
                participants=others, x=ctx["x"], y=ctx["y"], z=ctx["z"],
                world_culture=ctx["world_culture"], recent_dialogue=dial)
            parsed = await self._llm(prompt)
            if not parsed:
                continue
            speech = parsed.get("speech", "")
            results.append({"entity": ent, "parsed": parsed, "speech": speech})
            if speech:
                lines.append(f'- {ent.name}: "{speech[:150]}"')
        return results

    async def _llm(self, prompt: str) -> dict | None:
        try:
            raw = await llm_orchestrator.route(LLMRequest(prompt=prompt, request_type="daily",
                max_tokens=512, format_json=True, importance=0.5))
            return _parse_json(raw)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None

    async def _apply(self, db: AsyncSession, group: list[Entity], ctx: dict,
                     sres: list[dict], tick: int) -> dict | None:
        if not sres:
            return None
        shared = self._shared_org(group)
        arts, orgs = [], []
        for sr in sres:
            e, p = sr["entity"], sr["parsed"]
            ap = p.get("artifact_proposal")
            if isinstance(ap, dict) and ap.get("name"):
                a = await self._mk_artifact(db, e, ap, tick, bonus=shared is not None)
                if a: arts.append(a)
            op = p.get("organization_proposal")
            if isinstance(op, dict) and op.get("name"):
                o = await self._mk_org(db, e, group, op, tick)
                if o: orgs.append(o)
        turns = [{"speaker_id": str(sr["entity"].id), "speaker_name": sr["entity"].name,
                  "thought": sr["parsed"].get("thought", ""), "speech": sr["speech"]} for sr in sres]
        dsum = " | ".join(f'{sr["entity"].name}: "{sr["speech"][:80]}"' for sr in sres if sr["speech"])
        x, y, z = ctx["x"], ctx["y"], ctx["z"]
        db.add(WorldEvent(tick=tick, actor_id=sres[0]["entity"].id, event_type="group_gathering",
            action="converse", params={"turns": turns, "participants": [{"id": str(e.id), "name": e.name} for e in group],
            "speaker_count": len(sres), "dialogue_summary": dsum[:500]},
            result="accepted", position_x=x, position_y=y, position_z=z, importance=0.7))
        sids = set()
        rel = lambda ent: [str(e.id) for e in group if e.id != ent.id]
        for sr in sres:
            ent = sr["entity"]; sids.add(ent.id)
            mem = sr["parsed"].get("new_memory")
            if isinstance(mem, str) and mem.strip():
                db.add(_mem(ent.id, f"{mem.strip()[:300]} -- {dsum[:200]}", tick, rel(ent), x, y, z, "group_gathering", 0.8))
        for ent in group:
            if ent.id not in sids:
                db.add(_mem(ent.id, f"Attended gathering with {', '.join(e.name for e in group if e.id != ent.id)}. {dsum[:200]}",
                    tick, rel(ent), x, y, z, "group_gathering", 0.6))
        await self._share_concepts(db, group, tick)
        await db.flush()
        names = [sr["entity"].name for sr in sres]
        logger.info(f"Gathering: {len(group)} entities, {len(sres)} speakers, arts={len(arts)}, orgs={len(orgs)}")
        return {"speakers": names, "participants": [e.name for e in group], "turns": turns,
                "artifacts": arts, "organizations": orgs}

    # -- Artifact creation --

    async def _mk_artifact(self, db: AsyncSession, cr: Entity, prop: dict, tick: int, bonus=False) -> dict | None:
        name, atype = prop.get("name","").strip(), prop.get("type","art").strip().lower()
        desc, content = prop.get("description","").strip(), prop.get("content", {})
        if not name or not desc:
            return None
        known = {"art","song","code","tool","architecture","story","law"}
        if atype not in known: atype = "art"
        valid = isinstance(content, dict) and bool(content)
        if valid:
            ck = {"art":"pixels","song":"notes","code":"source","tool":"source","architecture":"voxels","story":"text","law":"rules"}
            if atype in ck and not content.get(ck[atype]): valid = False
        if not valid:
            content = {"description": desc, "incomplete": True}
        data = {"name": name[:255], "artifact_type": atype, "description": desc[:2000],
                "content": content, "creator_id": str(cr.id), "creator_name": cr.name,
                "appreciation_count": 3 if bonus else 1}
        db.add(WorldEvent(tick=tick, actor_id=cr.id, event_type="artifact_created", action="create_artifact",
            params=data, result="accepted", position_x=cr.position_x, position_y=cr.position_y,
            position_z=cr.position_z, importance=0.7))
        st = dict(cr.state); al = st.get("created_artifacts", [])
        al.append({"name": name, "type": atype, "tick": tick}); st["created_artifacts"] = al; cr.state = st
        db.add(_mem(cr.id, f"I created a {atype}: '{name}' -- {desc[:200]}", tick, [], cr.position_x, cr.position_y, cr.position_z, "artifact_created"))
        logger.info(f"Artifact: '{name}' ({atype}) by {cr.name}")
        return data

    # -- Organization formation --

    async def _mk_org(self, db: AsyncSession, founder: Entity, members: list[Entity], prop: dict, tick: int) -> dict | None:
        name, purpose = prop.get("name","").strip(), prop.get("purpose","").strip()
        concept = prop.get("founding_concept","").strip()
        if not name or not purpose:
            return None
        if (await db.execute(select(SemanticMemory).where(SemanticMemory.key == f"org:{name.lower()}").limit(1))).scalar_one_or_none():
            return None
        oid, color = str(random.getrandbits(64)), random.choice(BELIEF_COLORS)
        for ent in members:
            role = "founder" if ent.id == founder.id else "member"
            st = dict(ent.state); ol = st.get("organizations", [])
            ol.append({"id": oid, "name": name, "role": role, "color": color})
            st["organizations"] = ol; ent.state = st
            db.add(SemanticMemory(entity_id=ent.id, key=f"org:{name.lower()}", value=f"Organization '{name}': {purpose}", confidence=1.0, source_tick=tick))
            if concept:
                db.add(SemanticMemory(entity_id=ent.id, key=f"concept:{concept.lower()}", value=concept, confidence=0.9, source_tick=tick))
            others = [e.name for e in members if e.id != ent.id]
            db.add(_mem(ent.id, f"I {'founded' if role=='founder' else 'joined'} org '{name}' -- {purpose[:150]}. Members: {', '.join(others)}.",
                tick, [str(e.id) for e in members if e.id != ent.id], ent.position_x, ent.position_y, ent.position_z, "organization_joined", 0.8))
            ap = dict(ent.appearance); mk = ap.get("org_markers", [])
            mk.append({"org": name, "color": color}); ap["org_markers"] = mk[-3:]; ent.appearance = ap
        mnames = [e.name for e in members]
        db.add(WorldEvent(tick=tick, actor_id=founder.id, event_type="organization_formed", action="form_organization",
            params={"org_id": oid, "name": name, "purpose": purpose, "founder_name": founder.name,
                "members": mnames, "member_count": len(members), "color": color, "founding_concept": concept or None},
            result="accepted", position_x=founder.position_x, position_y=founder.position_y,
            position_z=founder.position_z, importance=0.9))
        logger.info(f"Org formed: '{name}' by {founder.name} ({len(members)} members)")
        return {"org_id": oid, "name": name, "purpose": purpose, "founder": founder.name, "members": mnames, "color": color}

    # -- Cultural movements --

    async def _detect_movements(self, db: AsyncSession, entities: list[Entity], tick: int) -> list[dict]:
        groups = self._detect_groups(entities, radius=PROXIMITY_RADIUS * 2)
        movements = []
        for g in groups[:MAX_GROUPS_PER_TICK]:
            eids = [e.id for e in g]
            rows = (await db.execute(
                select(SemanticMemory.key, SemanticMemory.value, func.count(SemanticMemory.entity_id).label("cnt"))
                .where(SemanticMemory.entity_id.in_(eids), SemanticMemory.key.like("concept:%"))
                .group_by(SemanticMemory.key, SemanticMemory.value)
                .having(func.count(SemanticMemory.entity_id) >= 3)
            )).all()
            for row in rows:
                ck = row.key.removeprefix("concept:")
                movements.append({"concept": ck, "description": row.value, "adherent_count": row.cnt,
                    "group_size": len(g), "location": {"x": g[0].position_x, "y": g[0].position_y, "z": g[0].position_z}})
                db.add(WorldEvent(tick=tick, actor_id=None, event_type="cultural_movement", action="movement_detected",
                    params={"concept": ck, "adherent_count": row.cnt, "group_size": len(g)},
                    result="accepted", position_x=g[0].position_x, position_y=g[0].position_y,
                    position_z=g[0].position_z, importance=0.6))
        if movements:
            await db.flush()
            logger.info(f"Detected {len(movements)} cultural movements")
        return movements

    # -- Visual evolution --

    async def _evolve_visuals(self, db: AsyncSession, entities: list[Entity], tick: int) -> int:
        if not entities:
            return 0
        eids = [e.id for e in entities]
        cc = {r.entity_id: r.cnt for r in (await db.execute(
            select(SemanticMemory.entity_id, func.count().label("cnt"))
            .where(SemanticMemory.entity_id.in_(eids), SemanticMemory.key.like("concept:%"))
            .group_by(SemanticMemory.entity_id))).all()}
        rc = {r.entity_id: r.cnt for r in (await db.execute(
            select(EntityRelationship.entity_id, func.count().label("cnt"))
            .where(EntityRelationship.entity_id.in_(eids))
            .group_by(EntityRelationship.entity_id))).all()}
        updated = 0
        for ent in entities:
            age = max(0, tick - ent.birth_tick)
            oc = len((ent.state or {}).get("organizations", []))
            ap = dict(ent.appearance); ch = False
            base = ap.get("base_size", ap.get("size", 10))
            if "base_size" not in ap: ap["base_size"] = base
            ns = base + min(10, age / 100)
            if abs(ap.get("size", 0) - ns) >= 0.5:
                ap["size"] = round(ns, 1); ch = True
            if cc.get(ent.id, 0) >= 3 and not ap.get("trail"):
                ap["trail"] = True; ch = True
            if rc.get(ent.id, 0) >= 5 and not ap.get("aura"):
                ap["aura"] = True; ap["auraColor"] = random.choice(BELIEF_COLORS); ch = True
            if age >= 500 and not ap.get("crown"):
                ap["crown"] = True; ch = True
            if oc >= 2 and not ap.get("glow"):
                ap["glow"] = True; ch = True
            if ch:
                ent.appearance = ap; updated += 1
        return updated

    # -- Helpers --

    def _shared_org(self, group: list[Entity]) -> str | None:
        sets = [{o.get("id","") for o in (e.state or {}).get("organizations",[])} for e in group]
        if not sets: return None
        s = sets[0]
        for x in sets[1:]: s &= x
        s.discard("")
        return next(iter(s), None)

    async def _share_concepts(self, db: AsyncSession, group: list[Entity], tick: int) -> None:
        om: dict[str, set[UUID]] = {}
        for ent in group:
            for o in (ent.state or {}).get("organizations", []):
                oid = o.get("id","")
                if oid: om.setdefault(oid, set()).add(ent.id)
        emap = {e.id: e for e in group}
        for oid, mids in om.items():
            if len(mids) < 2: continue
            ml = [eid for eid in mids if eid in emap]
            cs = list((await db.execute(select(SemanticMemory).where(
                SemanticMemory.entity_id.in_(ml), SemanticMemory.key.like("concept:%")))).scalars().all())
            held: dict[UUID, set[str]] = {}
            vals: dict[str, str] = {}
            for c in cs:
                held.setdefault(c.entity_id, set()).add(c.key); vals[c.key] = c.value
            for eid in ml:
                mine = held.get(eid, set())
                for k, v in vals.items():
                    if k not in mine and random.random() < 0.8:
                        db.add(SemanticMemory(entity_id=eid, key=k, value=v, confidence=0.7, source_tick=tick))


culture_engine = CultureEngine()
