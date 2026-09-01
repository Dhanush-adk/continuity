"""Add capability-level trust continuity records.

Revision ID: 0003_add_capability_trust
Revises: 0002_add_agent_description
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_add_capability_trust"
down_revision = "0002_add_agent_description"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum("TRUSTED", "LIMITED", "UNTRUSTED", name="capabilitytruststatus")
    action = sa.Enum("INHERIT", "RESTRICT", "REAUTHORIZE", name="continuityaction")
    op.create_table(
        "capability_trusts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_name", sa.String(length=255), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("continuity_action", action, nullable=False),
        sa.Column("inherited_from_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("autonomy_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "explicitly_reauthorized",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("reauthorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reauthorization_reason", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_version_id", "capability_name"),
    )
    op.create_index(
        "ix_capability_trusts_agent_version_id",
        "capability_trusts",
        ["agent_version_id"],
    )
    op.create_index(
        "ix_capability_trusts_inherited_from_version_id",
        "capability_trusts",
        ["inherited_from_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_capability_trusts_inherited_from_version_id", table_name="capability_trusts")
    op.drop_index("ix_capability_trusts_agent_version_id", table_name="capability_trusts")
    op.drop_table("capability_trusts")
    sa.Enum(name="continuityaction").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="capabilitytruststatus").drop(op.get_bind(), checkfirst=True)
