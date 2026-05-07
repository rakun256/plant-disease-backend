"""Add keep alive table

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "keep_alive",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("counter", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("pinged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.execute(
        sa.text(
            "INSERT INTO keep_alive (id, counter, pinged_at) VALUES (1, 0, now())"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("keep_alive")
