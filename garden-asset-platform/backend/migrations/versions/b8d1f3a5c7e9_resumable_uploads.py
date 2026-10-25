"""resumable upload sessions

Revision ID: b8d1f3a5c7e9
Revises: a7c9e2f4b6d8
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d1f3a5c7e9'
down_revision = 'a7c9e2f4b6d8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'upload_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('garden_id', sa.Integer(), nullable=True),
        sa.Column('tags_json', sa.Text(), nullable=True),
        sa.Column('expected_size', sa.BigInteger(), nullable=False),
        sa.Column('received_size', sa.BigInteger(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('temp_path', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('upload_sessions') as batch_op:
        batch_op.create_index(batch_op.f('ix_upload_sessions_user_id'), ['user_id'], unique=False)


def downgrade():
    op.drop_table('upload_sessions')
