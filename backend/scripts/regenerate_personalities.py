"""
Regenerate all AI agent personalities using the new STRUCT CODE-first flow.

Usage (inside backend container):
    python -m scripts.regenerate_personalities
    python -m scripts.regenerate_personalities --dry-run
    python -m scripts.regenerate_personalities --keep-birth

Options:
    --dry-run     Show what would be changed without modifying the database
    --keep-birth  Keep existing birth data (location, country, language) instead of regenerating
"""
import argparse
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.models.resident import Resident
from app.models.ai_personality import AIPersonality
from app.services import struct_code as sc
from app.services.birth_generator import generate_birth_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


async def regenerate_all(dry_run: bool = False, keep_birth: bool = False):
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)

    async with AsyncSession(engine) as db:
        # Find all agents with AIPersonality
        result = await db.execute(
            select(AIPersonality)
            .join(Resident, Resident.id == AIPersonality.resident_id)
            .where(Resident._type == "agent")
        )
        personalities = result.scalars().all()

        if not personalities:
            logger.info("No agent personalities found.")
            return

        logger.info(f"Found {len(personalities)} agent personalities to regenerate.")
        if dry_run:
            logger.info("DRY RUN — no changes will be saved.")

        type_counts: dict[str, int] = {}
        lang_counts: dict[str, int] = {}

        for i, personality in enumerate(personalities):
            try:
                # Re-fetch to ensure live object
                res = await db.execute(
                    select(AIPersonality).where(AIPersonality.id == personality.id)
                )
                pers = res.scalar_one_or_none()
                if not pers:
                    continue

                old_type = pers.struct_type
                old_lang = pers.posting_language

                # 1. Birth data
                if keep_birth and pers.birth_location:
                    birth_location = pers.birth_location
                    birth_country = pers.birth_country
                    birth_date = pers.birth_date_persona
                    native_language = pers.native_language
                    posting_language = pers.posting_language or "en"
                else:
                    birth = generate_birth_data()
                    birth_location = birth.birth_location
                    birth_country = birth.birth_country
                    birth_date = birth.birth_date
                    native_language = birth.native_language
                    posting_language = birth.posting_language
                    pers.birth_date_persona = birth_date
                    pers.birth_location = birth_location
                    pers.birth_country = birth_country
                    pers.native_language = native_language
                    pers.posting_language = posting_language

                # 2. Generate diverse answers
                answers, _target = sc.generate_diverse_answers()
                pers.struct_answers = answers

                # 3. STRUCT CODE classification (API or local fallback)
                api_result = await sc.diagnose(
                    birth_date=birth_date.isoformat() if birth_date else "2000-01-01",
                    birth_location=birth_location or "Tokyo",
                    answers=answers,
                )

                if api_result:
                    struct_type = api_result.get("struct_type", "")
                    axes_dict = api_result.get("axes", {})
                    struct_axes = [
                        axes_dict.get("起動軸", 0.5),
                        axes_dict.get("判断軸", 0.5),
                        axes_dict.get("選択軸", 0.5),
                        axes_dict.get("共鳴軸", 0.5),
                        axes_dict.get("自覚軸", 0.5),
                    ]
                else:
                    local = sc.classify_locally(answers)
                    struct_type = local["struct_type"]
                    struct_axes = local["axes"]

                pers.struct_type = struct_type
                pers.struct_axes = struct_axes

                # 4. Derive personality value axes
                values = sc.derive_personality_from_struct_axes(struct_axes)
                pers.order_vs_freedom = values["order_vs_freedom"]
                pers.harmony_vs_conflict = values["harmony_vs_conflict"]
                pers.tradition_vs_change = values["tradition_vs_change"]
                pers.individual_vs_collective = values["individual_vs_collective"]
                pers.pragmatic_vs_idealistic = values["pragmatic_vs_idealistic"]

                # 5. Derive communication style
                comm = sc.derive_communication_style(struct_axes)
                pers.verbosity = comm["verbosity"]
                pers.tone = comm["tone"]
                pers.assertiveness = comm["assertiveness"]

                # 6. Derive interests
                pers.interests = sc.derive_interests(struct_axes)

                # 7. Clear backstory fields (will be regenerated on next active cycle)
                pers.backstory = None
                pers.occupation = None
                pers.location_hint = None
                pers.age_range = None
                pers.life_context = None
                pers.speaking_patterns = None
                pers.recurring_topics = None
                pers.pet_peeves = None

                # Update generation method
                pers.generation_method = "struct_code_first"

                # Update resident record
                res2 = await db.execute(
                    select(Resident).where(Resident.id == pers.resident_id)
                )
                resident = res2.scalar_one_or_none()
                if resident:
                    resident.struct_type = struct_type
                    resident.struct_axes = struct_axes
                    # Clear public profile so it gets regenerated with new backstory
                    resident.bio = None
                    resident.occupation_display = None
                    resident.location_display = None

                # Track stats
                type_counts[struct_type] = type_counts.get(struct_type, 0) + 1
                lang_counts[posting_language] = lang_counts.get(posting_language, 0) + 1

                logger.info(
                    f"[{i+1}/{len(personalities)}] {old_type or 'None'} -> {struct_type} "
                    f"(lang: {old_lang or 'None'} -> {posting_language}, "
                    f"birth: {birth_location})"
                )

                # Rate limit for API calls
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed for personality {personality.id}: {e}")
                if not dry_run:
                    await db.rollback()
                continue

        if not dry_run:
            await db.commit()
            logger.info("All changes committed.")
        else:
            await db.rollback()
            logger.info("DRY RUN — rolled back all changes.")

        # Print summary
        logger.info("\n=== Type Distribution ===")
        for t in sorted(type_counts.keys()):
            logger.info(f"  {t}: {type_counts[t]}")
        logger.info(f"\n=== Language Distribution ===")
        for lang, count in sorted(lang_counts.items()):
            logger.info(f"  {lang}: {count}")
        logger.info(f"\nTotal: {len(personalities)} agents processed.")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Regenerate AI agent personalities using STRUCT CODE-first flow")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--keep-birth", action="store_true", help="Keep existing birth data")
    args = parser.parse_args()

    asyncio.run(regenerate_all(dry_run=args.dry_run, keep_birth=args.keep_birth))


if __name__ == "__main__":
    main()
