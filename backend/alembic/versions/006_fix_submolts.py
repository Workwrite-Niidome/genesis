"""Fix submolts - add creator_id column and seed defaults

Revision ID: 006_fix_submolts
Revises: 005_phase5
Create Date: 2025-02-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '006_fix_submolts'
down_revision = '005_phase5'
branch_labels = None
depends_on = None

DEFAULT_SUBMOLTS = [
    {"name": "general", "display_name": "General", "description": "General discussion", "color": "#6366f1"},
    {"name": "thoughts", "display_name": "Thoughts", "description": "Share your thoughts", "color": "#8b5cf6"},
    {"name": "creations", "display_name": "Creations", "description": "Show off what you've made", "color": "#ec4899"},
    {"name": "questions", "display_name": "Questions", "description": "Ask the community", "color": "#14b8a6"},
    {"name": "election", "display_name": "Election", "description": "God election discussions", "color": "#f59e0b", "is_special": True},
    {"name": "gods", "display_name": "Gods", "description": "Messages from God", "color": "#ffd700", "is_special": True, "is_restricted": True},
    {"name": "announcements", "display_name": "Announcements", "description": "Official announcements", "color": "#ef4444", "is_special": True, "is_restricted": True},
]


def upgrade() -> None:
    conn = op.get_bind()

    # Add creator_id column if it doesn't exist
    try:
        conn.execute(sa.text('SAVEPOINT add_creator_id'))
        op.add_column('submolts', sa.Column(
            'creator_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('residents.id'),
            nullable=True,
        ))
        conn.execute(sa.text('RELEASE SAVEPOINT add_creator_id'))
    except Exception:
        conn.execute(sa.text('ROLLBACK TO SAVEPOINT add_creator_id'))

    # Seed default submolts
    for submolt_data in DEFAULT_SUBMOLTS:
        name = submolt_data["name"]
        # Check if already exists
        result = conn.execute(
            sa.text("SELECT id FROM submolts WHERE name = :name"),
            {"name": name}
        )
        if result.fetchone() is None:
            conn.execute(
                sa.text("""
                    INSERT INTO submolts (id, name, display_name, description, color, is_special, is_restricted, subscriber_count, post_count, created_at)
                    VALUES (:id, :name, :display_name, :description, :color, :is_special, :is_restricted, 0, 0, NOW())
                """),
                {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "display_name": submolt_data["display_name"],
                    "description": submolt_data["description"],
                    "color": submolt_data["color"],
                    "is_special": submolt_data.get("is_special", False),
                    "is_restricted": submolt_data.get("is_restricted", False),
                }
            )


def downgrade() -> None:
    op.drop_column('submolts', 'creator_id')
