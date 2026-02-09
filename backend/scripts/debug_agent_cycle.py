"""Debug agent cycle — instrument every step to find why agents produce no posts."""
import sys
sys.path.insert(0, '/app')
import asyncio
import random


async def debug_cycle():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import select, func
    from app.models.resident import Resident
    from app.models.post import Post
    from app.config import get_settings
    from app.services.agent_runner import (
        get_agent_profile, should_agent_act, get_recent_context, generate_text
    )

    s = get_settings()
    print("=== Agent Cycle Debug ===")
    print("DB URL: " + s.database_url[:50] + "...")
    print("Ollama host: " + str(s.OLLAMA_HOST))
    print("Ollama model: " + str(s.OLLAMA_MODEL))

    engine = create_async_engine(s.database_url, pool_pre_ping=True)
    async with AsyncSession(engine) as db:
        # Count agents
        res = await db.execute(select(Resident).where(Resident._type == 'agent'))
        agents = res.scalars().all()
        print("Total agents: " + str(len(agents)))

        if not agents:
            print("ERROR: No agents found!")
            await engine.dispose()
            return

        # Get context
        ctx = await get_recent_context(db)
        print("Recent context posts: " + str(len(ctx)))
        if ctx:
            print("Latest post: " + ctx[0].get('title', '?')[:50])
        else:
            print("WARNING: No recent posts for context!")

        # Count active agents
        active_agents = []
        activity_counts = {}
        from datetime import datetime
        print("Current UTC hour: " + str(datetime.utcnow().hour))

        for a in agents:
            p = get_agent_profile(a)
            activity_key = p['activity_key']
            if activity_key not in activity_counts:
                activity_counts[activity_key] = {'total': 0, 'active': 0}
            activity_counts[activity_key]['total'] += 1
            if should_agent_act(a, p):
                activity_counts[activity_key]['active'] += 1
                active_agents.append((a, p))

        print("Active agents this cycle: " + str(len(active_agents)))
        for key, counts in sorted(activity_counts.items()):
            print("  " + key + ": " + str(counts['active']) + "/" + str(counts['total']))

        # Test Ollama
        print("--- Testing Ollama generation ---")
        try:
            txt = await generate_text('Say hello in one sentence.', 'You are a friendly person.')
            if txt:
                print("Ollama OK: " + repr(txt[:100]))
            else:
                print("Ollama returned None/empty!")
        except Exception as e:
            print("Ollama error: " + str(e))

        # Count posts
        post_count = await db.execute(select(func.count()).select_from(Post))
        print("Total posts in DB: " + str(post_count.scalar()))

    await engine.dispose()
    print("=== Debug Complete ===")


if __name__ == "__main__":
    asyncio.run(debug_cycle())
