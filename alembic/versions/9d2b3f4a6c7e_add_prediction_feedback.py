"""Add prediction feedback

Revision ID: 9d2b3f4a6c7e
Revises: 54a3c8cd969c
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d2b3f4a6c7e'
down_revision: Union[str, Sequence[str], None] = '54a3c8cd969c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('prediction_feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prediction_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('corrected_class', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'prediction_id', name='uq_prediction_feedback_user_prediction')
    )
    op.create_index(op.f('ix_prediction_feedback_id'), 'prediction_feedback', ['id'], unique=False)
    op.create_index(op.f('ix_prediction_feedback_prediction_id'), 'prediction_feedback', ['prediction_id'], unique=False)
    op.create_index(op.f('ix_prediction_feedback_user_id'), 'prediction_feedback', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_prediction_feedback_user_id'), table_name='prediction_feedback')
    op.drop_index(op.f('ix_prediction_feedback_prediction_id'), table_name='prediction_feedback')
    op.drop_index(op.f('ix_prediction_feedback_id'), table_name='prediction_feedback')
    op.drop_table('prediction_feedback')
