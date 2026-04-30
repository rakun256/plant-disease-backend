"""Add image quality fields

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('predictions', sa.Column('image_width', sa.Integer(), nullable=True))
    op.add_column('predictions', sa.Column('image_height', sa.Integer(), nullable=True))
    op.add_column('predictions', sa.Column('image_brightness_score', sa.Float(), nullable=True))
    op.add_column('predictions', sa.Column('image_contrast_score', sa.Float(), nullable=True))
    op.add_column('predictions', sa.Column('image_blur_score', sa.Float(), nullable=True))
    op.add_column('predictions', sa.Column('image_quality_score', sa.Float(), nullable=True))
    op.add_column('predictions', sa.Column('is_quality_acceptable', sa.Boolean(), nullable=True))
    op.add_column('predictions', sa.Column('quality_warnings_json', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('predictions', 'quality_warnings_json')
    op.drop_column('predictions', 'is_quality_acceptable')
    op.drop_column('predictions', 'image_quality_score')
    op.drop_column('predictions', 'image_blur_score')
    op.drop_column('predictions', 'image_contrast_score')
    op.drop_column('predictions', 'image_brightness_score')
    op.drop_column('predictions', 'image_height')
    op.drop_column('predictions', 'image_width')
