"""Add optional agent descriptions.

Revision ID: 0002_add_agent_description
Revises: 0001_initial_identity
Create Date: 2026-09-01
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_add_agent_description"
down_revision = "0001_initial_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("description", sa.String(length=2_000), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "description")
