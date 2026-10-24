"""asset soft delete lifecycle

Revision ID: f4b2d6e8a1c3
Revises: e9a1c3d5f7b2
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = 'f4b2d6e8a1c3'
down_revision = 'e9a1c3d5f7b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deleted_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('previous_status', sa.String(length=20), nullable=True))
        batch_op.create_foreign_key(
            'fk_assets_deleted_by_users', 'users', ['deleted_by'], ['id']
        )


def downgrade():
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_constraint('fk_assets_deleted_by_users', type_='foreignkey')
        batch_op.drop_column('previous_status')
        batch_op.drop_column('deleted_by')
        batch_op.drop_column('deleted_at')
