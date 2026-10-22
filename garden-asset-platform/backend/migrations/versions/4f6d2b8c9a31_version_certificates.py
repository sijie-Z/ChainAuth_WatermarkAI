"""证书按文件版本签发

certificates.asset_id 取消唯一约束，新增 version_id / version_no，
同一资产的不同版本可以各自持有证书；历史证书保留。

Revision ID: 4f6d2b8c9a31
Revises: 7b1c9a2d4e10
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = '4f6d2b8c9a31'
down_revision = '7b1c9a2d4e10'
branch_labels = None
depends_on = None

BACKFILL_VERSION = """
UPDATE certificates SET version_id = (
    SELECT v.id FROM asset_versions v
    WHERE v.asset_id = certificates.asset_id
      AND v.file_hash = certificates.file_hash
    ORDER BY v.version_no DESC
    LIMIT 1
)
"""

BACKFILL_VERSION_NO = """
UPDATE certificates SET version_no = (
    SELECT v.version_no FROM asset_versions v WHERE v.id = certificates.version_id
)
"""


def _certificate_columns(include_version=True, unique_asset=False):
    columns = [
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('certificate_id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
    ]
    if include_version:
        columns.extend([
            sa.Column('version_id', sa.Integer(), nullable=True),
            sa.Column('version_no', sa.Integer(), nullable=True),
        ])
    columns.extend([
        sa.Column('tx_hash', sa.String(length=66), nullable=True),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('watermark_id', sa.String(length=64), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('creator_name', sa.String(length=100), nullable=True),
        sa.Column('creator_id_hash', sa.String(length=64), nullable=True),
        sa.Column('ownership_type', sa.String(length=50), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('certificate_file', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.PrimaryKeyConstraint('id'),
    ])
    if include_version:
        columns.append(
            sa.ForeignKeyConstraint(['version_id'], ['asset_versions.id'])
        )
        columns.append(
            sa.UniqueConstraint('version_id', name='uq_certificate_version')
        )
    if unique_asset:
        columns.append(sa.UniqueConstraint('asset_id'))
    return columns


def _rebuild_sqlite(include_version):
    """SQLite 无法直接删除列上的 UNIQUE，按新结构重建表。"""
    target = 'certificates_new'
    op.create_table(target, *_certificate_columns(include_version=include_version))
    if include_version:
        op.execute(
            f"""
            INSERT INTO {target} (
                id, certificate_id, asset_id, version_id, version_no,
                tx_hash, block_number, watermark_id, file_hash,
                creator_name, creator_id_hash, ownership_type,
                valid_from, valid_until, certificate_file, status, created_at
            )
            SELECT
                id, certificate_id, asset_id, NULL, NULL,
                tx_hash, block_number, watermark_id, file_hash,
                creator_name, creator_id_hash, ownership_type,
                valid_from, valid_until, certificate_file, status, created_at
            FROM certificates
            """
        )
    else:
        op.execute(
            f"""
            INSERT INTO {target} (
                id, certificate_id, asset_id, tx_hash, block_number,
                watermark_id, file_hash, creator_name, creator_id_hash,
                ownership_type, valid_from, valid_until, certificate_file,
                status, created_at
            )
            SELECT
                id, certificate_id, asset_id, tx_hash, block_number,
                watermark_id, file_hash, creator_name, creator_id_hash,
                ownership_type, valid_from, valid_until, certificate_file,
                status, created_at
            FROM certificates
            """
        )
    op.drop_table('certificates')
    op.rename_table(target, 'certificates')
    op.create_index(
        'ix_certificates_certificate_id', 'certificates',
        ['certificate_id'], unique=True
    )
    op.create_index(
        'ix_certificates_asset_id', 'certificates', ['asset_id'], unique=False
    )


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        _rebuild_sqlite(include_version=True)
    else:
        op.add_column(
            'certificates', sa.Column('version_id', sa.Integer(), nullable=True)
        )
        op.add_column(
            'certificates', sa.Column('version_no', sa.Integer(), nullable=True)
        )
        op.drop_constraint(
            'certificates_asset_id_key', 'certificates', type_='unique'
        )
        op.create_foreign_key(
            'fk_certificates_version_id', 'certificates', 'asset_versions',
            ['version_id'], ['id']
        )
        op.create_unique_constraint(
            'uq_certificate_version', 'certificates', ['version_id']
        )
        op.create_index(
            'ix_certificates_asset_id', 'certificates', ['asset_id'], unique=False
        )

    # 旧证书按文件指纹回填到对应版本；找不到匹配版本时保持 NULL
    op.execute(BACKFILL_VERSION)
    op.execute(BACKFILL_VERSION_NO)


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 旧结构一个资产只能有一份证书；降级只保留最新的那份
    op.execute(
        """
        DELETE FROM certificates WHERE id NOT IN (
            SELECT MAX(id) FROM certificates GROUP BY asset_id
        )
        """
    )

    if dialect == 'sqlite':
        _rebuild_sqlite(include_version=False)
        # 重建为旧结构后 asset_id 唯一约束由建表定义带入
    else:
        op.drop_index('ix_certificates_asset_id', table_name='certificates')
        op.drop_constraint(
            'uq_certificate_version', 'certificates', type_='unique'
        )
        op.drop_constraint(
            'fk_certificates_version_id', 'certificates', type_='foreignkey'
        )
        op.drop_column('certificates', 'version_no')
        op.drop_column('certificates', 'version_id')
        op.create_unique_constraint(
            'certificates_asset_id_key', 'certificates', ['asset_id']
        )
