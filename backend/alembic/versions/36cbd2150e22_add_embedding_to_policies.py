"""add embedding to policies

Revision ID: 36cbd2150e22
Revises: a88a05d9a87a
Create Date: 2026-11-20 11:12:39.573680

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '36cbd2150e22'
down_revision: Union[str, Sequence[str], None] = 'a88a05d9a87a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # local Docker already enables this in docker/postgres/init.sql; a fresh
    # production database may not, and this does nothing when it exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column('policies', sa.Column('embedding', Vector(384), nullable=True))
    op.add_column('policies', sa.Column('embedding_model', sa.String(length=100), nullable=True))
    # Alembic does not detect new check constraints, so it is added by hand:
    # a vector and the name of the model that made it exist together or not at all
    op.create_check_constraint(
        'ck_policies_embedding_has_model',
        'policies',
        '(embedding IS NULL) = (embedding_model IS NULL)',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_policies_embedding_has_model', 'policies', type_='check')
    op.drop_column('policies', 'embedding_model')
    op.drop_column('policies', 'embedding')
