"""
资产相关API资源
"""
import os
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.asset import Asset, AssetTag, AssetFeature, AssetVersion
from app.models.garden import Garden
from app.models.license import LicenseApplication, License
from app.models.log import OperationLog
from app.utils.middleware import rate_limit
from app.services.notification_service import add_notification_event
from sqlalchemy import func, or_


ADMIN_ROLES = ('admin', 'asset_admin', 'license_admin', 'adm1', 'adm2')
# 资产写操作（编辑、删除、标签）只允许超级管理员与资产管理员；
# 审批员可查看/审核，但不应该能改删他人资产。
ASSET_MANAGE_ROLES = ('admin', 'asset_admin')
ASSET_STATUSES = ('draft', 'pending', 'published', 'rejected', 'deleted')


class PublicStatsResource(Resource):
    """公开统计数据（无需登录）"""

    @rate_limit(limit=120, window=60)
    def get(self):
        total = Asset.query.filter_by(status='published').count()
        watermarked = Asset.query.filter(
            Asset.watermark_id.isnot(None), Asset.status == 'published'
        ).count()
        chained = Asset.query.filter(
            Asset.chain_tx_hash.isnot(None), Asset.status == 'published'
        ).count()
        total_licenses = License.query.join(Asset).filter(Asset.status != 'deleted').count()

        by_type = {}
        for type_name in ['image', 'model', 'vector', 'document', 'video']:
            by_type[type_name] = Asset.query.filter_by(
                asset_type=type_name, status='published'
            ).count()

        gardens = Garden.query.filter_by(status='active').order_by(Garden.id).limit(6).all()

        return {
            'code': 200,
            'data': {
                'total_assets': total,
                'watermarked_assets': watermarked,
                'chained_assets': chained,
                'total_licenses': total_licenses,
                'by_type': by_type,
                'gardens': [g.to_dict() for g in gardens]
            }
        }, 200


# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'],
    'model': ['obj', 'fbx', 'gltf', 'glb', 'stl'],
    'vector': ['shp', 'geojson', 'kml', 'kmz', 'zip'],
    'document': ['pdf', 'doc', 'docx', 'dwg', 'dxf'],
    'video': ['mp4', 'mov', 'avi', 'mkv']
}


def allowed_file(filename, asset_type):
    """检查文件类型是否允许"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(asset_type, [])
    return ext in allowed


# 常见文件类型的魔术字节 (magic bytes)
MAGIC_BYTES = {
    # 图片
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'gif': [b'GIF87a', b'GIF89a'],
    'bmp': [b'BM'],
    'webp': [b'RIFF'],
    'tiff': [b'II*\x00', b'MM\x00*'],
    # 文档
    'pdf': [b'%PDF'],
    # 视频
    'mp4': [b'\x00\x00\x00\x18ftypmp42', b'\x00\x00\x00\x1cftypmp42', b'\x00\x00\x00\x20ftypmp42'],
    'mov': [b'\x00\x00\x00\x14ftypqt'],
    'avi': [b'RIFF'],
    # 矢量
    'shp': [b'\x00\x00\x27\x0a'],  # SHP 文件头 (ESRI)
    'geojson': [b'{'],
    'kml': [b'<?xml', b'<kml'],
    'kmz': [b'PK\x03\x04'],
    'zip': [b'PK\x03\x04'],
    # 3D模型
    'obj': [b'# ', b'v ', b'f '],
    'stl': [b'solid'],
    'glb': [b'glTF'],
    'fbx': [b'Kaydara'],
}


def validate_magic_bytes(file, ext):
    """通过魔术字节验证文件类型"""
    if ext not in MAGIC_BYTES:
        return True  # 未收录的格式仅依赖扩展名检查

    expected = MAGIC_BYTES[ext]
    header = file.read(32)
    file.seek(0)

    for magic in expected:
        if header.startswith(magic):
            return True
    return False


def calculate_file_hash(file):
    """计算文件SHA256哈希"""
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b''):
        sha256.update(chunk)
    file.seek(0)  # 重置指针
    return sha256.hexdigest()


def generate_asset_code(garden_code, asset_type):
    """生成资产编码"""
    type_map = {
        'image': 'IMG',
        'model': 'MDL',
        'vector': 'VEC',
        'document': 'DOC',
        'video': 'VID'
    }
    type_code = type_map.get(asset_type, 'OTH')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = uuid.uuid4().hex[:4].upper()
    return f"{garden_code}-{type_code}-{timestamp}-{random_suffix}"


class TagListResource(Resource):
    """已发布资产的标签分面"""

    def get(self):
        rows = db.session.query(
            AssetTag.name, func.count(Asset.id)
        ).join(
            Asset, AssetTag.asset_id == Asset.id
        ).filter(
            Asset.status == 'published',
            AssetTag.name.isnot(None)
        ).group_by(AssetTag.name).order_by(
            func.count(Asset.id).desc(), AssetTag.name.asc()
        ).all()
        return {
            'code': 200,
            'data': [
                {'name': name, 'count': count}
                for name, count in rows if name
            ]
        }, 200


class AssetListResource(Resource):
    """资产列表"""

    @jwt_required()
    def get(self):
        """获取资产列表"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 401, 'message': '用户不存在'}, 401

        page = request.args.get('page', 1, type=int)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        asset_type = request.args.get('asset_type')
        garden_id = request.args.get('garden_id', type=int)
        status = (request.args.get('status') or '').strip()
        watermark_status = (request.args.get('watermark_status') or '').strip()
        chain_status = (request.args.get('chain_status') or '').strip()
        keyword = request.args.get('keyword')
        tag = (request.args.get('tag') or '').strip()
        file_format = (request.args.get('file_format') or '').strip().lower()
        uploader_id = request.args.get('uploader_id', type=int)
        date_from = (request.args.get('date_from') or '').strip()
        date_to = (request.args.get('date_to') or '').strip()

        query = Asset.query

        # 状态可见性：管理员可按状态筛选；普通用户只能看已发布
        if status:
            if status not in ASSET_STATUSES:
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            if status != 'published' and user.role not in ADMIN_ROLES:
                return {'code': 403, 'message': '无权限查看该状态的资产'}, 403
            query = query.filter_by(status=status)
        elif user.role in ADMIN_ROLES:
            query = query.filter(Asset.status != 'deleted')
        else:
            query = query.filter_by(status='published')

        # 过滤条件
        if asset_type:
            query = query.filter_by(asset_type=asset_type)
        if garden_id:
            query = query.filter_by(garden_id=garden_id)
        if watermark_status in ('none', 'embedded', 'verified', 'failed'):
            query = query.filter_by(watermark_status=watermark_status)
        if chain_status in ('none', 'pending', 'confirmed', 'failed'):
            query = query.filter_by(chain_status=chain_status)
        if keyword:
            like = f'%{keyword}%'
            query = query.filter(or_(
                Asset.title.ilike(like),
                Asset.asset_code.ilike(like),
                Asset.description.ilike(like),
            ))
        if tag:
            query = query.filter(Asset.tags.any(AssetTag.name == tag))
        if file_format:
            query = query.filter(func.lower(Asset.file_format) == file_format)
        if uploader_id:
            query = query.filter(Asset.uploader_id == uploader_id)
        if date_from:
            try:
                query = query.filter(
                    Asset.created_at >= datetime.fromisoformat(date_from)
                )
            except ValueError:
                return {'code': 400, 'message': '开始日期格式无效'}, 400
        if date_to:
            try:
                end = datetime.fromisoformat(date_to)
                if len(date_to) == 10:
                    end += timedelta(days=1)
                    query = query.filter(Asset.created_at < end)
                else:
                    query = query.filter(Asset.created_at <= end)
            except ValueError:
                return {'code': 400, 'message': '结束日期格式无效'}, 400

        # 排序
        sort = (request.args.get('sort') or 'newest').strip()
        if sort == 'oldest':
            query = query.order_by(Asset.created_at.asc())
        elif sort == 'popular':
            query = query.order_by(Asset.view_count.desc(), Asset.created_at.desc())
        elif sort == 'downloads':
            query = query.order_by(Asset.download_count.desc(), Asset.created_at.desc())
        else:
            query = query.order_by(Asset.created_at.desc())

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'code': 200,
            'data': {
                'items': [asset.to_dict() for asset in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        }, 200


class AssetResource(Resource):
    """单个资产"""

    @jwt_required()
    def get(self, asset_id):
        """获取资产详情"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        if user:
            is_admin = user.role in ADMIN_ROLES
            is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        else:
            is_admin = is_owner = False

        # 已删除仅管理员可见；未发布仅所有者/管理员可见
        if asset.status == 'deleted' and not is_admin:
            return {'code': 404, 'message': '资产不存在'}, 404
        if asset.status != 'published' and not (is_admin or is_owner):
            return {'code': 404, 'message': '资产不存在'}, 404

        # 增加浏览次数
        asset.view_count += 1
        db.session.commit()

        return {
            'code': 200,
            'data': asset.to_dict()
        }, 200

    @jwt_required()
    def put(self, asset_id):
        """更新资产信息"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        # 权限检查
        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and user.role not in ASSET_MANAGE_ROLES:
            return {'code': 403, 'message': '无权限修改'}, 403

        data = request.get_json()

        # 更新字段
        if 'title' in data:
            asset.title = data['title']
        if 'description' in data:
            asset.description = data['description']

        db.session.commit()

        OperationLog.log(
            user=user,
            action='update',
            module='asset',
            description=f'更新资产: {asset.asset_code}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        return {
            'code': 200,
            'message': '更新成功',
            'data': asset.to_dict()
        }, 200

    @jwt_required()
    def delete(self, asset_id):
        """删除资产"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        # 权限检查
        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and user.role not in ASSET_MANAGE_ROLES:
            return {'code': 403, 'message': '无权限删除'}, 403

        asset.status = 'deleted'
        # 删除后撤销仍然有效的授权，避免继续下载
        License.query.filter_by(asset_id=asset_id, status='active').update(
            {'status': 'revoked'}, synchronize_session=False
        )
        db.session.commit()

        OperationLog.log(
            user=user,
            action='delete',
            module='asset',
            description=f'删除资产: {asset.asset_code}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        return {'code': 200, 'message': '删除成功'}, 200


class AssetUploadResource(Resource):
    """资产上传"""

    @jwt_required()
    @rate_limit(limit=10, window=60)
    def post(self):
        """上传资产"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        # 检查文件
        if 'file' not in request.files:
            return {'code': 400, 'message': '未上传文件'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'code': 400, 'message': '未选择文件'}, 400

        # 获取表单数据
        title = request.form.get('title')
        description = request.form.get('description', '')
        asset_type = request.form.get('asset_type', 'image')
        garden_id = request.form.get('garden_id', type=int)

        if not title:
            return {'code': 400, 'message': '标题不能为空'}, 400

        # 检查文件类型（扩展名 + 魔术字节双重验证）
        if not allowed_file(file.filename, asset_type):
            return {'code': 400, 'message': '不支持的文件类型'}, 400

        original_name = file.filename or ''
        if '.' not in original_name:
            return {'code': 400, 'message': '文件名缺少扩展名'}, 400
        ext = original_name.rsplit('.', 1)[1].lower()
        if not validate_magic_bytes(file, ext):
            return {'code': 400, 'message': '文件内容与扩展名不匹配'}, 400

        # 文件大小检查 (500MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 500 * 1024 * 1024)
        if file_size > max_size:
            return {'code': 400, 'message': f'文件大小超过限制 ({max_size // 1024 // 1024}MB)'}, 400

        # 计算文件哈希（用于去重）
        file_hash = calculate_file_hash(file)

        # 检查是否已存在相同文件。只向有权限查看该资产的人返回 ID，
        # 避免通过哈希探测他人草稿/已删除资产。
        existing = Asset.query.filter_by(file_hash=file_hash).first()
        if existing:
            visible = user and (
                user.role in ADMIN_ROLES
                or user_id in (existing.creator_id, existing.owner_id, existing.uploader_id)
            )
            data = None
            if visible:
                data = {
                    'existing_asset_id': existing.id,
                    'asset_code': existing.asset_code,
                    'status': existing.status
                }
            return {
                'code': 400,
                'message': '该文件已上传过，请勿重复上传',
                'data': data
            }, 400

        # 生成文件名和路径（UUID + 已验证扩展名；中文原名会被 secure_filename 剥掉扩展名）
        new_filename = f"{uuid.uuid4().hex}.{ext}"

        # 获取园林编码
        from app.models.garden import Garden
        garden = Garden.query.get(garden_id) if garden_id else None
        garden_code = garden.code if garden else 'GEN'

        # 生成资产编码
        asset_code = generate_asset_code(garden_code, asset_type)

        # 保存文件
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads')
        date_folder = datetime.now().strftime('%Y/%m/%d')
        save_dir = os.path.join(upload_folder, date_folder)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        file_path = os.path.join(save_dir, new_filename)
        file.save(file_path)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 创建资产记录
        asset = Asset(
            asset_code=asset_code,
            title=title,
            description=description,
            asset_type=asset_type,
            file_format=ext.upper(),
            file_size=file_size,
            file_hash=file_hash,
            storage_path=file_path,
            garden_id=garden_id,
            creator_id=user_id,
            uploader_id=user_id,
            owner_id=user_id,
            status='draft'
        )

        db.session.add(asset)
        db.session.flush()

        # 标签是可选字段，格式错误不应阻断上传
        tags_raw = request.form.get('tags')
        if tags_raw:
            try:
                tag_names = json.loads(tags_raw)
            except (TypeError, ValueError):
                tag_names = []
            if isinstance(tag_names, list):
                for tag_name in tag_names[:20]:
                    name = str(tag_name).strip()[:50]
                    if name:
                        db.session.add(AssetTag(asset_id=asset.id, name=name))

        # 缩略图失败不应影响上传本身，前端会在缺图时回退到占位图
        if asset_type == 'image':
            try:
                from app.utils.thumbnails import generate_thumbnail_set
                detail_path, _ = generate_thumbnail_set(file_path, asset.id)
                asset.thumbnail_path = detail_path
            except Exception as e:
                current_app.logger.warning(f'缩略图生成失败: {e}', exc_info=True)

        # 初始版本与资产在同一事务内入库，保证资产一定有 v1
        db.session.add(AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path=os.path.abspath(file_path),
            file_name=original_name[:255],
            file_format=ext.upper(),
            file_size=file_size,
            file_hash=file_hash,
            thumbnail_path=asset.thumbnail_path,
            change_note='初始版本',
            created_by=user_id
        ))

        db.session.commit()

        # 记录日志
        OperationLog.log(
            user=user,
            action='upload',
            module='asset',
            description=f'上传资产: {asset_code}',
            target_type='asset',
            target_id=asset.id,
            request=request
        )

        return {
            'code': 200,
            'message': '上传成功',
            'data': {
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'file_hash': file_hash
            }
        }, 200


class AssetRelatedResource(Resource):
    """同园林的相关资产"""

    @jwt_required()
    def get(self, asset_id):
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '资产不存在'}, 404

        query = Asset.query.filter(
            Asset.id != asset.id,
            Asset.status == 'published'
        )
        if asset.garden_id:
            query = query.filter(Asset.garden_id == asset.garden_id)
        related = query.order_by(Asset.view_count.desc(), Asset.created_at.desc()).limit(4).all()

        return {'code': 200, 'data': [item.to_dict() for item in related]}, 200


class AssetThumbnailResource(Resource):
    """资产缩略图（公开只读，URL 使用不可枚举的资产 UUID）"""

    def get(self, asset_id):
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '缩略图不存在'}, 404

        try:
            safe_id = str(uuid.UUID(str(asset_id)))
        except (ValueError, TypeError, AttributeError):
            return {'code': 404, 'message': '缩略图不存在'}, 404

        from flask import send_from_directory
        from app.utils.thumbnails import thumbnail_dir

        # 列表用 640px 卡片图，详情用 1600px 大图；旧数据缺少卡片图时回退到大图
        size = (request.args.get('size') or '').strip()
        filename = f'{safe_id}-card.jpg' if size == 'card' else f'{safe_id}.jpg'
        full_path = os.path.join(thumbnail_dir(), filename)
        if not os.path.isfile(full_path):
            if size != 'card':
                return {'code': 404, 'message': '缩略图不存在'}, 404
            filename = f'{safe_id}.jpg'
            if not os.path.isfile(os.path.join(thumbnail_dir(), filename)):
                return {'code': 404, 'message': '缩略图不存在'}, 404

        return send_from_directory(
            thumbnail_dir(),
            filename,
            mimetype='image/jpeg',
            conditional=True,
            max_age=86400
        )


class AssetDownloadResource(Resource):
    """资产下载"""

    @jwt_required()
    def get(self, asset_id):
        """下载资产"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)

        # 所有者与管理员可下载未发布资产；已删除仅管理员可见
        if asset.status == 'deleted' and user.role not in ADMIN_ROLES:
            return {'code': 404, 'message': '资产不存在'}, 404
        if asset.status != 'published' and not (is_owner or user.role in ADMIN_ROLES):
            return {'code': 403, 'message': '资产未发布'}, 403

        # 检查下载权限：有效授权未过期，或本人/管理员
        from app.models.license import License
        now = datetime.utcnow()
        has_license = License.query.filter(
            License.asset_id == asset_id,
            License.licensee_id == user_id,
            License.status == 'active',
            License.start_time <= now,
            or_(License.end_time.is_(None), License.end_time > now),
        ).first()

        if not has_license and not is_owner and user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无下载权限，请先申请授权'}, 403

        # 先确认文件存在，避免“下载失败但下载量已经增加”
        file_path = os.path.abspath(asset.watermarked_path or asset.storage_path or '')
        if not file_path or not os.path.exists(file_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        # 记录下载（关联本次使用的授权，便于后续审计）
        from app.models.extra import DownloadRecord
        record = DownloadRecord(
            asset_id=asset_id,
            user_id=user_id,
            license_id=has_license.id if has_license else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(record)
        asset.download_count += 1
        db.session.commit()

        OperationLog.log(
            user=user,
            action='download',
            module='asset',
            description=f'下载资产: {asset.asset_code}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        from flask import send_file as flask_send_file

        # 水印副本可能被转成 PNG；下载名必须跟随实际文件，而不是原始扩展名
        actual_ext = os.path.splitext(file_path)[1].lstrip('.').lower()
        download_ext = actual_ext or (asset.file_format or '').lower()
        download_name = f"{asset.asset_code}.{download_ext}" if download_ext else asset.asset_code

        return flask_send_file(
            file_path,
            as_attachment=True,
            download_name=download_name
        )


class FavoriteListResource(Resource):
    """当前用户的收藏列表"""

    @jwt_required()
    def get(self):
        from app.models.extra import Favorite

        user_id = get_jwt_identity()
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)

        query = Favorite.query.join(Asset, Favorite.asset_id == Asset.id).filter(
            Favorite.user_id == user_id,
            Asset.status != 'deleted'
        ).order_by(Favorite.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        items = []
        for favorite in pagination.items:
            data = favorite.asset.to_dict()
            data['favorited_at'] = favorite.created_at.isoformat() if favorite.created_at else None
            items.append(data)

        return {
            'code': 200,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'per_page': per_page
            }
        }, 200


class AssetFavoriteResource(Resource):
    """资产收藏"""

    @jwt_required()
    def get(self, asset_id):
        """查询当前用户是否已收藏"""
        from app.models.extra import Favorite

        user_id = get_jwt_identity()
        asset = Asset.query.get(asset_id)
        if not asset or asset.status == 'deleted':
            return {'code': 404, 'message': '资产不存在'}, 404

        favorited = Favorite.query.filter_by(user_id=user_id, asset_id=asset_id).first() is not None
        count = Favorite.query.filter_by(asset_id=asset_id).count()
        return {'code': 200, 'data': {'favorited': favorited, 'count': count}}, 200

    @jwt_required()
    def post(self, asset_id):
        """添加收藏"""
        user_id = get_jwt_identity()
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        from app.models.extra import Favorite
        existing = Favorite.query.filter_by(
            user_id=user_id,
            asset_id=asset_id
        ).first()

        if existing:
            count = Favorite.query.filter_by(asset_id=asset_id).count()
            return {'code': 200, 'message': '已收藏', 'data': {'favorited': True, 'count': count}}, 200

        favorite = Favorite(
            user_id=user_id,
            asset_id=asset_id,
            created_at=datetime.utcnow()
        )
        db.session.add(favorite)
        asset.favorite_count = (asset.favorite_count or 0) + 1
        db.session.commit()

        count = Favorite.query.filter_by(asset_id=asset_id).count()
        return {'code': 200, 'message': '收藏成功', 'data': {'favorited': True, 'count': count}}, 200

    @jwt_required()
    def delete(self, asset_id):
        """取消收藏（幂等）"""
        user_id = get_jwt_identity()

        from app.models.extra import Favorite
        favorite = Favorite.query.filter_by(
            user_id=user_id,
            asset_id=asset_id
        ).first()

        asset = Asset.query.get(asset_id)
        if favorite:
            if asset:
                asset.favorite_count = max((asset.favorite_count or 0) - 1, 0)
            db.session.delete(favorite)
            db.session.commit()

        count = Favorite.query.filter_by(asset_id=asset_id).count()
        return {'code': 200, 'message': '取消收藏成功', 'data': {'favorited': False, 'count': count}}, 200


class AssetStatsResource(Resource):
    """资产统计（管理后台仪表盘数据）"""

    @jwt_required()
    def get(self):
        """获取资产统计数据"""
        from datetime import datetime, timedelta

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if user.role not in ADMIN_ROLES:
            return {'code': 403, 'message': '无权限'}, 403

        # 统计数据
        total = Asset.query.filter(Asset.status != 'deleted').count()
        by_type = {}
        for type_name in ['image', 'model', 'vector', 'document', 'video']:
            by_type[type_name] = Asset.query.filter_by(
                asset_type=type_name,
                status='published'
            ).count()

        by_status = {}
        for status in ['draft', 'pending', 'published', 'rejected']:
            by_status[status] = Asset.query.filter_by(status=status).count()

        # 水印和区块链统计
        watermarked = Asset.query.filter(Asset.watermark_id.isnot(None)).count()
        chained = Asset.query.filter(Asset.chain_tx_hash.isnot(None)).count()

        # 待审批授权数量
        pending_licenses = LicenseApplication.query.filter_by(status='pending').count()

        # 按创建时间统计类型分布（本周 / 本月），供仪表盘切换使用
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        def count_by_type(since):
            rows = db.session.query(
                Asset.asset_type, func.count(Asset.id)
            ).filter(
                Asset.status == 'published',
                Asset.created_at >= since
            ).group_by(Asset.asset_type).all()
            counts = {name: 0 for name in ['image', 'model', 'vector', 'document', 'video']}
            for asset_type, count in rows:
                counts[asset_type] = count
            return counts

        by_type_week = count_by_type(week_ago)
        by_type_month = count_by_type(month_ago)

        # 水印嵌入趋势（最近30天，前端按周/月截取）
        watermark_trends = db.session.query(
            func.date(Asset.watermark_embedded_at).label('date'),
            func.count(Asset.id).label('count')
        ).filter(
            Asset.watermark_embedded_at >= month_ago,
            Asset.watermark_status.in_(['embedded', 'verified'])
        ).group_by(
            func.date(Asset.watermark_embedded_at)
        ).order_by(
            func.date(Asset.watermark_embedded_at)
        ).all()

        # 最近活动
        recent_activities = OperationLog.query.filter(
            OperationLog.status == 'success'
        ).order_by(OperationLog.created_at.desc()).limit(10).all()

        # 最近上传
        recent = Asset.query.filter(
            Asset.status != 'deleted'
        ).order_by(Asset.created_at.desc()).limit(10).all()

        return {
            'code': 200,
            'data': {
                'total': total,
                'by_type': by_type,
                'by_type_week': by_type_week,
                'by_type_month': by_type_month,
                'by_status': by_status,
                'watermarked': watermarked,
                'chained': chained,
                'pending_licenses': pending_licenses,
                'watermark_trends': [
                    {'date': str(d), 'count': c} for d, c in watermark_trends
                ],
                'recent_activities': [a.to_dict() for a in recent_activities],
                'recent': [a.to_dict() for a in recent]
            }
        }, 200


class MyAssetsResource(Resource):
    """我的资产"""

    @jwt_required()
    def get(self):
        """获取用户自己的资产列表"""
        user_id = get_jwt_identity()
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        status = (request.args.get('status') or '').strip()

        query = Asset.query.filter_by(creator_id=user_id)

        if status:
            if status not in ASSET_STATUSES:
                return {'code': 400, 'message': '无效的状态筛选'}, 400
            query = query.filter_by(status=status)
        else:
            query = query.filter(Asset.status != 'deleted')

        query = query.order_by(Asset.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'code': 200,
            'data': {
                'items': [asset.to_dict() for asset in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page
            }
        }, 200


class AssetTagsResource(Resource):
    """资产标签"""

    @jwt_required()
    def get(self, asset_id):
        """获取资产标签"""
        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        tags = AssetTag.query.filter_by(asset_id=asset_id).all()
        return {
            'code': 200,
            'data': [{'id': t.id, 'name': t.name} for t in tags]
        }, 200

    @jwt_required()
    def post(self, asset_id):
        """添加标签"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and user.role not in ASSET_MANAGE_ROLES:
            return {'code': 403, 'message': '无权限修改标签'}, 403

        data = request.get_json() or {}
        tags = data.get('tags', [])
        if not isinstance(tags, list) or len(tags) > 20:
            return {'code': 400, 'message': '标签格式错误'}, 400

        for tag_name in tags:
            existing = AssetTag.query.filter_by(
                asset_id=asset_id,
                name=tag_name
            ).first()
            if not existing:
                tag = AssetTag(
                    asset_id=asset_id,
                    name=tag_name
                )
                db.session.add(tag)

        db.session.commit()

        return {'code': 200, 'message': '标签添加成功'}, 200


class AssetPublishResource(Resource):
    """资产发布"""

    @jwt_required()
    def post(self, asset_id):
        """提交发布申请"""
        user_id = get_jwt_identity()
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        if user_id not in (asset.creator_id, asset.owner_id, asset.uploader_id):
            return {'code': 403, 'message': '无权限'}, 403

        if asset.status not in ('draft', 'rejected'):
            return {'code': 400, 'message': '只有草稿或已驳回的资产才能提交发布'}, 400

        if asset.asset_type in ('image', 'vector') and asset.watermark_status not in ('embedded', 'verified'):
            return {'code': 400, 'message': '提交发布前请先完成水印嵌入'}, 400

        asset.status = 'pending'
        asset.reject_reason = None

        reviewers = User.query.filter(
            User.role.in_(('admin', 'asset_admin')),
            User.status == 'active'
        ).all()
        for reviewer in reviewers:
            add_notification_event(
                reviewer.id,
                'asset_pending',
                '有新的资产待审核',
                f'{asset.asset_code} · {asset.title}',
                '/admin/assets?status=pending'
            )

        db.session.commit()

        return {'code': 200, 'message': '提交发布成功，等待审核'}, 200


class AssetApproveResource(Resource):
    """资产审核"""

    @jwt_required()
    def post(self, asset_id):
        """审核资产"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        if user.role not in ('admin', 'asset_admin', 'adm1', 'adm2'):
            return {'code': 403, 'message': '无审核权限'}, 403

        # 执行“上传者与审核人分离”，避免自己审核自己的资产
        if user_id in (asset.creator_id, asset.uploader_id):
            return {'code': 403, 'message': '不能审核自己上传的资产'}, 403

        if asset.status != 'pending':
            return {'code': 400, 'message': '只有待审核状态才能审核'}, 400

        data = request.get_json()
        action = data.get('action')  # approve 或 reject
        reason = data.get('reason', '')

        if action == 'approve':
            asset.status = 'published'
            asset.approver_id = user_id
            asset.approve_time = datetime.utcnow()
            asset.publish_at = datetime.utcnow()
        elif action == 'reject':
            asset.status = 'rejected'
            asset.reject_reason = reason
        else:
            return {'code': 400, 'message': '无效操作'}, 400

        recipient_id = asset.uploader_id or asset.creator_id or asset.owner_id
        if action == 'approve':
            add_notification_event(
                recipient_id,
                'asset_approved',
                '资产审核通过',
                f'《{asset.title}》已发布到资产档案',
                f'/assets/{asset_id}'
            )
        else:
            add_notification_event(
                recipient_id,
                'asset_rejected',
                '资产审核未通过',
                f'《{asset.title}》 · {reason or "请查看资产详情"}',
                f'/assets/{asset_id}'
            )

        db.session.commit()

        OperationLog.log(
            user=user,
            action=action,
            module='asset',
            description=f'审核资产: {asset.asset_code}, 结果: {action}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        return {'code': 200, 'message': '审核完成'}, 200