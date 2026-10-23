"""下载指纹副本

- 新增 download_fingerprints（每个授权+资产一份可见指纹副本）
- download_records 增加 fingerprint_id

Revision ID: c4d8e1f2a6b7
Revises: b7c3e9d2f6a4
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d8e1f2a6b7'
down_revision = 'b7c3e9d2f6a4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'download_fingerprints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fingerprint_code', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
        sa.Column('license_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('license_id', 'asset_id', name='uk_license_asset_fingerprint'),
    )
    op.create_index(
        op.f('ix_download_fingerprints_fingerprint_code'),
        'download_fingerprints', ['fingerprint_code'], unique=True
    )
    op.create_index(
        'ix_download_fingerprints_asset_id',
        'download_fingerprints', ['asset_id'], unique=False
    )
    op.create_index(
        'ix_download_fingerprints_license_id',
        'download_fingerprints', ['license_id'], unique=False
    )
    op.create_index(
        'ix_download_fingerprints_user_id',
        'download_fingerprints', ['user_id'], unique=False
    )
    op.create_index(
        'ix_download_fingerprints_created_at',
        'download_fingerprints', ['created_at'], unique=False
    )
    op.add_column(
        'download_records',
        sa.Column('fingerprint_id', sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column('download_records', 'fingerprint_id')
    op.drop_index(
        'ix_download_fingerprints_created_at', table_name='download_fingerprints'
    )
    op.drop_index(
        'ix_download_fingerprints_user_id', table_name='download_fingerprints'
    )
    op.drop_index(
        'ix_download_fingerprints_license_id', table_name='download_fingerprints'
    )
    op.drop_index(
        'ix_download_fingerprints_asset_id', table_name='download_fingerprints'
    )
    op.drop_index(
        op.f('ix_download_fingerprints_fingerprint_code'),
        table_name='download_fingerprints'
    )
    op.drop_table('download_fingerprints')
