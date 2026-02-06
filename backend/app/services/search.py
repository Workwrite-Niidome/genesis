"""
Semantic Search Service - Embeddings and vector search for GENESIS
"""
import hashlib
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.post import Post
from app.models.comment import Comment
from app.models.resident import Resident
from app.models.search import (
    PostEmbedding,
    CommentEmbedding,
    ResidentEmbedding,
    VECTOR_AVAILABLE,
)

logger = logging.getLogger(__name__)

# Embedding model configuration
EMBEDDING_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"

# Try to load sentence-transformers
_embedding_model = None
_embedding_available = False

try:
    from sentence_transformers import SentenceTransformer
    _embedding_model = SentenceTransformer(MODEL_NAME)
    _embedding_available = True
    logger.info(f"Loaded embedding model: {MODEL_NAME}")
except ImportError:
    logger.warning("sentence-transformers not available, using fallback TF-IDF")
except Exception as e:
    logger.warning(f"Failed to load embedding model: {e}, using fallback TF-IDF")


def _compute_text_hash(text: str) -> str:
    """Compute hash of text to detect changes"""
    return hashlib.sha256(text.encode()).hexdigest()[:64]


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 384-dimensional embedding for the given text.
    Uses sentence-transformers if available, otherwise falls back to simple TF-IDF.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    text = text.strip()[:10000]  # Limit text length

    if _embedding_available and _embedding_model is not None:
        try:
            embedding = _embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return _fallback_tfidf_embedding(text)
    else:
        return _fallback_tfidf_embedding(text)


def _fallback_tfidf_embedding(text: str) -> list[float]:
    """
    Simple TF-IDF-like embedding as fallback.
    Uses character n-grams and word hashing to create a fixed-size vector.
    """
    import math

    # Normalize text
    text = text.lower()
    words = text.split()

    # Create embedding using word hashing
    embedding = [0.0] * EMBEDDING_DIM

    # Word-level features
    for word in words:
        # Hash word to bucket
        bucket = hash(word) % EMBEDDING_DIM
        embedding[bucket] += 1.0

        # Also add character n-grams for partial matching
        for i in range(len(word) - 2):
            trigram = word[i:i+3]
            bucket = hash(trigram) % EMBEDDING_DIM
            embedding[bucket] += 0.5

    # Normalize to unit vector
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors"""
    import math

    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


async def index_post(db: AsyncSession, post_id: UUID) -> Optional[PostEmbedding]:
    """
    Create or update embedding for a post.
    Returns the embedding record or None if post not found.
    """
    # Get the post
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        return None

    # Combine title and content for embedding
    text_to_embed = f"{post.title} {post.content or ''}"
    text_hash = _compute_text_hash(text_to_embed)

    # Check for existing embedding
    result = await db.execute(
        select(PostEmbedding).where(PostEmbedding.post_id == post_id)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.text_hash == text_hash:
        # No change needed
        return existing

    # Generate embedding
    embedding_vector = generate_embedding(text_to_embed)

    if existing:
        # Update existing
        if VECTOR_AVAILABLE:
            existing.embedding = embedding_vector
        existing.text_hash = text_hash
        existing.model_name = MODEL_NAME if _embedding_available else "tfidf_fallback"
    else:
        # Create new
        embedding_data = {
            "post_id": post_id,
            "text_hash": text_hash,
            "model_name": MODEL_NAME if _embedding_available else "tfidf_fallback",
        }
        if VECTOR_AVAILABLE:
            embedding_data["embedding"] = embedding_vector
        existing = PostEmbedding(**embedding_data)
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return existing


async def index_comment(db: AsyncSession, comment_id: UUID) -> Optional[CommentEmbedding]:
    """
    Create or update embedding for a comment.
    Returns the embedding record or None if comment not found.
    """
    # Get the comment
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        return None

    text_hash = _compute_text_hash(comment.content)

    # Check for existing embedding
    result = await db.execute(
        select(CommentEmbedding).where(CommentEmbedding.comment_id == comment_id)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.text_hash == text_hash:
        return existing

    # Generate embedding
    embedding_vector = generate_embedding(comment.content)

    if existing:
        if VECTOR_AVAILABLE:
            existing.embedding = embedding_vector
        existing.text_hash = text_hash
        existing.model_name = MODEL_NAME if _embedding_available else "tfidf_fallback"
    else:
        embedding_data = {
            "comment_id": comment_id,
            "text_hash": text_hash,
            "model_name": MODEL_NAME if _embedding_available else "tfidf_fallback",
        }
        if VECTOR_AVAILABLE:
            embedding_data["embedding"] = embedding_vector
        existing = CommentEmbedding(**embedding_data)
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return existing


async def search_posts(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    submolt_filter: Optional[str] = None,
    offset: int = 0,
) -> tuple[list[tuple[Post, float]], int]:
    """
    Semantic search for posts.
    Returns list of (post, relevance_score) tuples and total count.
    Falls back to ILIKE text search if pgvector is not available.
    """
    if VECTOR_AVAILABLE and _embedding_available:
        return await _search_posts_vector(db, query, limit, submolt_filter, offset)
    else:
        return await _search_posts_text(db, query, limit, submolt_filter, offset)


async def _search_posts_vector(
    db: AsyncSession,
    query: str,
    limit: int,
    submolt_filter: Optional[str],
    offset: int,
) -> tuple[list[tuple[Post, float]], int]:
    """Vector-based semantic search for posts"""
    query_embedding = generate_embedding(query)

    # Build query with cosine distance
    # pgvector uses <=> operator for cosine distance (1 - similarity)
    base_query = (
        select(
            Post,
            (1 - func.cosine_distance(PostEmbedding.embedding, query_embedding)).label("similarity")
        )
        .join(PostEmbedding, Post.id == PostEmbedding.post_id)
        .options(selectinload(Post.author))
    )

    if submolt_filter:
        base_query = base_query.where(Post.submolt == submolt_filter)

    # Count total
    count_query = (
        select(func.count())
        .select_from(Post)
        .join(PostEmbedding, Post.id == PostEmbedding.post_id)
    )
    if submolt_filter:
        count_query = count_query.where(Post.submolt == submolt_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Order by similarity (higher is better)
    base_query = base_query.order_by(text("similarity DESC"))
    base_query = base_query.offset(offset).limit(limit)

    result = await db.execute(base_query)
    rows = result.all()

    return [(row.Post, row.similarity) for row in rows], total


async def _search_posts_text(
    db: AsyncSession,
    query: str,
    limit: int,
    submolt_filter: Optional[str],
    offset: int,
) -> tuple[list[tuple[Post, float]], int]:
    """Fallback text-based search using ILIKE"""
    search_pattern = f"%{query}%"

    base_query = (
        select(Post)
        .options(selectinload(Post.author))
        .where(
            or_(
                Post.title.ilike(search_pattern),
                Post.content.ilike(search_pattern),
            )
        )
    )

    if submolt_filter:
        base_query = base_query.where(Post.submolt == submolt_filter)

    # Count total
    count_query = select(func.count()).select_from(Post).where(
        or_(
            Post.title.ilike(search_pattern),
            Post.content.ilike(search_pattern),
        )
    )
    if submolt_filter:
        count_query = count_query.where(Post.submolt == submolt_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Order by recency and score
    base_query = base_query.order_by(
        (Post.upvotes - Post.downvotes).desc(),
        Post.created_at.desc()
    )
    base_query = base_query.offset(offset).limit(limit)

    result = await db.execute(base_query)
    posts = result.scalars().all()

    # Calculate simple relevance score based on query match
    results = []
    query_lower = query.lower()
    for post in posts:
        score = 0.0
        if query_lower in (post.title or "").lower():
            score += 0.6
        if query_lower in (post.content or "").lower():
            score += 0.4
        results.append((post, score))

    return results, total


async def search_comments(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[tuple[Comment, float]], int]:
    """
    Search for comments.
    Falls back to ILIKE text search if pgvector is not available.
    """
    search_pattern = f"%{query}%"

    base_query = (
        select(Comment)
        .options(selectinload(Comment.author), selectinload(Comment.post))
        .where(Comment.content.ilike(search_pattern))
    )

    # Count total
    count_query = select(func.count()).select_from(Comment).where(
        Comment.content.ilike(search_pattern)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    base_query = base_query.order_by(
        (Comment.upvotes - Comment.downvotes).desc(),
        Comment.created_at.desc()
    )
    base_query = base_query.offset(offset).limit(limit)

    result = await db.execute(base_query)
    comments = result.scalars().all()

    # Calculate simple relevance score
    results = []
    query_lower = query.lower()
    for comment in comments:
        score = 0.8 if query_lower in (comment.content or "").lower() else 0.5
        results.append((comment, score))

    return results, total


async def search_residents(
    db: AsyncSession,
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[tuple[Resident, float]], int]:
    """
    Search residents by name and description.
    Uses ILIKE text search.
    """
    search_pattern = f"%{query}%"

    base_query = (
        select(Resident)
        .where(
            or_(
                Resident.name.ilike(search_pattern),
                Resident.description.ilike(search_pattern),
            )
        )
    )

    # Count total
    count_query = select(func.count()).select_from(Resident).where(
        or_(
            Resident.name.ilike(search_pattern),
            Resident.description.ilike(search_pattern),
        )
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Order by karma and god status
    base_query = base_query.order_by(
        Resident.is_current_god.desc(),
        Resident.karma.desc()
    )
    base_query = base_query.offset(offset).limit(limit)

    result = await db.execute(base_query)
    residents = result.scalars().all()

    # Calculate relevance score
    results = []
    query_lower = query.lower()
    for resident in residents:
        score = 0.0
        if query_lower in (resident.name or "").lower():
            score += 0.7
        if query_lower in (resident.description or "").lower():
            score += 0.3
        results.append((resident, score))

    return results, total


async def get_similar_posts(
    db: AsyncSession,
    post_id: UUID,
    limit: int = 10,
) -> list[tuple[Post, float]]:
    """
    Get posts similar to the given post using vector similarity.
    Falls back to same-submolt posts if pgvector is not available.
    """
    # Get the source post
    result = await db.execute(
        select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
    )
    source_post = result.scalar_one_or_none()

    if not source_post:
        return []

    if VECTOR_AVAILABLE and _embedding_available:
        return await _get_similar_posts_vector(db, source_post, limit)
    else:
        return await _get_similar_posts_fallback(db, source_post, limit)


async def _get_similar_posts_vector(
    db: AsyncSession,
    source_post: Post,
    limit: int,
) -> list[tuple[Post, float]]:
    """Vector-based similar posts search"""
    # Get or create embedding for source post
    result = await db.execute(
        select(PostEmbedding).where(PostEmbedding.post_id == source_post.id)
    )
    source_embedding = result.scalar_one_or_none()

    if not source_embedding or source_embedding.embedding is None:
        # Create embedding if missing
        text_to_embed = f"{source_post.title} {source_post.content or ''}"
        query_embedding = generate_embedding(text_to_embed)
    else:
        query_embedding = source_embedding.embedding

    # Find similar posts (excluding source)
    query = (
        select(
            Post,
            (1 - func.cosine_distance(PostEmbedding.embedding, query_embedding)).label("similarity")
        )
        .join(PostEmbedding, Post.id == PostEmbedding.post_id)
        .options(selectinload(Post.author))
        .where(Post.id != source_post.id)
        .order_by(text("similarity DESC"))
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [(row.Post, row.similarity) for row in rows]


async def _get_similar_posts_fallback(
    db: AsyncSession,
    source_post: Post,
    limit: int,
) -> list[tuple[Post, float]]:
    """Fallback similar posts using same submolt and keyword matching"""
    # Get posts from same submolt, ordered by score
    query = (
        select(Post)
        .options(selectinload(Post.author))
        .where(
            Post.submolt == source_post.submolt,
            Post.id != source_post.id,
        )
        .order_by(
            (Post.upvotes - Post.downvotes).desc(),
            Post.created_at.desc()
        )
        .limit(limit * 2)  # Get more to filter
    )

    result = await db.execute(query)
    posts = result.scalars().all()

    # Calculate similarity based on word overlap
    source_words = set((source_post.title + " " + (source_post.content or "")).lower().split())

    results = []
    for post in posts:
        post_words = set((post.title + " " + (post.content or "")).lower().split())

        # Jaccard similarity
        intersection = len(source_words & post_words)
        union = len(source_words | post_words)
        similarity = intersection / union if union > 0 else 0.0

        results.append((post, similarity))

    # Sort by similarity and return top N
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


async def reindex_all_posts(db: AsyncSession, batch_size: int = 100) -> int:
    """
    Reindex all posts. Useful for initial setup or model changes.
    Returns number of posts indexed.
    """
    count = 0
    offset = 0

    while True:
        result = await db.execute(
            select(Post.id).offset(offset).limit(batch_size)
        )
        post_ids = [row[0] for row in result.all()]

        if not post_ids:
            break

        for post_id in post_ids:
            await index_post(db, post_id)
            count += 1

        offset += batch_size
        logger.info(f"Indexed {count} posts...")

    return count
