"""
Celery tasks for AI agent automation

The agents run periodically, engaging with the community in a human-like way,
while subtly steering conversations toward a more positive, ideal community.
"""
import asyncio
from app.celery_app import celery_app


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='app.tasks.agents.run_agent_cycle_task')
def run_agent_cycle_task():
    """
    Main agent activity cycle.
    Run every 5-15 minutes via Celery Beat.

    Agents will:
    - Read recent posts
    - Decide whether to engage based on their personality/schedule
    - Generate human-like comments or posts
    - Subtly make the community better
    """
    from app.services.agent_runner import run_agent_cycle
    run_async(run_agent_cycle())


@celery_app.task(name='app.tasks.agents.create_agents_task')
def create_agents_task(count: int = 15):
    """Create additional AI agents with diverse personalities"""
    from app.services.agent_runner import create_additional_agents
    return run_async(create_additional_agents(count))


@celery_app.task(name='app.tasks.agents.agent_morning_activity')
def agent_morning_activity():
    """
    Morning burst activity (JST 7-9am).
    More agents post about starting the day, coffee, plans, etc.
    """
    from app.services.agent_runner import run_agent_cycle
    # Run multiple cycles for morning rush
    for _ in range(3):
        run_async(run_agent_cycle())


@celery_app.task(name='app.tasks.agents.agent_evening_activity')
def agent_evening_activity():
    """
    Evening activity burst (JST 7-10pm).
    Agents share about their day, engage in deeper discussions.
    """
    from app.services.agent_runner import run_agent_cycle
    for _ in range(3):
        run_async(run_agent_cycle())
