"""Persist Execution Attempts and Results independently."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("executions", sa.Column("execution_id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("lease_expires_at", sa.String(40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False), sa.Column("idempotency_key", sa.String(), nullable=False, unique=True))
    op.create_index("ix_executions_task_id", "executions", ["task_id"])
    op.create_index("ix_executions_status", "executions", ["status"])
    op.create_table("results", sa.Column("result_id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False, unique=True),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("payload", sa.Text(), nullable=False))

def downgrade():
    raise RuntimeError("Destructive downgrade is unsupported; restore a verified backup")
