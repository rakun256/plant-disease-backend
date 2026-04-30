"""Add prediction latency fields

Revision ID: c1e2f3a4b5d6
Revises: 9d2b3f4a6c7e
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e2f3a4b5d6'
down_revision: Union[str, Sequence[str], None] = '9d2b3f4a6c7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('predictions', sa.Column('inference_time_ms', sa.Float(), nullable=True))
    op.add_column(
        'predictions',
        sa.Column('is_low_confidence', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('predictions', 'is_low_confidence')
    op.drop_column('predictions', 'inference_time_ms')
