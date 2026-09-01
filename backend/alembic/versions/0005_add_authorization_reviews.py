"""Add immutable human review records for REVIEW authorizations.

Revision ID: 0005_auth_reviews
Revises: 0004_mandate_policy_audit
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_auth_reviews"
down_revision = "0004_mandate_policy_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    review_decision = sa.Enum("APPROVE", "DENY", name="human_review_decision")
    op.create_table(
        "authorization_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authorization_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", review_decision, nullable=False),
        sa.Column("reviewer_id", sa.String(length=255), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["authorization_decision_id"], ["authorization_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authorization_decision_id"),
    )
    op.create_index(
        "ix_authorization_reviews_authorization_decision_id",
        "authorization_reviews",
        ["authorization_decision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_authorization_reviews_authorization_decision_id", table_name="authorization_reviews"
    )
    op.drop_table("authorization_reviews")
    sa.Enum(name="human_review_decision").drop(op.get_bind(), checkfirst=True)
