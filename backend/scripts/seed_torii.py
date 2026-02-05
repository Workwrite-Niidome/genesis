#!/usr/bin/env python3
"""
seed_torii.py - Generate a massive Itsukushima Shrine-style Torii gate in voxel form.

Usage:
    docker compose exec backend python scripts/seed_torii.py

This script connects to the PostgreSQL database, clears all existing voxel_blocks,
and inserts a complete Ryobu-style Torii gate with water, gold accents, and lanterns.
"""

import math
import random
import uuid
import time
import psycopg2
from psycopg2.extras import execute_values

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_DSN = "postgresql://genesis:genesis@db:5432/genesis"
GOD_UUID = "2328c812-9fd7-4cb1-9f86-39b8a621116f"
STRUCTURE_ID = str(uuid.uuid4())
PLACED_TICK = 0

# Colours (uppercase hex)
VERMILLION = "#CC2200"
DARK_VERMILLION = "#991100"
DARK_WOOD = "#3D1C00"
DARK_STONE = "#444444"
OCEAN_BLUE = "#0D3B66"
GOLD = "#FFD700"
WARM_ORANGE = "#FF8C00"

# Materials
SOLID = "solid"
LIQUID = "liquid"
EMISSIVE = "emissive"


def make_voxel(x, y, z, color, material=SOLID, has_collision=True):
    """Return a tuple ready for bulk insertion."""
    return (
        int(x), int(y), int(z),
        color, material, has_collision,
        GOD_UUID, STRUCTURE_ID, PLACED_TICK,
    )


# ---------------------------------------------------------------------------
# Circular cross-section helpers
# ---------------------------------------------------------------------------
def circle_offsets_4x4():
    """
    A 4x4 circle with corners cut off (12 blocks).
    Offsets are relative to the pillar centre so the pillar occupies
    cx-2..cx+1, cz-2..cz+1  (4 wide) minus the 4 corner blocks.
    """
    offsets = []
    for dx in range(-2, 2):
        for dz in range(-2, 2):
            # cut corners
            if (dx, dz) in [(-2, -2), (-2, 1), (1, -2), (1, 1)]:
                continue
            offsets.append((dx, dz))
    return offsets


CIRCLE_4x4 = circle_offsets_4x4()


# ---------------------------------------------------------------------------
# Generators for each architectural element
# ---------------------------------------------------------------------------
def gen_main_pillars():
    """Main pillars (hashira) - 2 pillars, circular 4x4, y=0..38."""
    voxels = []
    for cx in (-15, 15):
        cz = 0
        for y in range(0, 39):
            for dx, dz in CIRCLE_4x4:
                voxels.append(make_voxel(cx + dx, y, cz + dz, VERMILLION))
    return voxels


def gen_support_pillars():
    """Support pillars (hikae-bashira) - 4 pillars, 2x2, y=0..24."""
    voxels = []
    positions = [
        (-15, -5), (-15, 5),
        (15, -5), (15, 5),
    ]
    for cx, cz in positions:
        for y in range(0, 25):
            for dx in range(0, 2):
                for dz in range(0, 2):
                    voxels.append(make_voxel(cx + dx, y, cz + dz, VERMILLION))
    return voxels


def gen_diagonal_supports():
    """
    Nurizuka - diagonal braces connecting each support pillar to its
    corresponding main pillar.  We draw a simple diagonal line of blocks
    from the top of each support pillar toward the main pillar.
    """
    voxels = []
    # Each support pillar top is at y=24.  Main pillar centre z=0.
    # Support pillars are at z=-5 and z=5.
    pairs = [
        # (support_cx, support_cz, main_cx, main_cz)
        (-15, -5, -15, 0),
        (-15,  5, -15, 0),
        ( 15, -5,  15, 0),
        ( 15,  5,  15, 0),
    ]
    for sx, sz, mx, mz in pairs:
        # Diagonal from (sx, 24, sz) up toward (mx, 28, mz)
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            bx = int(round(sx + (mx - sx) * t))
            by = int(round(24 + (28 - 24) * t))
            bz = int(round(sz + (mz - sz) * t))
            # 2-wide diagonal
            voxels.append(make_voxel(bx, by, bz, VERMILLION))
            voxels.append(make_voxel(bx + 1, by, bz, VERMILLION))
    return voxels


def gen_kasagi():
    """Top beam (kasagi) - x=-22..22, y=39..41, z=-2..2 with curved ends."""
    voxels = []
    for x in range(-22, 23):
        y_base = 39
        # Ends curve upward
        extra = 0
        if x <= -20 or x >= 20:
            extra = 1
        if x <= -21 or x >= 21:
            extra = 2
        for dy in range(0, 3):
            for z in range(-2, 3):
                voxels.append(make_voxel(x, y_base + dy + extra, z, DARK_VERMILLION))
    return voxels


def gen_shimagi():
    """Lower top beam (shimagi) - x=-20..20, y=37..38, z=-2..2."""
    voxels = []
    for x in range(-20, 21):
        for y in range(37, 39):
            for z in range(-2, 3):
                voxels.append(make_voxel(x, y, z, VERMILLION))
    return voxels


def gen_nuki():
    """Connecting beam (nuki) - x=-17..17, y=28..29, z=-1..1."""
    voxels = []
    for x in range(-17, 18):
        for y in range(28, 30):
            for z in range(-1, 2):
                voxels.append(make_voxel(x, y, z, VERMILLION))
    return voxels


def gen_gakuzuka():
    """Nameplate/tablet (gakuzuka) - x=-2..2, y=30..36, z=-1..1."""
    voxels = []
    for x in range(-2, 3):
        for y in range(30, 37):
            for z in range(-1, 2):
                voxels.append(make_voxel(x, y, z, DARK_WOOD))
    return voxels


def gen_base():
    """Stone foundation (nemaki) - 6x6 at y=0..1 under each main pillar."""
    voxels = []
    for cx in (-15, 15):
        cz = 0
        for y in range(0, 2):
            for dx in range(-3, 3):
                for dz in range(-3, 3):
                    voxels.append(make_voxel(cx + dx, y, cz + dz, DARK_STONE))
    return voxels


def gen_water():
    """
    Water surface at y=-1, x=-50..50, z=-40..40.
    Gaps/randomness at the edges for a natural look.
    Inner area (x=-25..25, z=-10..10) is kept solid.
    """
    voxels = []
    random.seed(42)  # reproducible
    for x in range(-50, 51):
        for z in range(-40, 41):
            # Inner zone - always place
            if -25 <= x <= 25 and -10 <= z <= 10:
                voxels.append(make_voxel(x, -1, z, OCEAN_BLUE, LIQUID, False))
                continue
            # Edge zone - random gaps for natural look
            dist_x = max(0, abs(x) - 40)
            dist_z = max(0, abs(z) - 30)
            edge_dist = math.sqrt(dist_x ** 2 + dist_z ** 2)
            # Probability decreases toward the edges
            if edge_dist > 0:
                prob = max(0.0, 1.0 - edge_dist / 12.0)
            else:
                prob = 0.97
            if random.random() < prob:
                voxels.append(make_voxel(x, -1, z, OCEAN_BLUE, LIQUID, False))
    return voxels


def gen_gold_trim():
    """Gold trim on top of kasagi and on nuki beam ends."""
    voxels = []
    # Top of kasagi
    for x in range(-22, 23):
        extra = 0
        if x <= -20 or x >= 20:
            extra = 1
        if x <= -21 or x >= 21:
            extra = 2
        y = 42 + extra
        for z in range(-2, 3):
            voxels.append(make_voxel(x, y, z, GOLD, EMISSIVE))
    # Nuki beam ends - small gold caps
    for x in (-17, 17):
        for y in range(28, 30):
            for z in range(-1, 2):
                voxels.append(make_voxel(x, y, z, GOLD, EMISSIVE))
    return voxels


def gen_lanterns():
    """4 emissive lantern blocks near the pillar bases."""
    voxels = []
    positions = [
        (-13, 1, 3),
        (-13, 1, -3),
        (17, 1, 3),
        (17, 1, -3),
    ]
    for x, y, z in positions:
        voxels.append(make_voxel(x, y, z, WARM_ORANGE, EMISSIVE))
    return voxels


# ---------------------------------------------------------------------------
# De-duplication: keep only one voxel per (x, y, z). Later layers win.
# ---------------------------------------------------------------------------
def deduplicate(voxels):
    """
    Remove duplicate (x, y, z) entries, keeping the LAST occurrence.
    This lets us layer elements on top of each other (e.g. base under pillar).
    """
    seen = {}
    for v in voxels:
        key = (v[0], v[1], v[2])
        seen[key] = v
    return list(seen.values())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Itsukushima Shrine Torii Gate - Voxel Seed Script")
    print("  (Ryobu-style / Ryobu Torii)")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------
    # 1. Generate all voxels
    # ------------------------------------------------------------------
    print("[1/5] Generating voxel data...")
    all_voxels = []

    generators = [
        ("Water surface",       gen_water),
        ("Stone foundations",    gen_base),
        ("Main pillars",        gen_main_pillars),
        ("Support pillars",     gen_support_pillars),
        ("Diagonal supports",   gen_diagonal_supports),
        ("Kasagi (top beam)",   gen_kasagi),
        ("Shimagi (lower beam)",gen_shimagi),
        ("Nuki (cross beam)",   gen_nuki),
        ("Gakuzuka (tablet)",   gen_gakuzuka),
        ("Gold trim",           gen_gold_trim),
        ("Lanterns",            gen_lanterns),
    ]

    counts = {}
    for name, gen_fn in generators:
        voxels = gen_fn()
        counts[name] = len(voxels)
        print(f"    {name}: {len(voxels)} voxels")
        all_voxels.extend(voxels)

    total_before = len(all_voxels)
    all_voxels = deduplicate(all_voxels)
    total_after = len(all_voxels)
    print(f"\n    Total before dedup: {total_before}")
    print(f"    Total after dedup:  {total_after}")
    print(f"    Duplicates removed: {total_before - total_after}")
    print()

    # ------------------------------------------------------------------
    # 2. Connect to database
    # ------------------------------------------------------------------
    print("[2/5] Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()
    print("    Connected.")
    print()

    # ------------------------------------------------------------------
    # 3. Clear existing data
    # ------------------------------------------------------------------
    print("[3/5] Clearing existing voxel_blocks...")
    cur.execute("DELETE FROM voxel_blocks;")
    print(f"    Cleared.")
    print()

    # ------------------------------------------------------------------
    # 4. Bulk insert
    # ------------------------------------------------------------------
    print(f"[4/5] Inserting {total_after} voxels (bulk)...")
    t0 = time.time()

    insert_sql = (
        "INSERT INTO voxel_blocks "
        "(x, y, z, color, material, has_collision, placed_by, structure_id, placed_tick) "
        "VALUES %s"
    )

    # psycopg2 execute_values is very fast for bulk inserts.
    # Template ensures correct casting.
    template = (
        "(%(x)s, %(y)s, %(z)s, %(color)s, %(material)s, "
        "%(has_collision)s, %(placed_by)s::uuid, %(structure_id)s::uuid, %(placed_tick)s)"
    )

    # Convert tuples to dicts for the template
    rows = [
        {
            "x": v[0], "y": v[1], "z": v[2],
            "color": v[3], "material": v[4], "has_collision": v[5],
            "placed_by": v[6], "structure_id": v[7], "placed_tick": v[8],
        }
        for v in all_voxels
    ]

    # Insert in batches of 5000
    BATCH = 5000
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        execute_values(
            cur, insert_sql, batch,
            template=(
                "(%(x)s, %(y)s, %(z)s, %(color)s, %(material)s, "
                "%(has_collision)s, %(placed_by)s::uuid, %(structure_id)s::uuid, %(placed_tick)s)"
            ),
            page_size=BATCH,
        )
        done = min(i + BATCH, len(rows))
        pct = done / len(rows) * 100
        print(f"    ... {done}/{len(rows)} ({pct:.0f}%)")

    conn.commit()
    elapsed = time.time() - t0
    print(f"    Insert completed in {elapsed:.2f}s")
    print()

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    cur.execute("SELECT COUNT(*) FROM voxel_blocks;")
    db_count = cur.fetchone()[0]

    cur.execute(
        "SELECT material, COUNT(*) FROM voxel_blocks GROUP BY material ORDER BY material;"
    )
    mat_counts = cur.fetchall()

    cur.execute(
        "SELECT color, COUNT(*) FROM voxel_blocks GROUP BY color ORDER BY COUNT(*) DESC;"
    )
    color_counts = cur.fetchall()

    cur.execute(
        "SELECT MIN(x), MAX(x), MIN(y), MAX(y), MIN(z), MAX(z) FROM voxel_blocks;"
    )
    bounds = cur.fetchone()

    print("[5/5] Summary")
    print(f"    Total voxels in DB: {db_count}")
    print(f"    Structure ID:       {STRUCTURE_ID}")
    print()
    print("    By material:")
    for mat, cnt in mat_counts:
        print(f"        {mat}: {cnt}")
    print()
    print("    By color:")
    for col, cnt in color_counts:
        print(f"        {col}: {cnt}")
    print()
    print(f"    Bounding box:")
    print(f"        X: {bounds[0]} to {bounds[1]}")
    print(f"        Y: {bounds[2]} to {bounds[3]}")
    print(f"        Z: {bounds[4]} to {bounds[5]}")
    print()
    print("Done! The Itsukushima Torii gate has been placed in the world.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
