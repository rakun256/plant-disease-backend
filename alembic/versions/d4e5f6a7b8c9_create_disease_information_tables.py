"""Create disease information tables

Revision ID: d4e5f6a7b8c9
Revises: c1e2f3a4b5d6
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c1e2f3a4b5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DISCLAIMER = (
    "This information is based on an AI-assisted prediction and general plant disease "
    "guidance. It is not a replacement for diagnosis by a qualified agricultural expert."
)


DISEASES = [
    {
        "slug": "healthy",
        "name": "Healthy Apple Leaf",
        "description": "The leaf does not show obvious visual signs of the supported apple leaf diseases.",
        "symptoms": "Typical green leaf color and texture without clear rust-colored, olive-green, or black disease lesions.",
        "causes": "No disease cause is indicated by the current visual prediction.",
        "prevention": "Continue routine orchard monitoring, balanced watering, good airflow, sanitation, and locally recommended preventive care.",
        "severity_level": "none",
        "recommendations": [
            "Keep monitoring leaves regularly, especially after wet or humid weather.",
            "Maintain good orchard hygiene by removing fallen leaves and plant debris.",
            "Follow local agricultural guidance for watering, pruning, and preventive spray schedules when appropriate.",
        ],
    },
    {
        "slug": "rust",
        "name": "Cedar Apple Rust",
        "description": "Cedar apple rust is a fungal disease that can produce yellow to orange spots on apple leaves and may reduce tree vigor when pressure is high.",
        "symptoms": "Yellow-orange leaf spots, sometimes with small dark centers or raised structures on the underside of leaves.",
        "causes": "A rust fungus that alternates between apple trees and juniper or cedar hosts, with infection favored by wet spring conditions.",
        "prevention": "Improve airflow, monitor nearby juniper or cedar hosts, remove obvious alternate-host galls where practical, and follow local extension guidance for preventive fungicide timing.",
        "severity_level": "moderate",
        "recommendations": [
            "Confirm symptoms on multiple leaves before making treatment decisions.",
            "Remove heavily affected leaves or nearby cedar/juniper galls when practical and permitted.",
            "Consult a local agricultural extension service or crop specialist about suitable fungicide options and timing.",
        ],
    },
    {
        "slug": "scab",
        "name": "Apple Scab",
        "description": "Apple scab is a fungal disease that can cause olive-green to dark lesions on leaves and fruit, especially in cool and wet conditions.",
        "symptoms": "Olive-green, brown, or black velvety spots on leaves; leaves may yellow, curl, or drop early when infection is severe.",
        "causes": "A fungal pathogen that overwinters in infected leaf litter and spreads during wet periods.",
        "prevention": "Remove fallen leaves, prune for airflow, avoid prolonged leaf wetness where possible, and follow local guidance for preventive fungicide programs.",
        "severity_level": "moderate",
        "recommendations": [
            "Remove and dispose of fallen infected leaves to reduce future disease pressure.",
            "Improve canopy airflow through appropriate pruning and spacing.",
            "Ask a local agricultural expert about scab-resistant varieties and region-appropriate treatment timing.",
        ],
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'diseases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('symptoms', sa.Text(), nullable=True),
        sa.Column('causes', sa.Text(), nullable=True),
        sa.Column('prevention', sa.Text(), nullable=True),
        sa.Column('severity_level', sa.String(), nullable=True),
        sa.Column('disclaimer', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index(op.f('ix_diseases_id'), 'diseases', ['id'], unique=False)

    op.create_table(
        'disease_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_disease_recommendations_id'), 'disease_recommendations', ['id'], unique=False)
    op.create_index(op.f('ix_disease_recommendations_disease_id'), 'disease_recommendations', ['disease_id'], unique=False)

    disease_table = sa.table(
        'diseases',
        sa.column('id', sa.Integer),
        sa.column('slug', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('symptoms', sa.Text),
        sa.column('causes', sa.Text),
        sa.column('prevention', sa.Text),
        sa.column('severity_level', sa.String),
        sa.column('disclaimer', sa.Text),
    )
    recommendation_table = sa.table(
        'disease_recommendations',
        sa.column('disease_id', sa.Integer),
        sa.column('recommendation', sa.Text),
        sa.column('order_index', sa.Integer),
    )

    connection = op.get_bind()
    for disease in DISEASES:
        connection.execute(
            disease_table.insert().values(
                slug=disease["slug"],
                name=disease["name"],
                description=disease["description"],
                symptoms=disease["symptoms"],
                causes=disease["causes"],
                prevention=disease["prevention"],
                severity_level=disease["severity_level"],
                disclaimer=DISCLAIMER,
            )
        )
        disease_id = connection.execute(
            sa.select(disease_table.c.id).where(disease_table.c.slug == disease["slug"])
        ).scalar_one()
        op.bulk_insert(
            recommendation_table,
            [
                {
                    "disease_id": disease_id,
                    "recommendation": recommendation,
                    "order_index": index,
                }
                for index, recommendation in enumerate(disease["recommendations"])
            ],
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_disease_recommendations_disease_id'), table_name='disease_recommendations')
    op.drop_index(op.f('ix_disease_recommendations_id'), table_name='disease_recommendations')
    op.drop_table('disease_recommendations')
    op.drop_index(op.f('ix_diseases_id'), table_name='diseases')
    op.drop_table('diseases')
