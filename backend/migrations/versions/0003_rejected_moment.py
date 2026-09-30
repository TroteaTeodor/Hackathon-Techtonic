"""remember the moment a customer said isn't right

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("rejected_moment", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "rejected_moment")
