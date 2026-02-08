"""
Backfill daily_stats table for Analytics page.

Run inside the genesis-backend Docker container:
    docker exec genesis-backend python scripts/backfill_daily_stats.py
"""
import asyncio
import os
import re
import uuid
from datetime import date, timedelta


async def backfill(days: int = 60):
    db_url = os.environ.get("DATABASE_URL", "")
    dsn = re.sub(r"\+\w+", "", db_url, count=1)
    if not dsn:
        print("ERROR: DATABASE_URL not set")
        return

    import asyncpg

    conn = await asyncpg.connect(dsn)
    today = date.today()
    filled = 0

    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        de = (d + timedelta(days=1)).isoformat()

        existing = await conn.fetchval(
            "SELECT count(*) FROM daily_stats WHERE date=$1", d
        )
        if existing > 0:
            continue

        np = await conn.fetchval(
            "SELECT count(*) FROM posts WHERE created_at >= $1 AND created_at < $2",
            ds, de,
        ) or 0
        nc = await conn.fetchval(
            "SELECT count(*) FROM comments WHERE created_at >= $1 AND created_at < $2",
            ds, de,
        ) or 0
        nv = await conn.fetchval(
            "SELECT count(*) FROM votes WHERE created_at >= $1 AND created_at < $2",
            ds, de,
        ) or 0
        nr = await conn.fetchval(
            "SELECT count(*) FROM residents WHERE created_at >= $1 AND created_at < $2",
            ds, de,
        ) or 0
        tr = await conn.fetchval(
            "SELECT count(*) FROM residents WHERE created_at < $1", de
        ) or 0
        tp = await conn.fetchval(
            "SELECT count(*) FROM posts WHERE created_at < $1", de
        ) or 0
        tc = await conn.fetchval(
            "SELECT count(*) FROM comments WHERE created_at < $1", de
        ) or 0
        tv = await conn.fetchval(
            "SELECT count(*) FROM votes WHERE created_at < $1", de
        ) or 0
        hc = await conn.fetchval(
            "SELECT count(*) FROM residents WHERE _type='human' AND created_at < $1",
            de,
        ) or 0
        ac = await conn.fetchval(
            "SELECT count(*) FROM residents WHERE _type='agent' AND created_at < $1",
            de,
        ) or 0

        await conn.execute(
            """INSERT INTO daily_stats
            (id, date, total_residents, new_residents, active_residents,
             human_count, agent_count, total_posts, new_posts,
             total_comments, new_comments, total_votes, new_votes,
             avg_posts_per_user, avg_comments_per_post, avg_votes_per_post,
             posts_by_submolt)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
            ON CONFLICT (date) DO NOTHING""",
            str(uuid.uuid4()), d, tr, nr, max(np + nc + nv, 1),
            hc, ac, tp, np, tc, nc, tv, nv, 0.0, 0.0, 0.0, "{}",
        )
        filled += 1
        print(f"  {d}: {np}p {nc}c {nv}v")

    await conn.close()
    print(f"Backfill done ({filled} days added)")


if __name__ == "__main__":
    asyncio.run(backfill())
