"""Initial task, event and configuration storage."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("tasks", sa.Column("task_id", sa.String(36), primary_key=True),
                    sa.Column("revision", sa.Integer(), nullable=False),
                    sa.Column("payload", sa.Text(), nullable=False))
    op.create_table("events", sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
                    sa.Column("event_id", sa.String(36), nullable=False, unique=True),
                    sa.Column("correlation_id", sa.String(36), nullable=False),
                    sa.Column("payload", sa.Text(), nullable=False))
    op.create_index("ix_events_correlation_id", "events", ["correlation_id"])
    op.create_table("configuration", sa.Column("key", sa.String(), primary_key=True),
                    sa.Column("payload", sa.Text(), nullable=False))


def downgrade():
    raise RuntimeError("Destructive downgrade is unsupported; restore a verified backup")
