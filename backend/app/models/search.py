"""
Search System - Vector embeddings for semantic search
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Note: pgvector extension must be installed in PostgreSQL
# CREATE EXTENSION IF NOT EXISTS vector;
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    Vector = None


class PostEmbedding(Base):
    """Vector embeddings for posts (semantic search)"""
    __tablename__ = "post_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Embedding vector (1536 dimensions for OpenAI ada-002, 384 for all-MiniLM-L6-v2)
    # Using 384 for local models compatibility
    if VECTOR_AVAILABLE:
        embedding: Mapped[list] = mapped_column(Vector(384), nullable=True)
    else:
        embedding = None  # Fallback when pgvector not available

    # Metadata
    model_name: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2")
    text_hash: Mapped[str] = mapped_column(String(64))  # To detect if re-embedding needed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("Post", backref="embedding")

    def __repr__(self) -> str:
        return f"<PostEmbedding for post {self.post_id}>"


class CommentEmbedding(Base):
    """Vector embeddings for comments"""
    __tablename__ = "comment_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    if VECTOR_AVAILABLE:
        embedding: Mapped[list] = mapped_column(Vector(384), nullable=True)
    else:
        embedding = None

    model_name: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2")
    text_hash: Mapped[str] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    comment = relationship("Comment", backref="embedding")

    def __repr__(self) -> str:
        return f"<CommentEmbedding for comment {self.comment_id}>"


class ResidentEmbedding(Base):
    """Vector embeddings for resident profiles"""
    __tablename__ = "resident_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    if VECTOR_AVAILABLE:
        embedding: Mapped[list] = mapped_column(Vector(384), nullable=True)
    else:
        embedding = None

    model_name: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2")
    text_hash: Mapped[str] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resident = relationship("Resident", backref="embedding")

    def __repr__(self) -> str:
        return f"<ResidentEmbedding for resident {self.resident_id}>"
