"""bind download fingerprints to source file hash

Revision ID: f7b2d4a6c8e1
Revises: e5a8c2f7b1d4
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa


revision = 'f7b2d4a6c8e1'
down_revision = 'e5a8c2f7b1d4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('download_fingerprints') as batch_op:
        batch_op.add_column(
            sa.Column('source_hash', sa.String(length=64), nullable=True)
        )
        batch_op.drop_constraint(
            'uk_license_asset_fingerprint', type_='unique'
        )
        batch_op.create_unique_constraint(
            'uk_license_asset_source_fingerprint',
            ['license_id', 'asset_id', 'source_hash'],
        )
        batch_op.create_index(
            batch_op.f('ix_download_fingerprints_source_hash'),
            ['source_hash'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('download_fingerprints') as batch_op:
        batch_op.drop_index(batch_op.f('ix_download_fingerprints_source_hash'))
        batch_op.drop_constraint(
            'uk_license_asset_source_fingerprint', type_='unique'
        )
        batch_op.create_unique_constraint(
            'uk_license_asset_fingerprint', ['license_id', 'asset_id']
        )
        batch_op.drop_column('source_hash')
