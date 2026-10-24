"""通知渠道与授权范围执行

- notification_preferences / notification_deliveries
- licenses / license_applications 增加可执行范围字段
- download_records 增加成功/拒绝状态与申报用途、地域

Revision ID: 9a2e4c7d1b55
Revises: 4f6d2b8c9a31
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = '9a2e4c7d1b55'
down_revision = '4f6d2b8c9a31'
branch_labels = None
depends_on = None


def _scope_columns():
    return (
        sa.Column('usage_purpose_code', sa.String(length=40), nullable=True),
        sa.Column('allowed_channels', sa.JSON(), nullable=True),
        sa.Column('allowed_formats', sa.JSON(), nullable=True),
        sa.Column('max_downloads', sa.Integer(), nullable=True),
    )


def upgrade():
    for table in ('licenses', 'license_applications'):
        for column in _scope_columns():
            op.add_column(table, column)

    op.add_column(
        'licenses',
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0')
    )

    op.add_column(
        'download_records',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success')
    )
    op.add_column(
        'download_records',
        sa.Column('denial_reason', sa.String(length=300), nullable=True)
    )
    op.add_column(
        'download_records',
        sa.Column('usage_purpose', sa.String(length=40), nullable=True)
    )
    op.add_column(
        'download_records',
        sa.Column('territory', sa.String(length=100), nullable=True)
    )
    op.create_index(
        'ix_download_records_status', 'download_records', ['status'], unique=False
    )

    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('email_groups', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(
        'ix_notification_preferences_user_id',
        'notification_preferences', ['user_id'], unique=True
    )

    op.create_table(
        'notification_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['notification_events.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'channel', name='uk_notification_delivery'),
    )
    op.create_index(
        'ix_notification_deliveries_event_id',
        'notification_deliveries', ['event_id'], unique=False
    )
    op.create_index(
        'ix_notification_deliveries_status',
        'notification_deliveries', ['status'], unique=False
    )
    op.create_index(
        'ix_notification_deliveries_created_at',
        'notification_deliveries', ['created_at'], unique=False
    )


def downgrade():
    op.drop_index(
        'ix_notification_deliveries_created_at', table_name='notification_deliveries'
    )
    op.drop_index(
        'ix_notification_deliveries_status', table_name='notification_deliveries'
    )
    op.drop_index(
        'ix_notification_deliveries_event_id', table_name='notification_deliveries'
    )
    op.drop_table('notification_deliveries')

    op.drop_index(
        'ix_notification_preferences_user_id', table_name='notification_preferences'
    )
    op.drop_table('notification_preferences')

    op.drop_index('ix_download_records_status', table_name='download_records')
    for column in ('territory', 'usage_purpose', 'denial_reason', 'status'):
        op.drop_column('download_records', column)

    op.drop_column('licenses', 'download_count')
    for table in ('licenses', 'license_applications'):
        for column in ('max_downloads', 'allowed_formats', 'allowed_channels',
                       'usage_purpose_code'):
            op.drop_column(table, column)
