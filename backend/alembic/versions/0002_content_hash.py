"""add content_hash / detail_level / language for image dedup

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("analyses", sa.Column("detail_level", sa.String(length=32), nullable=True))
    op.add_column("analyses", sa.Column("language", sa.String(length=16), nullable=True))
    op.create_index("ix_analyses_content_hash", "analyses", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_analyses_content_hash", table_name="analyses")
    op.drop_column("analyses", "language")
    op.drop_column("analyses", "detail_level")
    op.drop_column("analyses", "content_hash")
