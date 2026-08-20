"""add media_type / video_path / transcript for video storage + audio

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("media_type", sa.String(length=16), nullable=False, server_default="image"),
    )
    op.add_column("analyses", sa.Column("video_path", sa.String(length=1024), nullable=True))
    op.add_column("analyses", sa.Column("transcript", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "transcript")
    op.drop_column("analyses", "video_path")
    op.drop_column("analyses", "media_type")
