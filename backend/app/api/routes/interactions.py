import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, cast, literal
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.interaction import Interaction

router = APIRouter()


@router.get("")
async def list_interactions(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Interaction)
        .order_by(Interaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    interactions = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "participant_ids": [str(pid) for pid in (i.participant_ids or [])],
            "interaction_type": i.interaction_type,
            "content": i.content,
            "concepts_involved": [str(cid) for cid in (i.concepts_involved or [])],
            "tick_number": i.tick_number,
            "created_at": i.created_at.isoformat(),
        }
        for i in interactions
    ]


@router.get("/ai/{ai_id}")
async def get_ai_interactions(
    ai_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Interaction)
        .where(Interaction.participant_ids.op("@>")(cast(literal([ai_id]), PG_ARRAY(PG_UUID(as_uuid=True)))))
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    interactions = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "participant_ids": [str(pid) for pid in (i.participant_ids or [])],
            "interaction_type": i.interaction_type,
            "content": i.content,
            "concepts_involved": [str(cid) for cid in (i.concepts_involved or [])],
            "tick_number": i.tick_number,
            "created_at": i.created_at.isoformat(),
        }
        for i in interactions
    ]
