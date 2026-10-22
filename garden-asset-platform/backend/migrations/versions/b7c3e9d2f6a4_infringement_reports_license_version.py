"""侵权线索与授权版本绑定

- 新增 infringement_reports
- licenses 增加 version_id / version_no（签发时绑定的文件版本）

Revision ID: b7c3e9d2f6a4
Revises: 9a2e4c7d1b55
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c3e9d2f6a4'
down_revision = '9a2e4c7d1b55'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'licenses', sa.Column('version_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'licenses', sa.Column('version_no', sa.Integer(), nullable=True)
    )

    op.create_table(
        'infringement_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_code', sa.String(length=40), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=True),
        sa.Column('reporter_id', sa.Integer(), nullable=True),
        sa.Column('reporter_name', sa.String(length=100), nullable=True),
        sa.Column('contact', sa.String(length=200), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('suspect_filename', sa.String(length=255), nullable=True),
        sa.Column('suspect_file_path', sa.String(length=500), nullable=True),
        sa.Column('suspect_file_hash', sa.String(length=64), nullable=True),
        sa.Column('suspect_file_size', sa.BigInteger(), nullable=True),
        sa.Column('watermark_id', sa.String(length=64), nullable=True),
        sa.Column('certificate_id', sa.String(length=64), nullable=True),
        sa.Column('trace_verified', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('reviewer_id', sa.Integer(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_code'),
    )
    op.create_index(
        'ix_infringement_reports_asset_id',
        'infringement_reports', ['asset_id'], unique=False
    )
    op.create_index(
        'ix_infringement_reports_reporter_id',
        'infringement_reports', ['reporter_id'], unique=False
    )
    op.create_index(
        'ix_infringement_reports_status',
        'infringement_reports', ['status'], unique=False
    )
    op.create_index(
        'ix_infringement_reports_created_at',
        'infringement_reports', ['created_at'], unique=False
    )


def downgrade():
    op.drop_index(
        'ix_infringement_reports_created_at', table_name='infringement_reports'
    )
    op.drop_index(
        'ix_infringement_reports_status', table_name='infringement_reports'
    )
    op.drop_index(
        'ix_infringement_reports_reporter_id', table_name='infringement_reports'
    )
    op.drop_index(
        'ix_infringement_reports_asset_id', table_name='infringement_reports'
    )
    op.drop_table('infringement_reports')
    op.drop_column('licenses', 'version_no')
    op.drop_column('licenses', 'version_id')
