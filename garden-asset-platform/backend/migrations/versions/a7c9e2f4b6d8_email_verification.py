"""user email verification timestamp

Revision ID: a7c9e2f4b6d8
Revises: f4b2d6e8a1c3
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c9e2f4b6d8'
down_revision = 'f4b2d6e8a1c3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('email_verified_at')
