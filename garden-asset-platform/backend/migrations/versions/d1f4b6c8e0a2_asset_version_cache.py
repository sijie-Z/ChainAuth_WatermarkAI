"""asset current_version_no cache

Revision ID: d1f4b6c8e0a2
Revises: b8d1f3a5c7e9
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa


revision = 'd1f4b6c8e0a2'
down_revision = 'b8d1f3a5c7e9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(
            sa.Column(
                'current_version_no',
                sa.Integer(),
                nullable=True,
                server_default='1',
            )
        )
    op.get_bind().execute(sa.text(
        """
        UPDATE assets SET current_version_no = (
            SELECT MAX(version_no) FROM asset_versions
            WHERE asset_versions.asset_id = assets.id
        )
        WHERE EXISTS (
            SELECT 1 FROM asset_versions
            WHERE asset_versions.asset_id = assets.id
        )
        """
    ))


def downgrade():
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_column('current_version_no')
