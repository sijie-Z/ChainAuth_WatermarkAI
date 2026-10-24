"""异步任务队列表

Revision ID: 7b1c9a2d4e10
Revises: 42313531c6a5
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = '7b1c9a2d4e10'
down_revision = '42313531c6a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'async_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('version_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=140), nullable=True),
        sa.Column('worker_id', sa.String(length=100), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_async_tasks_task_type'), 'async_tasks', ['task_type'], unique=False
    )
    op.create_index(
        op.f('ix_async_tasks_status'), 'async_tasks', ['status'], unique=False
    )
    op.create_index(
        op.f('ix_async_tasks_asset_id'), 'async_tasks', ['asset_id'], unique=False
    )
    op.create_index(
        op.f('ix_async_tasks_user_id'), 'async_tasks', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_async_tasks_dedupe_key'), 'async_tasks', ['dedupe_key'], unique=False
    )
    op.create_index(
        op.f('ix_async_tasks_created_at'), 'async_tasks', ['created_at'], unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_async_tasks_created_at'), table_name='async_tasks')
    op.drop_index(op.f('ix_async_tasks_dedupe_key'), table_name='async_tasks')
    op.drop_index(op.f('ix_async_tasks_user_id'), table_name='async_tasks')
    op.drop_index(op.f('ix_async_tasks_asset_id'), table_name='async_tasks')
    op.drop_index(op.f('ix_async_tasks_status'), table_name='async_tasks')
    op.drop_index(op.f('ix_async_tasks_task_type'), table_name='async_tasks')
    op.drop_table('async_tasks')
