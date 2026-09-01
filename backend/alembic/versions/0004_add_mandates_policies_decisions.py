"""Add deterministic mandate, policy, and authorization audit records.

Revision ID: 0004_mandate_policy_audit
Revises: 0003_add_capability_trust
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_mandate_policy_audit"
down_revision = "0003_add_capability_trust"
branch_labels = None
depends_on = None


def upgrade() -> None:
    mandate_status = sa.Enum("DRAFT", "ACTIVE", "EXPIRED", "REVOKED", name="mandate_status")
    authorization_outcome = sa.Enum("ALLOW", "REVIEW", "DENY", name="authorization_outcome")
    op.create_table(
        "mandates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", sa.String(length=255), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("structured_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", mandate_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mandates_organization_id", "mandates", ["organization_id"])
    op.create_index("ix_mandates_agent_id", "mandates", ["agent_id"])
    op.create_table(
        "organization_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_vendors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approval_thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hard_payment_limit", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index(
        "ix_organization_policies_organization_id", "organization_policies", ["organization_id"]
    )
    op.create_table(
        "authorization_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mandate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_name", sa.String(length=255), nullable=False),
        sa.Column("proposed_action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision", authorization_outcome, nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "capability_trust_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("mandate_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.ForeignKeyConstraint(["mandate_id"], ["mandates.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_authorization_decisions_organization_id", "authorization_decisions", ["organization_id"]
    )
    op.create_index("ix_authorization_decisions_agent_id", "authorization_decisions", ["agent_id"])
    op.create_index(
        "ix_authorization_decisions_agent_version_id",
        "authorization_decisions",
        ["agent_version_id"],
    )
    op.create_index(
        "ix_authorization_decisions_mandate_id", "authorization_decisions", ["mandate_id"]
    )


def downgrade() -> None:
    for name in (
        "ix_authorization_decisions_mandate_id",
        "ix_authorization_decisions_agent_version_id",
        "ix_authorization_decisions_agent_id",
        "ix_authorization_decisions_organization_id",
    ):
        op.drop_index(name, table_name="authorization_decisions")
    op.drop_table("authorization_decisions")
    op.drop_index("ix_organization_policies_organization_id", table_name="organization_policies")
    op.drop_table("organization_policies")
    op.drop_index("ix_mandates_agent_id", table_name="mandates")
    op.drop_index("ix_mandates_organization_id", table_name="mandates")
    op.drop_table("mandates")
    sa.Enum(name="authorization_outcome").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="mandate_status").drop(op.get_bind(), checkfirst=True)
