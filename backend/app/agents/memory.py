"""
GENESIS v3 - Memory System
===========================
Episodic + semantic memory storage and management for AI entities.

Episodic memories are time-bound events with importance scores and TTLs.
Semantic memories are persistent key-value knowledge entries with confidence.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import EpisodicMemory, SemanticMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages an entity's memories: episodic events and semantic knowledge.

    Episodic memories represent experienced events with an importance score
    and a TTL derived from that importance. They are capped per entity.

    Semantic memories represent learned facts as key-value pairs with a
    confidence score, upserted on the key.
    """

    MAX_EPISODIC = 500  # Max episodic memories per entity
    TTL_MULTIPLIER = 10_000  # TTL in ticks = importance * TTL_MULTIPLIER

    # ------------------------------------------------------------------
    # Episodic memories
    # ------------------------------------------------------------------

    async def add_episodic(
        self,
        db: AsyncSession,
        entity_id: UUID,
        summary: str,
        importance: float,
        tick: int,
        related_entity_ids: list[UUID] | None = None,
        location: tuple[float, float, float] | None = None,
        memory_type: str = "event",
    ) -> EpisodicMemory:
        """Add an episodic memory.

        TTL is computed as ``importance * TTL_MULTIPLIER`` ticks.
        If the entity already has MAX_EPISODIC memories, the lowest-importance
        ones are pruned to make room.
        """
        ttl = int(importance * self.TTL_MULTIPLIER)
        expires_at_tick = tick + ttl

        # Serialize helpers
        related_ids = (
            [str(uid) for uid in related_entity_ids]
            if related_entity_ids
            else []
        )
        loc_dict = None
        if location is not None:
            loc_dict = {"x": location[0], "y": location[1], "z": location[2]}

        memory = EpisodicMemory(
            entity_id=entity_id,
            summary=summary,
            importance=importance,
            tick=tick,
            expires_at_tick=expires_at_tick,
            related_entity_ids=related_ids,
            location=loc_dict,
            memory_type=memory_type,
        )
        db.add(memory)
        await db.flush()

        # Enforce capacity limit -- remove lowest importance if over cap
        await self._enforce_capacity(db, entity_id)

        logger.debug(
            "Added episodic memory for entity %s: %s (importance=%.2f, ttl=%d)",
            entity_id, summary[:60], importance, ttl,
        )
        return memory

    async def _enforce_capacity(self, db: AsyncSession, entity_id: UUID) -> None:
        """Remove lowest-importance episodic memories if over MAX_EPISODIC."""
        count_q = select(func.count()).select_from(EpisodicMemory).where(
            EpisodicMemory.entity_id == entity_id
        )
        result = await db.execute(count_q)
        total = result.scalar_one()

        if total <= self.MAX_EPISODIC:
            return

        overflow = total - self.MAX_EPISODIC

        # Find the IDs of the lowest-importance memories to remove
        lowest_q = (
            select(EpisodicMemory.id)
            .where(EpisodicMemory.entity_id == entity_id)
            .order_by(EpisodicMemory.importance.asc(), EpisodicMemory.tick.asc())
            .limit(overflow)
        )
        result = await db.execute(lowest_q)
        ids_to_remove = [row[0] for row in result.all()]

        if ids_to_remove:
            await db.execute(
                delete(EpisodicMemory).where(EpisodicMemory.id.in_(ids_to_remove))
            )
            logger.debug(
                "Pruned %d low-importance memories for entity %s",
                len(ids_to_remove), entity_id,
            )

    # ------------------------------------------------------------------
    # Semantic memories
    # ------------------------------------------------------------------

    async def add_semantic(
        self,
        db: AsyncSession,
        entity_id: UUID,
        key: str,
        value: str,
        confidence: float,
        tick: int,
    ) -> SemanticMemory:
        """Add or update a semantic knowledge entry (upsert on key).

        If the key already exists for this entity, the value and confidence
        are updated and the tick is refreshed.
        """
        stmt = select(SemanticMemory).where(
            SemanticMemory.entity_id == entity_id,
            SemanticMemory.key == key,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.value = value
            existing.confidence = confidence
            existing.tick = tick
            await db.flush()
            logger.debug(
                "Updated semantic memory for entity %s: %s = %s (conf=%.2f)",
                entity_id, key, value[:60], confidence,
            )
            return existing

        memory = SemanticMemory(
            entity_id=entity_id,
            key=key,
            value=value,
            confidence=confidence,
            tick=tick,
        )
        db.add(memory)
        await db.flush()
        logger.debug(
            "Added semantic memory for entity %s: %s = %s (conf=%.2f)",
            entity_id, key, value[:60], confidence,
        )
        return memory

    # ------------------------------------------------------------------
    # Retrieval -- episodic
    # ------------------------------------------------------------------

    async def get_recent_memories(
        self, db: AsyncSession, entity_id: UUID, limit: int = 20
    ) -> list[dict]:
        """Get most recent episodic memories, ordered newest-first."""
        stmt = (
            select(EpisodicMemory)
            .where(EpisodicMemory.entity_id == entity_id)
            .order_by(EpisodicMemory.tick.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [self._episodic_to_dict(m) for m in result.scalars().all()]

    async def get_important_memories(
        self, db: AsyncSession, entity_id: UUID, limit: int = 10
    ) -> list[dict]:
        """Get highest importance episodic memories."""
        stmt = (
            select(EpisodicMemory)
            .where(EpisodicMemory.entity_id == entity_id)
            .order_by(EpisodicMemory.importance.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [self._episodic_to_dict(m) for m in result.scalars().all()]

    async def get_memories_about(
        self,
        db: AsyncSession,
        entity_id: UUID,
        target_entity_id: UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Get memories involving a specific entity.

        Searches the ``related_entity_ids`` JSON array for the target ID.
        """
        target_str = str(target_entity_id)

        # Use a JSON contains check -- works with PostgreSQL and SQLite JSON1
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.entity_id == entity_id,
                EpisodicMemory.related_entity_ids.contains(target_str),
            )
            .order_by(EpisodicMemory.tick.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [self._episodic_to_dict(m) for m in result.scalars().all()]

    # ------------------------------------------------------------------
    # Retrieval -- semantic
    # ------------------------------------------------------------------

    async def get_semantic(
        self, db: AsyncSession, entity_id: UUID, key: str
    ) -> str | None:
        """Get a semantic knowledge value by key, or None if not found."""
        stmt = select(SemanticMemory.value).where(
            SemanticMemory.entity_id == entity_id,
            SemanticMemory.key == key,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def get_all_semantic(
        self, db: AsyncSession, entity_id: UUID
    ) -> dict[str, str]:
        """Get all semantic knowledge as a {key: value} dict."""
        stmt = select(SemanticMemory.key, SemanticMemory.value).where(
            SemanticMemory.entity_id == entity_id
        )
        result = await db.execute(stmt)
        return {row.key: row.value for row in result.all()}

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def cleanup_expired(
        self, db: AsyncSession, entity_id: UUID, current_tick: int
    ) -> int:
        """Remove episodic memories past their TTL. Returns count removed."""
        stmt = (
            delete(EpisodicMemory)
            .where(
                EpisodicMemory.entity_id == entity_id,
                EpisodicMemory.expires_at_tick <= current_tick,
            )
            .returning(EpisodicMemory.id)
        )
        result = await db.execute(stmt)
        removed = len(result.all())
        if removed:
            logger.debug(
                "Cleaned up %d expired memories for entity %s at tick %d",
                removed, entity_id, current_tick,
            )
        return removed

    # ------------------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------------------

    async def summarize_for_prompt(
        self, db: AsyncSession, entity_id: UUID, limit: int = 15
    ) -> str:
        """Build a text summary of memories for LLM prompt injection.

        Combines the most important memories with the most recent ones
        (deduped), then appends all semantic knowledge.
        """
        # Gather important + recent, dedup by id
        important = await self.get_important_memories(db, entity_id, limit=limit // 2)
        recent = await self.get_recent_memories(db, entity_id, limit=limit)

        seen_ids: set[str] = set()
        combined: list[dict] = []
        for mem in important + recent:
            mid = str(mem["id"])
            if mid not in seen_ids:
                seen_ids.add(mid)
                combined.append(mem)
        combined = combined[:limit]

        # Build episodic section
        lines: list[str] = []
        if combined:
            lines.append("== Recent & Important Memories ==")
            for mem in combined:
                importance_marker = ""
                if mem["importance"] >= 8.0:
                    importance_marker = " [CRITICAL]"
                elif mem["importance"] >= 5.0:
                    importance_marker = " [NOTABLE]"
                loc_str = ""
                if mem.get("location"):
                    loc = mem["location"]
                    loc_str = f" @({loc['x']:.0f},{loc['y']:.0f},{loc['z']:.0f})"
                lines.append(
                    f"  tick {mem['tick']}: {mem['summary']}"
                    f"{importance_marker}{loc_str}"
                )

        # Build semantic section
        knowledge = await self.get_all_semantic(db, entity_id)
        if knowledge:
            lines.append("")
            lines.append("== Known Facts ==")
            for k, v in sorted(knowledge.items()):
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _episodic_to_dict(mem: EpisodicMemory) -> dict:
        """Convert an EpisodicMemory ORM object to a plain dict."""
        return {
            "id": mem.id,
            "entity_id": mem.entity_id,
            "summary": mem.summary,
            "importance": mem.importance,
            "tick": mem.tick,
            "expires_at_tick": mem.expires_at_tick,
            "related_entity_ids": mem.related_entity_ids or [],
            "location": mem.location,
            "memory_type": mem.memory_type,
        }


# Module-level singleton
memory_manager = MemoryManager()
