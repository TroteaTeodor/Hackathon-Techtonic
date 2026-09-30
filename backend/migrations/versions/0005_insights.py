"""intervention call-to-action label and personalised-wording flag

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("interventions", sa.Column("cta", sa.String(60), nullable=True))
    op.add_column("interventions", sa.Column("personalized", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("interventions", "personalized")
    op.drop_column("interventions", "cta")
