"""upload session fingerprints and write leases

Revision ID: e5a8c2f7b1d4
Revises: d1f4b6c8e0a2
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5a8c2f7b1d4'
down_revision = 'd1f4b6c8e0a2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('upload_sessions') as batch_op:
        batch_op.add_column(
            sa.Column('file_fingerprint', sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column('lease_token', sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column('lease_expires_at', sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('upload_sessions') as batch_op:
        batch_op.drop_column('lease_expires_at')
        batch_op.drop_column('lease_token')
        batch_op.drop_column('file_fingerprint')
