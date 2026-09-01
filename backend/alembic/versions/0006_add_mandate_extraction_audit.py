"""Persist raw provider extraction and canonicalization issues.

Revision ID: 0006_mandate_canonicalization
Revises: 0005_auth_reviews
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_mandate_canonicalization"
down_revision = "0005_auth_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mandates",
        sa.Column(
            "raw_extraction",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "mandates",
        sa.Column(
            "canonicalization_issues",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("mandates", "raw_extraction", server_default=None)
    op.alter_column("mandates", "canonicalization_issues", server_default=None)


def downgrade() -> None:
    op.drop_column("mandates", "canonicalization_issues")
    op.drop_column("mandates", "raw_extraction")
