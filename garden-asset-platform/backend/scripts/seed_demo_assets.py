"""用真实园林照片填充本地演示库

用法（需在 backend 目录或任意目录运行均可）：
    python scripts/seed_demo_assets.py --reset
    python scripts/seed_demo_assets.py --reset --watermark-count 4 --chain-count 2

依赖 .scratch/demo/photos 下的照片与 manifest.json（由 scripts/fetch_demo_photos.py 生成），
照片只用于本地演示，不进入仓库。
"""
import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Asset, AssetFeature, AssetTag, AssetVersion, BlockchainTransaction, Certificate,
    Garden, License, LicenseApplication, LicenseContract, OperationLog, User
)
from app.models.extra import DownloadRecord, Favorite  # noqa: E402
from app.seed_data import GARDENS  # noqa: E402
from app.utils.thumbnails import generate_thumbnail_set  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / '.scratch' / 'demo' / 'photos' / 'manifest.json'
DEFAULT_META = REPO_ROOT / '.scratch' / 'demo' / 'photos' / 'assets.json'


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def photos_from_manifest(data):
    if isinstance(data, list):
        return data, {}
    photos = data.get('photos') or data.get('files') or []
    covers = data.get('covers') or {}
    return photos, covers


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def reset_demo_data():
    """清空演示库中的业务数据，保留用户与园林。"""
    LicenseContract.query.delete()
    License.query.delete()
    LicenseApplication.query.delete()
    DownloadRecord.query.delete()
    Favorite.query.delete()
    Certificate.query.delete()
    BlockchainTransaction.query.delete()
    AssetFeature.query.delete()
    AssetTag.query.delete()
    OperationLog.query.delete()
    AssetVersion.query.delete()
    Asset.query.delete()
    db.session.commit()


def ensure_initial_version(asset):
    """为演示资产补建 v1，已有版本时不动"""
    if AssetVersion.query.filter_by(asset_id=asset.id).first():
        return False
    storage_path = asset.storage_path or ''
    db.session.add(AssetVersion(
        asset_id=asset.id,
        version_no=1,
        file_path=os.path.abspath(storage_path) if storage_path else '',
        file_name=os.path.basename(storage_path) if storage_path else None,
        file_format=asset.file_format,
        file_size=asset.file_size,
        file_hash=asset.file_hash,
        thumbnail_path=asset.thumbnail_path,
        change_note='初始版本',
        created_by=asset.uploader_id or asset.creator_id
    ))
    return True


def refresh_gardens():
    for data in GARDENS:
        garden = Garden.query.filter_by(code=data['code']).first()
        if not garden:
            garden = Garden(**data)
            db.session.add(garden)
        else:
            for key, value in data.items():
                setattr(garden, key, value)
    db.session.commit()


def make_asset(photo, meta, admin, index):
    garden_code = meta.get('garden_code') or photo.get('garden_code') or 'GEN'
    garden = Garden.query.filter_by(code=garden_code).first()
    if not garden:
        raise ValueError(f'未知园林编码: {garden_code}')

    photo_path = (DEFAULT_MANIFEST.parent / photo['filename']).resolve()
    if not photo_path.is_file():
        raise FileNotFoundError(photo_path)

    asset_code = f"{garden_code}-IMG-{datetime.now():%Y%m%d}-D{index:02d}"
    asset = Asset.query.filter_by(asset_code=asset_code).first() or Asset(asset_code=asset_code)
    asset.title = meta.get('title') or photo.get('commons_title') or f'{garden.name}影像'
    asset.description = meta.get('description') or photo.get('description') or ''
    asset.asset_type = 'image'
    asset.file_format = 'jpg'
    asset.file_size = photo_path.stat().st_size
    asset.file_hash = file_sha256(photo_path)
    asset.storage_path = str(photo_path)
    asset.garden_id = garden.id
    asset.creator_id = admin.id
    asset.uploader_id = admin.id
    asset.owner_id = admin.id
    asset.status = 'published'

    db.session.add(asset)
    db.session.flush()

    asset.thumbnail_path, _ = generate_thumbnail_set(photo_path, asset.id)
    db.session.add(asset)
    ensure_initial_version(asset)
    return asset


def seed_licenses(assets, users):
    admin = users['admin']
    adm1 = users['adm1']
    adm2 = users['adm2']
    user1 = users['user1']
    user2 = users['user2']
    now = datetime.utcnow()

    active_license = License(
        license_code=f'LIC-{now:%Y%m%d%H%M%S}-DEMO1',
        asset_id=assets[0].id,
        licensor_id=admin.id,
        licensee_id=user1.id,
        license_type='non_commercial',
        usage_scope='用于课程教学与学术研究中的园林案例分析，不用于商业传播。',
        territory='中国大陆',
        start_time=now - timedelta(days=12),
        end_time=now + timedelta(days=353),
        status='active'
    )
    db.session.add(active_license)
    assets[0].license_count = (assets[0].license_count or 0) + 1

    approved = LicenseApplication(
        application_code=f'APP-{now:%Y%m%d%H%M%S}-DEMO1',
        asset_id=assets[1].id,
        applicant_id=user2.id,
        license_type='commercial_publish',
        usage_scope='用于城市文化宣传册出版，发行范围为中国大陆。',
        usage_purpose='城市文化宣传册配图',
        duration_months=12,
        status='approved',
        adm1_status='approved',
        adm1_reviewer_id=adm1.id,
        adm1_review_time=now - timedelta(days=5),
        adm1_review_comment='材料齐全，同意授权。',
        adm2_status='approved',
        adm2_reviewer_id=adm2.id,
        adm2_review_time=now - timedelta(days=4),
        adm2_review_comment='使用范围明确，准予通过。'
    )
    db.session.add(approved)
    db.session.flush()

    db.session.add(License(
        license_code=f'LIC-{now:%Y%m%d%H%M%S}-DEMO2',
        asset_id=assets[1].id,
        licensor_id=admin.id,
        licensee_id=user2.id,
        license_type='commercial_publish',
        usage_scope=approved.usage_scope,
        territory='中国大陆',
        start_time=now - timedelta(days=4),
        end_time=now + timedelta(days=361),
        status='active'
    ))
    assets[1].license_count = (assets[1].license_count or 0) + 1

    db.session.add(LicenseApplication(
        application_code=f'APP-{now:%Y%m%d%H%M%S}-DEMO2',
        asset_id=assets[2].id,
        applicant_id=user1.id,
        license_type='non_commercial',
        usage_scope='用于学校园林文化社团的展板与校内刊物。',
        usage_purpose='校内非商业展示',
        duration_months=6,
        status='pending',
        adm1_status='pending',
        adm2_status='pending'
    ))

    db.session.add(LicenseApplication(
        application_code=f'APP-{now:%Y%m%d%H%M%S}-DEMO3',
        asset_id=assets[3].id,
        applicant_id=user2.id,
        license_type='derivative',
        usage_scope='以园林影像为素材创作数字插画，并在线上展览发布。',
        usage_purpose='衍生数字插画创作',
        duration_months=12,
        status='adm1_approved',
        adm1_status='approved',
        adm1_reviewer_id=adm1.id,
        adm1_review_time=now - timedelta(days=2),
        adm1_review_comment='一级审核通过，提请二级复核。',
        adm2_status='pending'
    ))

    db.session.commit()
    return 5


def seed_download_records(assets, users):
    """补充下载台账样例，便于演示“下载记录/下载台账”。"""
    if len(assets) < 5:
        return 0

    licenses = License.query.filter_by(status='active').order_by(License.id).all()
    now = datetime.utcnow()
    combos = [
        (users['user1'], assets[0], licenses[0] if licenses else None, 3),
        (users['user1'], assets[1], None, 2),
        (users['user2'], assets[1], licenses[1] if len(licenses) > 1 else None, 5),
        (users['user2'], assets[2], None, 1),
        (users['user1'], assets[3], None, 8),
        (users['user2'], assets[4], None, 0),
    ]
    for user, asset, license_row, days_ago in combos:
        db.session.add(DownloadRecord(
            user_id=user.id,
            asset_id=asset.id,
            license_id=license_row.id if license_row else None,
            ip_address='127.0.0.1',
            user_agent='Demo Seeder',
            created_at=now - timedelta(days=days_ago, hours=days_ago)
        ))
    db.session.commit()
    return len(combos)


def seed_collections(assets, users):
    """给演示用户准备两个合集，便于体验策展与公开合集。"""
    from app.models import Collection, CollectionAsset

    if len(assets) < 4:
        return 0

    user1 = users['user1']
    definitions = [
        ('拙政园水景', '以水院、荷池与倒影为主的拙政园影像。', True, assets[:3]),
        ('古建细节', '斗拱、花窗、铺地与假山细节，用于设计参考。', False, assets[3:5]),
    ]
    created = 0
    for name, description, is_public, members in definitions:
        collection = Collection(
            name=name,
            description=description,
            owner_id=user1.id,
            is_public=is_public
        )
        db.session.add(collection)
        db.session.flush()
        for asset in members:
            db.session.add(CollectionAsset(
                collection_id=collection.id,
                asset_id=asset.id
            ))
        created += 1
    db.session.commit()
    return created


def seed_user_assets(source_assets, user):
    """给演示用户造一条草稿和一条被驳回资产，便于体验“我的资产”流程。"""
    if not source_assets:
        return 0

    created = 0
    drafts = [
        {
            'code': 'ZZY-IMG-20261021-U01',
            'title': '拙政园·见山楼（待整理）',
            'description': '从远香堂西望见山楼，尚待补充拍摄年代与授权说明。',
            'source': source_assets[0],
            'status': 'draft',
            'reason': None
        },
        {
            'code': 'HXSZ-IMG-20261021-U02',
            'title': '环秀山庄·旧影（待补充来源）',
            'description': '历史影像，需补充拍摄年代、收藏机构与授权说明。',
            'source': source_assets[-1],
            'status': 'rejected',
            'reason': '历史影像缺少拍摄年代与来源说明，请补充后重新提交。'
        }
    ]

    for item in drafts:
        if Asset.query.filter_by(asset_code=item['code']).first():
            continue
        source = item['source']
        path = source.storage_path
        with open(path, 'rb') as handle:
            actual_hash = hashlib.sha256(handle.read()).hexdigest()
        asset = Asset(
            asset_code=item['code'],
            title=item['title'],
            description=item['description'],
            asset_type='image',
            file_format='jpg',
            file_size=os.path.getsize(path),
            file_hash=actual_hash,
            storage_path=path,
            garden_id=source.garden_id,
            creator_id=user.id,
            uploader_id=user.id,
            owner_id=user.id,
            status=item['status'],
            reject_reason=item['reason']
        )
        db.session.add(asset)
        db.session.flush()
        asset.thumbnail_path, _ = generate_thumbnail_set(path, asset.id)
        ensure_initial_version(asset)
        created += 1

    db.session.commit()
    return created


def process_assets(assets, admin, watermark_count, chain_count):
    from app.services.watermark_service import WatermarkService
    from app.services.blockchain_service import blockchain_service

    watermarked = 0
    chained = 0
    for asset in assets[:watermark_count]:
        result = WatermarkService.embed_watermark(asset, admin)
        if result.get('success'):
            watermarked += 1
            print(f"  水印: {asset.title} -> {result.get('watermark_id')}")
        else:
            print(f"  水印失败: {asset.title}: {result.get('message')}")

    for asset in assets[:chain_count]:
        result = blockchain_service.register_asset(asset, admin)
        if result.get('success'):
            chained += 1
            print(f"  存证: {asset.title} -> {result.get('certificate_id')}")
        else:
            print(f"  存证失败: {asset.title}: {result.get('message')}")

    return watermarked, chained


def main():
    parser = argparse.ArgumentParser(description='用真实照片填充演示库')
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    parser.add_argument('--meta', default=str(DEFAULT_META))
    parser.add_argument('--reset', action='store_true', help='清空现有资产与授权后重建')
    parser.add_argument('--watermark-count', type=int, default=4, help='自动嵌入水印的资产数')
    parser.add_argument('--chain-count', type=int, default=2, help='自动上链存证的资产数')
    args = parser.parse_args()

    app = create_app('development')
    with app.app_context():
        db_path = str(db.engine.url.database or '')
        if args.reset and not any(token in db_path.lower() for token in ('demo', '.scratch')):
            sys.exit(f'拒绝清空非演示数据库: {db_path}')

        manifest = load_json(args.manifest)
        photos, covers = photos_from_manifest(manifest)
        meta_list = load_json(args.meta) if Path(args.meta).is_file() else []
        meta_by_filename = {item['filename']: item for item in meta_list if item.get('filename')}

        if not photos:
            sys.exit('manifest 中没有照片')

        refresh_gardens()
        if args.reset:
            reset_demo_data()
            print('已清空旧演示数据')

        admin = User.query.filter_by(role='admin').first()
        if not admin:
            sys.exit('请先运行 scripts/init_db.py 创建管理员')

        photos = sorted(photos, key=lambda p: (p.get('garden_code') or '', p.get('filename') or ''))
        assets = []
        for index, photo in enumerate(photos, start=1):
            meta = meta_by_filename.get(photo.get('filename'), {})
            try:
                asset = make_asset(photo, meta, admin, index)
                assets.append(asset)
                print(f"  资产: {asset.title} ({asset.asset_code})")
            except Exception as e:
                print(f"  跳过 {photo.get('filename')}: {e}")

        db.session.commit()
        print(f'已写入 {len(assets)} 个真实影像资产')

        if covers:
            for garden_code, filename in covers.items():
                asset = next((a for a in assets if Path(a.storage_path).name == filename), None)
                garden = Garden.query.filter_by(code=garden_code).first()
                if asset and garden:
                    garden.cover_image = f'/api/assets/{asset.id}/thumbnail?size=card&v=2'
            db.session.commit()
            print(f'已设置 {len(covers)} 个园林封面')

        watermarked = chained = 0
        if args.watermark_count or args.chain_count:
            watermarked, chained = process_assets(
                assets, admin,
                max(args.watermark_count, 0),
                max(args.chain_count, 0)
            )

        licenses = 0
        user_assets = 0
        downloads = 0
        collections = 0
        if len(assets) >= 4:
            users = {name: User.query.filter_by(username=name).first()
                     for name in ('admin', 'adm1', 'adm2', 'user1', 'user2')}
            if all(users.values()):
                licenses = seed_licenses(assets, users)
                user_assets = seed_user_assets(assets, users['user1'])
                downloads = seed_download_records(assets, users)
                collections = seed_collections(assets, users)
                print(f'已写入 {licenses} 条授权/申请记录，{user_assets} 条用户草稿/驳回资产，'
                      f'{downloads} 条下载记录，{collections} 个合集')

        print('\n完成:')
        print(f'  资产 {len(assets)}，水印 {watermarked}，存证 {chained}，授权/申请 {licenses}')
        print(f'  用户草稿/驳回资产 {user_assets}，下载记录 {downloads}，合集 {collections}')
        print(f'  数据库: {db_path}')


if __name__ == '__main__':
    main()
