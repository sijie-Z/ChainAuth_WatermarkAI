"""operation_logs.integrity_hash

Revision ID: e9a1c3d5f7b2
Revises: d6b2f4a8c901
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = 'e9a1c3d5f7b2'
down_revision = 'd6b2f4a8c901'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('operation_logs') as batch_op:
        batch_op.add_column(
            sa.Column('integrity_hash', sa.String(length=64), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('operation_logs') as batch_op:
        batch_op.drop_column('integrity_hash')
