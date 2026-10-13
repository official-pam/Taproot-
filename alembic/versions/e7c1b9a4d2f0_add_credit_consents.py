"""add credit_consents (Taproot loan-sharing consent)

Revision ID: e7c1b9a4d2f0
Revises: d4b8e3a2f1c7
Create Date: 2026-10-13 21:45:00

Additive only. A second, separate consent recorded when a trader asks for a
loan and agrees to share their business record with the partner bank. Rows
are never deleted; revoking sets revoked_at.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c1b9a4d2f0"
down_revision: Union[str, None] = "d4b8e3a2f1c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credit_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("wa_id", sa.Text(), nullable=False),
        sa.Column("partner", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["wa_id"], ["users.wa_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_consents_wa_id", "credit_consents", ["wa_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_consents_wa_id", table_name="credit_consents")
    op.drop_table("credit_consents")
