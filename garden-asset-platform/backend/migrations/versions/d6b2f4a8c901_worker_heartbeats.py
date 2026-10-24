"""worker 心跳

- 新增 worker_heartbeats：记录进程内线程 / `flask tasks run` 的存活与处理量
- 供后台任务队列页与 /api/tasks/health 判断“队列有任务但无人消费”

Revision ID: d6b2f4a8c901
Revises: c4d8e1f2a6b7
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = 'd6b2f4a8c901'
down_revision = 'c4d8e1f2a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(length=120), nullable=False),
        sa.Column(
            'kind', sa.String(length=20), nullable=False, server_default='thread'
        ),
        sa.Column('hostname', sa.String(length=120), nullable=True),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column(
            'processed', sa.Integer(), nullable=False, server_default='0'
        ),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('worker_id', name='uq_worker_heartbeats_worker_id'),
    )
    op.create_index(
        'ix_worker_heartbeats_last_seen_at',
        'worker_heartbeats', ['last_seen_at'], unique=False
    )


def downgrade():
    op.drop_index(
        'ix_worker_heartbeats_last_seen_at', table_name='worker_heartbeats'
    )
    op.drop_table('worker_heartbeats')
