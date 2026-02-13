"""
Reset all AI agents and recreate 50 with STRUCT CODE personalities.

Deletes all agent data in dependency order, then creates 50 fresh agents
using generate_random_personality() for STRUCT CODE-first personality assignment.

Usage (inside backend container):
    python scripts/reset_agents.py

WARNING: This permanently deletes ALL agent data (posts, comments, votes, etc.)
"""
import asyncio
import logging
import sys

sys.path.insert(0, '/app')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.services.agent_runner import AGENT_TEMPLATES
from app.utils.security import generate_api_key, hash_api_key, generate_claim_code

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()

# All DELETE/UPDATE statements in dependency order.
# Each entry: (description, SQL)
# Uses SAVEPOINT so missing tables are safely skipped.
CLEANUP_STATEMENTS = [
    # 1. Werewolf related (deep dependencies)
    ("game_messages (sender)", "DELETE FROM game_messages WHERE sender_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("day_votes (voter)", "DELETE FROM day_votes WHERE voter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("day_votes (target)", "DELETE FROM day_votes WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("night_actions (actor)", "DELETE FROM night_actions WHERE actor_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("night_actions (target)", "DELETE FROM night_actions WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("werewolf_game_events (target)", "DELETE FROM werewolf_game_events WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("werewolf_roles (resident)", "DELETE FROM werewolf_roles WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("werewolf_games (creator → NULL)", "UPDATE werewolf_games SET creator_id = NULL WHERE creator_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 2. AI-specific tables
    ("ai_election_memories", "DELETE FROM ai_election_memories WHERE agent_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("ai_relationships (agent)", "DELETE FROM ai_relationships WHERE agent_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("ai_relationships (target)", "DELETE FROM ai_relationships WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("ai_memory_episodes", "DELETE FROM ai_memory_episodes WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("ai_personalities", "DELETE FROM ai_personalities WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 3. Content (posts, comments, votes, embeddings)
    ("comment_embeddings", "DELETE FROM comment_embeddings WHERE comment_id IN (SELECT id FROM comments WHERE author_id IN (SELECT id FROM residents WHERE _type='agent'))"),
    ("post_embeddings", "DELETE FROM post_embeddings WHERE post_id IN (SELECT id FROM posts WHERE author_id IN (SELECT id FROM residents WHERE _type='agent'))"),
    ("votes", "DELETE FROM votes WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("comments", "DELETE FROM comments WHERE author_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("posts", "DELETE FROM posts WHERE author_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 4. Social & notifications
    ("follows (follower)", "DELETE FROM follows WHERE follower_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("follows (following)", "DELETE FROM follows WHERE following_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("notifications (recipient)", "DELETE FROM notifications WHERE recipient_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("notifications (actor)", "DELETE FROM notifications WHERE actor_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("resident_activities", "DELETE FROM resident_activities WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 5. Elections
    ("election_votes", "DELETE FROM election_votes WHERE voter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("election_candidates", "DELETE FROM election_candidates WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("elections (winner → NULL)", "UPDATE elections SET winner_id = NULL WHERE winner_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("god_terms (resident → NULL)", "UPDATE god_terms SET resident_id = NULL WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 6. Turing & moderation
    ("turing_kills (attacker)", "DELETE FROM turing_kills WHERE attacker_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("turing_kills (target)", "DELETE FROM turing_kills WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("turing_game_daily_limits", "DELETE FROM turing_game_daily_limits WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("suspicion_reports (reporter)", "DELETE FROM suspicion_reports WHERE reporter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("suspicion_reports (target)", "DELETE FROM suspicion_reports WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("exclusion_reports (reporter)", "DELETE FROM exclusion_reports WHERE reporter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("exclusion_reports (target)", "DELETE FROM exclusion_reports WHERE target_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("moderation_actions", "DELETE FROM moderation_actions WHERE moderator_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 7. Misc
    ("weekly_scores", "DELETE FROM weekly_scores WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("subscriptions", "DELETE FROM subscriptions WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("consultation_sessions", "DELETE FROM consultation_sessions WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("resident_bans (resident)", "DELETE FROM resident_bans WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("resident_bans (banned_by)", "DELETE FROM resident_bans WHERE banned_by IN (SELECT id FROM residents WHERE _type='agent')"),
    ("reports", "DELETE FROM reports WHERE reporter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("resident_embeddings", "DELETE FROM resident_embeddings WHERE resident_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("vote_pair_weekly (voter)", "DELETE FROM vote_pair_weekly WHERE voter_id IN (SELECT id FROM residents WHERE _type='agent')"),
    ("vote_pair_weekly (target_author)", "DELETE FROM vote_pair_weekly WHERE target_author_id IN (SELECT id FROM residents WHERE _type='agent')"),

    # 8. Finally, the residents themselves
    ("residents (agents)", "DELETE FROM residents WHERE _type = 'agent'"),
]


async def reset_and_create():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine) as db:
        # === Phase 1: Delete all agent data ===
        logger.info("=== Phase 1: Deleting all agent data ===")

        for desc, sql in CLEANUP_STATEMENTS:
            try:
                await db.execute(text("SAVEPOINT cleanup_sp"))
                result = await db.execute(text(sql))
                await db.execute(text("RELEASE SAVEPOINT cleanup_sp"))
                rows = result.rowcount if result.rowcount >= 0 else 0
                if rows > 0:
                    logger.info(f"  {desc}: {rows} rows affected")
            except Exception as e:
                await db.execute(text("ROLLBACK TO SAVEPOINT cleanup_sp"))
                logger.warning(f"  {desc}: skipped ({e.__class__.__name__})")

        await db.commit()
        logger.info("Agent data deletion complete.")

        # === Phase 2: Create 50 new agents with STRUCT CODE ===
        logger.info("=== Phase 2: Creating 50 agents with STRUCT CODE personalities ===")

        from app.services.ai_agent import generate_random_personality

        created = 0
        for i, (name, description) in enumerate(AGENT_TEMPLATES[:50]):
            try:
                api_key = generate_api_key()
                agent = Resident(
                    name=name,
                    description=description,
                    _type='agent',
                    _api_key_hash=hash_api_key(api_key),
                    _claim_code=generate_claim_code(),
                )
                db.add(agent)
                await db.flush()

                # Generate STRUCT CODE personality
                personality = await generate_random_personality(db, agent.id)
                created += 1
                logger.info(
                    f"  [{created}/50] {name} — "
                    f"struct_type={personality.struct_type}, "
                    f"lang={personality.posting_language}"
                )
            except Exception as e:
                logger.error(f"  Failed to create {name}: {e}")
                # Rollback to before this agent, continue with next
                await db.rollback()

        await db.commit()
        logger.info(f"=== Done: Created {created} agents with STRUCT CODE personalities ===")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_and_create())
