"""Persist exact-action approvals, handoffs and Target-local context."""
from alembic import op
import sqlalchemy as sa
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("approvals", sa.Column("approval_id",sa.String(36),primary_key=True),sa.Column("action_digest",sa.String(64),nullable=False),sa.Column("decision",sa.String(16),nullable=False),sa.Column("payload",sa.Text(),nullable=False))
    op.create_table("handoffs", sa.Column("handoff_id",sa.String(36),primary_key=True),sa.Column("task_id",sa.String(36),nullable=False),sa.Column("execution_id",sa.String(36),nullable=False),sa.Column("payload_digest",sa.String(64),nullable=False),sa.Column("payload",sa.Text(),nullable=False))
    op.create_index("ix_handoffs_task_id","handoffs",["task_id"])
    op.create_table("project_context",sa.Column("key",sa.String(),primary_key=True),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("payload",sa.Text(),nullable=False))
def downgrade():
    raise RuntimeError("Destructive downgrade is unsupported; restore a verified backup")
