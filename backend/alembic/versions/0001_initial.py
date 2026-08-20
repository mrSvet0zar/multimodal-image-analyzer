"""initial analyses table

Revision ID: 0001
Revises:
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("uploaded_at", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("sentiment", sa.String(length=128), nullable=False, server_default="neutral"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("objects", sa.JSON(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("processing_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_analyses_uploaded_at", "analyses", ["uploaded_at"])


def downgrade() -> None:
    op.drop_index("ix_analyses_uploaded_at", table_name="analyses")
    op.drop_table("analyses")
