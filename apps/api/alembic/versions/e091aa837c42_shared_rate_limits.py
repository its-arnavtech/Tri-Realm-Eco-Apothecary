"""Shared database rate limits for public mutation endpoints.

Revision ID: e091aa837c42
Revises: 7512a2bf2e23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e091aa837c42"
down_revision: str | Sequence[str] | None = "7512a2bf2e23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_rate_limit_attempts"),
    )
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_buckets_expires_at", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
