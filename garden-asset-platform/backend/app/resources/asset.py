"""
资产相关API资源
"""
import os
import uuid
import hashlib
import json
import mimetypes
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
from app.utils.paths import VERSION_EXT_ALIASES, canonical_extension, uuid_filename
from app.services.notification_service import add_notification_event
from app.services.object_storage import (
    delete_ref_quietly,
    is_object_ref,
    ref_exists,
    send_ref,
    send_ref_range,
    store_original,
)
from app.services.upload_session_service import (
    UPLOAD_LEASE_SECONDS,
    calculate_prefix_hash,
    calculate_upload_fingerprint,
    claim_upload_session,
    clear_upload_lease,
    lease_is_valid,
    normalize_fingerprint,
    purge_stale_upload_sessions,
    remove_session_files,
    remove_upload_session_dir,
    upload_session_lock,
)
from sqlalchemy import case, func, or_, update


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


# 常见文件类型的魔术字节：每个格式可由多组规则匹配，每组规则是
# (偏移, 签名) 的列表，列表内全部命中才算匹配。
ZIP_SIGNATURES = [
    [(0, b'PK\x03\x04')],
    [(0, b'PK\x05\x06')],
    [(0, b'PK\x07\x08')],
]
OLE_SIGNATURE = [[(0, b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')]]

MAGIC_RULES = {
    # 图片
    'jpg': [[(0, b'\xff\xd8\xff')]],
    'jpeg': [[(0, b'\xff\xd8\xff')]],
    'png': [[(0, b'\x89PNG\r\n\x1a\n')]],
    'gif': [[(0, b'GIF87a')], [(0, b'GIF89a')]],
    'bmp': [[(0, b'BM')]],
    'webp': [[(0, b'RIFF'), (8, b'WEBP')]],
    'tiff': [[(0, b'II*\x00')], [(0, b'MM\x00*')]],
    # 文档
    'pdf': [[(0, b'%PDF')]],
    'doc': OLE_SIGNATURE,
    'xls': OLE_SIGNATURE,
    'ppt': OLE_SIGNATURE,
    'docx': ZIP_SIGNATURES,
    'xlsx': ZIP_SIGNATURES,
    'pptx': ZIP_SIGNATURES,
    'dwg': [[(0, b'AC10')]],
    # 视频
    'mp4': [[(4, b'ftyp')]],
    'mov': [[(4, b'ftyp'), (8, b'qt  ')]],
    'avi': [[(0, b'RIFF'), (8, b'AVI ')]],
    'mkv': [[(0, b'\x1a\x45\xdf\xa3')]],
    # 矢量
    'shp': [[(0, b'\x00\x00\x27\x0a')]],
    'kmz': ZIP_SIGNATURES,
    'zip': ZIP_SIGNATURES,
    # 3D模型
    'glb': [[(0, b'glTF')]],
    'fbx': [[(0, b'Kaydara FBX Binary')]],
}

# 文本类格式不能只看扩展名，至少要求头部没有 NUL 字节
TEXT_EXTENSIONS = {'obj', 'geojson', 'gltf', 'kml', 'dxf', 'txt', 'md'}

_MAGIC_HEADER_SIZE = 64


def _text_header(header):
    return header.lstrip(b'\xef\xbb\xbf \t\r\n')


def _magic_matches(header, ext, size):
    """判断文件头是否匹配扩展名对应的白名单签名。"""
    if size <= 0:
        return False
    if ext == 'stl':
        # ASCII STL 以 solid 开头；二进制 STL 没有稳定魔数，
        # 至少要求满足 80 字节头 + 4 字节面片数的结构。
        return header.startswith(b'solid') or size >= 84
    if ext == 'obj':
        return _text_header(header).startswith((
            b'#', b'v ', b'f ', b'o ', b'g ', b's ', b'l ',
            b'mtllib', b'usemtl',
        ))
    if ext in ('geojson', 'gltf'):
        return _text_header(header).startswith(b'{')
    if ext == 'kml':
        return _text_header(header).startswith((b'<?xml', b'<kml'))
    if ext == 'dxf':
        return (
            _text_header(header).startswith(b'0')
            or header.startswith(b'AutoCAD Binary DXF')
        )
    if ext == 'fbx':
        return _text_header(header).startswith(b'; FBX') or header.startswith(
            b'Kaydara FBX Binary'
        )
    if ext in ('txt', 'md'):
        return b'\x00' not in header
    rules = MAGIC_RULES.get(ext)
    if not rules:
        return False
    return any(
        all(header[offset:offset + len(signature)] == signature
            for offset, signature in rule)
        for rule in rules
    )


def validate_magic_bytes(file, ext):
    """通过魔术字节验证文件类型"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    header = file.read(_MAGIC_HEADER_SIZE)
    file.seek(0)
    return _magic_matches(header, ext, size)


def calculate_file_hash(file):
    """计算文件SHA256哈希"""
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b''):
        sha256.update(chunk)
    file.seek(0)  # 重置指针
    return sha256.hexdigest()


def validate_magic_bytes_path(path, ext):
    """对已落盘文件做魔术字节校验。"""
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as handle:
            header = handle.read(_MAGIC_HEADER_SIZE)
    except OSError:
        return False
    return _magic_matches(header, ext, size)


def calculate_file_hash_path(path):
    """对已落盘文件计算 SHA-256。"""
    sha256 = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            sha256.update(chunk)
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
                Asset.tags.any(or_(
                    AssetTag.name.ilike(like), AssetTag.tag_name.ilike(like)
                )),
                Asset.garden.has(or_(
                    Garden.name.ilike(like), Garden.code.ilike(like)
                )),
                Asset.uploader.has(or_(
                    User.username.ilike(like), User.nickname.ilike(like)
                )),
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

        # 排序：带关键词且未指定排序时按相关度，标题/编码命中优先
        sort = (request.args.get('sort') or ('relevance' if keyword else 'newest')).strip()
        if sort == 'oldest':
            query = query.order_by(Asset.created_at.asc())
        elif sort == 'popular':
            query = query.order_by(Asset.view_count.desc(), Asset.created_at.desc())
        elif sort == 'downloads':
            query = query.order_by(Asset.download_count.desc(), Asset.created_at.desc())
        elif sort == 'relevance' and keyword:
            like = f'%{keyword}%'
            relevance = case(
                (Asset.title.ilike(like), 5),
                (Asset.asset_code.ilike(like), 4),
                (Asset.description.ilike(like), 2),
                else_=1,
            )
            query = query.order_by(relevance.desc(), Asset.created_at.desc())
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

        # 标签为整体替换：先校验，避免部分字段已修改后才报错
        normalized_tags = None
        if 'tags' in data:
            raw_tags = data.get('tags')
            if not isinstance(raw_tags, list) or len(raw_tags) > 20:
                return {'code': 400, 'message': '标签格式错误'}, 400
            normalized_tags = []
            for raw_tag in raw_tags:
                name = str(raw_tag).strip()[:50]
                if name and name not in normalized_tags:
                    normalized_tags.append(name)

        # 更新字段
        if 'title' in data:
            asset.title = data['title']
        if 'description' in data:
            asset.description = data['description']
        if normalized_tags is not None:
            AssetTag.query.filter_by(asset_id=asset_id).delete(
                synchronize_session=False
            )
            for name in normalized_tags:
                db.session.add(AssetTag(asset_id=asset_id, name=name))

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

        if asset.status != 'deleted':
            asset.previous_status = asset.status
            asset.deleted_at = datetime.utcnow()
        asset.deleted_by = user_id
        asset.status = 'deleted'

        # 删除后撤销仍然有效的授权，通知被授权方；同时取消待审申请
        active_licenses = License.query.filter_by(
            asset_id=asset_id, status='active'
        ).all()
        for license_row in active_licenses:
            license_row.status = 'revoked'
            add_notification_event(
                license_row.licensee_id,
                'license_revoked',
                '资产已删除，授权已撤销',
                f'《{asset.title}》已从平台删除，原授权停止使用',
                '/license/my'
            )
        pending_apps = LicenseApplication.query.filter(
            LicenseApplication.asset_id == asset_id,
            LicenseApplication.status.in_(('pending', 'adm1_approved'))
        ).all()
        for application in pending_apps:
            application.status = 'cancelled'
            add_notification_event(
                application.applicant_id,
                'license_rejected',
                '资产已删除，申请已取消',
                f'《{asset.title}》已从平台删除',
                '/license/my?tab=applications'
            )

        # 排队中的水印/存证任务不再有执行意义
        from app.models.task import AsyncTask
        AsyncTask.query.filter_by(asset_id=asset_id, status='queued').update(
            {'status': 'cancelled'}, synchronize_session=False
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

        return {'code': 200, 'message': '资产已移入回收站，可联系管理员恢复'}, 200


class AssetRestoreResource(Resource):
    """恢复已删除资产（退回草稿，授权不自动恢复）"""

    @jwt_required()
    def post(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404
        if asset.status != 'deleted':
            return {'code': 400, 'message': '该资产不在回收站'}, 400

        is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
        if not is_owner and user.role not in ASSET_MANAGE_ROLES:
            return {'code': 403, 'message': '无权限恢复'}, 403

        asset.status = 'draft'
        asset.deleted_at = None
        asset.deleted_by = None
        asset.previous_status = None
        db.session.commit()

        OperationLog.log(
            user=user,
            action='restore',
            module='asset',
            description=f'恢复资产: {asset.asset_code}',
            target_type='asset',
            target_id=asset_id,
            request=request
        )

        owner_id = asset.owner_id or asset.creator_id or asset.uploader_id
        if owner_id and owner_id != user_id:
            add_notification_event(
                owner_id,
                'asset_restored',
                '资产已恢复',
                f'《{asset.title}》已由管理员恢复到草稿，请重新完成发布流程',
                f'/assets/{asset.id}'
            )
            db.session.commit()

        return {
            'code': 200,
            'message': '资产已恢复为草稿，请重新水印/存证并提交发布',
            'data': asset.to_dict()
        }, 200


class AssetUploadResource(Resource):
    """资产上传"""

    @jwt_required()
    @rate_limit(limit=120, window=60)
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
        existing = Asset.query.filter(
            Asset.file_hash == file_hash,
            Asset.status != 'deleted',
        ).first()
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
            current_version_no=1,
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

        # 初始版本与资产在同一事务内入库，保证资产一定有 v1。
        # 对象存储只决定新写位置；缩略图仍基于刚保存的本地文件生成。
        storage_ref = store_original(file_path, asset.id, f'.{ext}', kind='original')
        asset.storage_path = storage_ref
        db.session.add(AssetVersion(
            asset_id=asset.id,
            version_no=1,
            file_path=storage_ref,
            file_name=original_name[:255],
            file_format=ext.upper(),
            file_size=file_size,
            file_hash=file_hash,
            thumbnail_path=asset.thumbnail_path,
            change_note='初始版本',
            created_by=user_id
        ))

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            if is_object_ref(storage_ref):
                delete_ref_quietly(storage_ref)
            raise

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


def _create_asset_from_saved_file(
    user_id, title, description, asset_type, garden_id, original_name,
    ext, file_path, file_hash, file_size, tag_names, commit=True
):
    """把已落盘文件登记为资产（含 v1 与缩略图），由上传/断点续传共用。

    commit=False 时只 flush，由调用方把资产、v1 与会话状态放在同一事务提交。
    """
    from app.models.garden import Garden

    garden = Garden.query.get(garden_id) if garden_id else None
    garden_code = garden.code if garden else 'GEN'
    asset_code = generate_asset_code(garden_code, asset_type)

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
        current_version_no=1,
        status='draft',
    )
    db.session.add(asset)
    db.session.flush()

    seen = set()
    for raw_name in (tag_names or [])[:20]:
        name = str(raw_name).strip()[:50]
        if name and name not in seen:
            seen.add(name)
            db.session.add(AssetTag(asset_id=asset.id, name=name))

    if asset_type == 'image':
        try:
            from app.utils.thumbnails import generate_thumbnail_set
            detail_path, _ = generate_thumbnail_set(file_path, asset.id)
            asset.thumbnail_path = detail_path
        except Exception as exc:
            current_app.logger.warning(
                '缩略图生成失败: %s', exc, exc_info=True
            )

    storage_ref = store_original(file_path, asset.id, f'.{ext}', kind='original')
    asset.storage_path = storage_ref
    db.session.add(AssetVersion(
        asset_id=asset.id,
        version_no=1,
        file_path=storage_ref,
        file_name=(original_name or '')[:255],
        file_format=ext.upper(),
        file_size=file_size,
        file_hash=file_hash,
        thumbnail_path=asset.thumbnail_path,
        change_note='初始版本',
        created_by=user_id,
    ))
    try:
        if commit:
            db.session.commit()
        else:
            db.session.flush()
    except Exception:
        if is_object_ref(storage_ref):
            delete_ref_quietly(storage_ref)
        raise
    return asset


class AssetUploadSessionResource(Resource):
    """创建/查询断点续传会话"""

    @jwt_required()
    @rate_limit(limit=120, window=60)
    def post(self):
        from app.models.extra import UploadSession

        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        filename = str(data.get('filename') or '').strip()
        title = str(data.get('title') or '').strip()
        asset_type = str(data.get('asset_type') or 'image').strip()
        expected_size = data.get('size')
        garden_id = data.get('garden_id')
        tags = data.get('tags') or []

        if not filename or not title:
            return {'code': 400, 'message': '文件名和标题不能为空'}, 400
        if not isinstance(expected_size, int) or expected_size <= 0:
            return {'code': 400, 'message': '文件大小无效'}, 400
        if not allowed_file(filename, asset_type):
            return {'code': 400, 'message': '不支持的文件类型'}, 400
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 500 * 1024 * 1024)
        if expected_size > max_size:
            return {
                'code': 400,
                'message': f'文件大小超过限制 ({max_size // 1024 // 1024}MB)'
            }, 400
        if not isinstance(tags, list):
            return {'code': 400, 'message': '标签格式错误'}, 400
        fingerprint = normalize_fingerprint(data.get('fingerprint'))
        if data.get('fingerprint') and not fingerprint:
            return {'code': 400, 'message': '文件指纹格式无效'}, 400
        tags = [
            str(tag).strip()[:50] for tag in tags[:20] if str(tag).strip()
        ]
        if garden_id is not None:
            try:
                garden_id = int(garden_id)
            except (TypeError, ValueError):
                return {'code': 400, 'message': '园林参数无效'}, 400
            if not db.session.get(Garden, garden_id):
                return {'code': 400, 'message': '园林不存在'}, 400

        canonical_ext = canonical_extension(filename, VERSION_EXT_ALIASES)
        if not canonical_ext:
            return {'code': 400, 'message': '不支持的文件类型'}, 400

        # 先回收该用户长期未更新的会话，避免临时目录无限累积
        purge_stale_upload_sessions(user_id=user_id)

        upload_id = uuid.uuid4().hex
        upload_root = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', './uploads'),
            'resumable',
        )
        session_dir = os.path.join(upload_root, upload_id)
        temp_path = os.path.join(session_dir, 'data.part')
        try:
            os.makedirs(session_dir, exist_ok=True)
            with open(temp_path, 'wb'):
                pass

            session = UploadSession(
                id=upload_id,
                user_id=user_id,
                filename=filename[:255],
                asset_type=asset_type,
                title=title[:255],
                description=str(data.get('description') or '')[:2000],
                garden_id=garden_id,
                tags_json=json.dumps(tags[:20], ensure_ascii=False),
                expected_size=expected_size,
                received_size=0,
                chunk_size=current_app.config.get(
                    'RESUMABLE_CHUNK_SIZE', 4 * 1024 * 1024
                ),
                temp_path=temp_path,
                file_fingerprint=fingerprint,
                status='uploading',
            )
            db.session.add(session)
            db.session.commit()
        except Exception:
            db.session.rollback()
            remove_upload_session_dir(upload_id)
            raise
        return {
            'code': 200,
            'message': '上传会话已创建',
            'data': session.to_dict(),
        }, 200


class AssetUploadSessionClaimResource(Resource):
    """认领未完成会话并签发短期写入租约"""

    @jwt_required()
    @rate_limit(limit=120, window=60)
    def post(self, upload_id):
        from app.models.extra import UploadSession
        data = request.get_json(silent=True) or {}
        fingerprint = normalize_fingerprint(data.get('fingerprint'))
        if data.get('fingerprint') and not fingerprint:
            return {'code': 400, 'message': '文件指纹格式无效'}, 400
        try:
            with upload_session_lock(upload_id):
                session = db.session.get(UploadSession, upload_id)
                if not session or session.user_id != get_jwt_identity():
                    return {'code': 404, 'message': '上传会话不存在'}, 404
                if session.status != 'uploading':
                    return {'code': 409, 'message': '上传会话已结束'}, 409
                supplied_lease = data.get('lease_token')
                if session.file_fingerprint and fingerprint != session.file_fingerprint:
                    return {
                        'code': 409,
                        'message': '所选文件内容与未完成上传不一致，请选择原文件'
                    }, 409
                if (
                    session.lease_token
                    and supplied_lease != session.lease_token
                    and lease_is_valid(session)
                ):
                    return {
                        'code': 409,
                        'error': 'upload_lease_required',
                        'message': '该文件正在其他页面续传，请稍后重试',
                        'data': {
                            'received_size': session.received_size,
                            'lease_expires_at': (
                                session.lease_expires_at.isoformat()
                            ),
                        },
                    }, 409
                # 旧会话没有指纹时，至少核对已接收文件头；完成时还会
                # 对完整文件做 SHA-256 校验。
                if (
                    not session.file_fingerprint
                    and fingerprint
                    and session.received_size >= 64 * 1024
                ):
                    prefix = str(data.get('prefix_hash') or '').lower()
                    if (
                        not normalize_fingerprint(prefix)
                        or calculate_prefix_hash(session.temp_path) != prefix
                    ):
                        return {
                            'code': 409,
                            'message': '所选文件与已上传内容不一致，请重新选择原文件'
                        }, 409
                token, error = claim_upload_session(session, fingerprint)
                if error:
                    return {'code': 409, 'message': error}, 409
                db.session.commit()
                return {
                    'code': 200,
                    'data': {
                        **session.to_dict(),
                        'lease_token': token,
                        'lease_expires_in': UPLOAD_LEASE_SECONDS,
                    },
                }, 200
        except TimeoutError as exc:
            return {'code': 409, 'message': str(exc)}, 409


class AssetUploadSessionListResource(Resource):
    """列出当前用户未完成的上传会话（页面刷新/换设备后恢复）"""

    @jwt_required()
    def get(self):
        from app.models.extra import UploadSession

        user_id = get_jwt_identity()
        purge_stale_upload_sessions(user_id=user_id)
        sessions = UploadSession.query.filter_by(
            user_id=user_id, status='uploading'
        ).order_by(UploadSession.updated_at.desc()).limit(20).all()
        return {
            'code': 200,
            'data': {
                'items': [session.to_dict() for session in sessions],
                'ttl_hours': current_app.config.get(
                    'UPLOAD_SESSION_TTL_HOURS', 48
                ),
            },
        }, 200


def _upload_lease_error(session):
    if not session.lease_token:
        return None
    if not lease_is_valid(session):
        return {
            'code': 409,
            'error': 'upload_lease_required',
            'message': '上传租约已过期，请重新认领会话',
        }, 409
    if request.headers.get('X-Upload-Lease') != session.lease_token:
        return {
            'code': 409,
            'error': 'upload_lease_required',
            'message': '该文件正在其他页面续传，请稍后重试',
        }, 409
    return None


class AssetUploadSessionDetailResource(Resource):
    """查询状态、追加分块或取消会话"""

    @jwt_required()
    def get(self, upload_id):
        from app.models.extra import UploadSession
        session = db.session.get(UploadSession, upload_id)
        if not session or session.user_id != get_jwt_identity():
            return {'code': 404, 'message': '上传会话不存在'}, 404
        return {'code': 200, 'data': session.to_dict()}, 200

    @jwt_required()
    @rate_limit(limit=240, window=60)
    def put(self, upload_id):
        # 先读完请求体再拿会话锁：慢速网络中传输分块可能耗时很久，
        # 持锁期间只做文件写入与数据库提交。
        chunk = request.get_data(cache=False)
        if not chunk:
            return {'code': 400, 'message': '分块内容为空'}, 400
        try:
            with upload_session_lock(upload_id):
                return self._append_chunk(upload_id, chunk)
        except TimeoutError as exc:
            return {'code': 409, 'message': str(exc)}, 409

    @jwt_required()
    @rate_limit(limit=60, window=60)
    def patch(self, upload_id):
        """续传前同步用户当前填写的标题、园林、描述与标签。"""
        from app.models.extra import UploadSession
        session = db.session.get(UploadSession, upload_id)
        if not session or session.user_id != get_jwt_identity():
            return {'code': 404, 'message': '上传会话不存在'}, 404
        if session.status != 'uploading':
            return {'code': 409, 'message': '上传会话已结束'}, 409
        lease_error = _upload_lease_error(session)
        if lease_error:
            return lease_error

        data = request.get_json(silent=True) or {}
        if 'title' in data:
            title = str(data.get('title') or '').strip()
            if not title:
                return {'code': 400, 'message': '标题不能为空'}, 400
            session.title = title[:255]
        if 'description' in data:
            session.description = str(data.get('description') or '')[:2000]
        if 'tags' in data:
            tags = data.get('tags') or []
            if not isinstance(tags, list):
                return {'code': 400, 'message': '标签格式错误'}, 400
            tags = [
                str(tag).strip()[:50]
                for tag in tags[:20]
                if str(tag).strip()
            ]
            session.tags_json = json.dumps(tags, ensure_ascii=False)
        if 'garden_id' in data:
            garden_id = data.get('garden_id')
            if garden_id in (None, ''):
                session.garden_id = None
            else:
                try:
                    garden_id = int(garden_id)
                except (TypeError, ValueError):
                    return {'code': 400, 'message': '园林参数无效'}, 400
                if not db.session.get(Garden, garden_id):
                    return {'code': 400, 'message': '园林不存在'}, 400
                session.garden_id = garden_id
        if 'asset_type' in data:
            asset_type = str(data.get('asset_type') or '').strip()
            if asset_type not in ALLOWED_EXTENSIONS:
                return {'code': 400, 'message': '资产类型无效'}, 400
            if not allowed_file(session.filename, asset_type):
                return {'code': 400, 'message': '文件类型与资产类型不匹配'}, 400
            session.asset_type = asset_type

        session.updated_at = datetime.utcnow()
        db.session.commit()
        return {'code': 200, 'data': session.to_dict()}, 200

    def _append_chunk(self, upload_id, chunk):
        from app.models.extra import UploadSession
        session = db.session.get(UploadSession, upload_id)
        if not session or session.user_id != get_jwt_identity():
            return {'code': 404, 'message': '上传会话不存在'}, 404
        if session.status != 'uploading':
            return {'code': 409, 'message': '上传会话已结束'}, 409
        lease_error = _upload_lease_error(session)
        if lease_error:
            return lease_error

        try:
            offset = int(
                request.headers.get('X-Upload-Offset')
                or request.args.get('offset')
                or -1
            )
        except (TypeError, ValueError):
            offset = -1
        if offset != session.received_size:
            return {
                'code': 409,
                'message': '分块偏移不匹配，请从已接收位置继续',
                'data': {'received_size': session.received_size},
            }, 409

        if len(chunk) > session.chunk_size * 2:
            return {'code': 400, 'message': '单个分块过大'}, 400
        if session.received_size + len(chunk) > session.expected_size:
            return {'code': 400, 'message': '分块超过声明的文件大小'}, 400

        # 从偏移处重写并截断：即便上一次写入只完成了一半，也不会把
        # 重复字节追加到文件尾部。
        try:
            with open(session.temp_path, 'r+b') as handle:
                handle.seek(offset)
                handle.write(chunk)
                handle.truncate(offset + len(chunk))
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            current_app.logger.warning(
                '分块写入失败: %s', upload_id, exc_info=True
            )
            return {
                'code': 409,
                'message': '临时文件不可写，请取消后重新上传',
            }, 409

        updated = UploadSession.query.filter_by(
            id=upload_id, status='uploading', received_size=offset
        ).update(
            {
                UploadSession.received_size: offset + len(chunk),
                UploadSession.updated_at: datetime.utcnow(),
                UploadSession.lease_expires_at: (
                    datetime.utcnow() + timedelta(seconds=UPLOAD_LEASE_SECONDS)
                    if session.lease_token else None
                ),
            },
            synchronize_session=False,
        )
        if updated != 1:
            db.session.rollback()
            current = db.session.get(UploadSession, upload_id)
            return {
                'code': 409,
                'message': '分块偏移不匹配，请从已接收位置继续',
                'data': {
                    'received_size': current.received_size if current else 0,
                },
            }, 409
        db.session.commit()
        db.session.expire(session)
        return {
            'code': 200,
            'data': {
                'received_size': session.received_size,
                'expected_size': session.expected_size,
            },
        }, 200

    @jwt_required()
    def delete(self, upload_id):
        from app.models.extra import UploadSession
        try:
            with upload_session_lock(upload_id):
                session = db.session.get(UploadSession, upload_id)
                if not session or session.user_id != get_jwt_identity():
                    return {'code': 404, 'message': '上传会话不存在'}, 404
                if session.status == 'completed':
                    return {'code': 409, 'message': '已完成的上传不能取消'}, 409
                if session.status == 'uploading':
                    session.status = 'cancelled'
                    clear_upload_lease(session)
                    db.session.commit()
        except TimeoutError as exc:
            return {'code': 409, 'message': str(exc)}, 409
        remove_session_files(session)
        return {'code': 200, 'message': '已取消未完成的上传'}, 200


class AssetUploadSessionCompleteResource(Resource):
    """合并分块并创建资产"""

    @jwt_required()
    @rate_limit(limit=120, window=60)
    def post(self, upload_id):
        from app.models.extra import UploadSession
        try:
            with upload_session_lock(upload_id):
                response, status = self._complete_locked(upload_id)
        except TimeoutError as exc:
            return {'code': 409, 'message': str(exc)}, 409

        session = db.session.get(UploadSession, upload_id)
        if session and session.status in (
            'completed', 'failed', 'expired', 'cancelled'
        ):
            remove_session_files(session)
        return response, status

    def _complete_locked(self, upload_id):
        from app.models.extra import UploadSession

        user_id = get_jwt_identity()
        session = db.session.get(UploadSession, upload_id)
        if not session or session.user_id != user_id:
            return {'code': 404, 'message': '上传会话不存在'}, 404
        if session.status == 'completed' and session.asset_id:
            return {
                'code': 200,
                'message': '上传已完成',
                'data': {'asset_id': session.asset_id},
            }, 200
        if session.status != 'uploading':
            return {'code': 409, 'message': '上传会话已结束'}, 409
        lease_error = _upload_lease_error(session)
        if lease_error:
            return lease_error
        if session.received_size != session.expected_size:
            return {
                'code': 400,
                'message': '文件尚未上传完整',
                'data': {
                    'received_size': session.received_size,
                    'expected_size': session.expected_size,
                },
            }, 400
        if not os.path.isfile(session.temp_path):
            session.status = 'expired'
            clear_upload_lease(session)
            db.session.commit()
            return {
                'code': 409,
                'message': '临时文件已丢失，请重新上传',
            }, 409
        if os.path.getsize(session.temp_path) != session.expected_size:
            actual_size = os.path.getsize(session.temp_path)
            session.status = 'failed'
            clear_upload_lease(session)
            db.session.commit()
            return {
                'code': 400,
                'message': '临时文件大小与声明不一致，请重新上传',
                'data': {
                    'received_size': actual_size,
                    'expected_size': session.expected_size,
                },
            }, 400

        canonical_ext = canonical_extension(
            session.filename, VERSION_EXT_ALIASES
        )
        if not canonical_ext:
            session.status = 'failed'
            clear_upload_lease(session)
            db.session.commit()
            return {'code': 400, 'message': '不支持的文件类型'}, 400
        ext = canonical_ext.lstrip('.')
        if not validate_magic_bytes_path(session.temp_path, ext):
            session.status = 'failed'
            clear_upload_lease(session)
            db.session.commit()
            return {'code': 400, 'message': '文件内容与扩展名不匹配'}, 400
        if (
            session.file_fingerprint
            and calculate_upload_fingerprint(
                session.temp_path, session.expected_size
            ) != session.file_fingerprint
        ):
            session.status = 'failed'
            clear_upload_lease(session)
            db.session.commit()
            return {
                'code': 400,
                'message': '文件内容与认领时不一致，请重新选择原文件上传'
            }, 400

        file_hash = calculate_file_hash_path(session.temp_path)
        existing = Asset.query.filter(
            Asset.file_hash == file_hash,
            Asset.status != 'deleted',
        ).first()
        if existing:
            session.status = 'failed'
            clear_upload_lease(session)
            db.session.commit()
            # 与普通上传保持一致：只向能查看该资产的人返回 ID/编码，
            # 避免用哈希探测他人草稿/待审资产。
            user = User.query.get(user_id)
            visible = user and (
                user.role in ADMIN_ROLES
                or user_id in (
                    existing.creator_id,
                    existing.owner_id,
                    existing.uploader_id,
                )
            )
            data = None
            if visible:
                data = {
                    'existing_asset_id': existing.id,
                    'asset_code': existing.asset_code,
                    'status': existing.status,
                }
            return {
                'code': 400,
                'message': '该文件已上传过，请勿重复上传',
                'data': data,
            }, 400

        upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads')
        date_folder = datetime.now().strftime('%Y/%m/%d')
        save_dir = os.path.join(upload_folder, date_folder)
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, uuid_filename(canonical_ext))
        os.replace(session.temp_path, file_path)
        asset = None
        try:
            file_size = os.path.getsize(file_path)
            try:
                tag_names = json.loads(session.tags_json or '[]')
            except (TypeError, ValueError):
                tag_names = []
            asset = _create_asset_from_saved_file(
                user_id=user_id,
                title=session.title,
                description=session.description or '',
                asset_type=session.asset_type,
                garden_id=session.garden_id,
                original_name=session.filename,
                ext=ext,
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                tag_names=tag_names,
                commit=False,
            )
            # 资产、v1 与会话状态同一事务提交，避免重试时误判重复文件
            session.status = 'completed'
            session.asset_id = asset.id
            clear_upload_lease(session)
            db.session.commit()
        except Exception:
            current_app.logger.exception('断点续传创建资产失败')
            if asset and is_object_ref(asset.storage_path):
                delete_ref_quietly(asset.storage_path)
            # 先恢复文件，再回滚释放会话行锁；否则其他 worker 可能
            # 在恢复前把会话误判为临时文件丢失。
            try:
                os.replace(file_path, session.temp_path)
            except OSError:
                db.session.rollback()
                session.status = 'failed'
                clear_upload_lease(session)
                db.session.commit()
                current_app.logger.exception('断点续传临时文件恢复失败')
            else:
                db.session.rollback()
            raise

        user = User.query.get(user_id)
        OperationLog.log(
            user=user,
            action='upload',
            module='asset',
            description=f'断点续传上传资产: {asset.asset_code}',
            target_type='asset',
            target_id=asset.id,
            request=request,
        )
        return {
            'code': 200,
            'message': '上传成功',
            'data': {
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'file_hash': file_hash,
            },
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


def _download_ticket_serializer():
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='asset-download-ticket'
    )


DOWNLOAD_TICKET_MAX_AGE = 120


def _download_ticket_max_age():
    return int(current_app.config.get(
        'DOWNLOAD_TICKET_MAX_AGE', DOWNLOAD_TICKET_MAX_AGE
    ))


def _verify_download_ticket(ticket):
    try:
        return _download_ticket_serializer().loads(
            ticket, max_age=_download_ticket_max_age()
        )
    except Exception:
        return None


def _asset_download_error(asset, user, user_id):
    """资产基础可下载性检查；None 表示通过。"""
    if not asset:
        return {'code': 404, 'message': '资产不存在'}, 404

    is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
    if asset.status == 'deleted' and user.role not in ADMIN_ROLES:
        return {'code': 404, 'message': '资产不存在'}, 404
    if asset.status != 'published' and not (is_owner or user.role in ADMIN_ROLES):
        return {'code': 403, 'message': '资产未发布'}, 403
    return None


def _download_scope_decision(asset, user_id, user, purpose, territory):
    """返回 (可用授权, 拒绝原因, 台账使用的授权ID)。"""
    now = datetime.utcnow()
    licenses = License.query.filter(
        License.asset_id == asset.id,
        License.licensee_id == user_id,
        License.status == 'active',
        License.start_time <= now,
        or_(License.end_time.is_(None), License.end_time > now),
    ).order_by(License.id.asc()).all()

    is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
    bypass_scope = is_owner or user.role in ADMIN_ROLES
    current_version = AssetVersion.query.filter_by(
        asset_id=asset.id
    ).order_by(AssetVersion.version_no.desc()).first()

    selected_license = None
    denial_reason = None
    if not bypass_scope:
        if not licenses:
            denial_reason = '无下载权限，请先申请授权'
        else:
            from app.services.license_scope import scope_violation
            reasons = []
            for license_row in licenses:
                reason = scope_violation(
                    license_row,
                    source_format=asset.file_format,
                    purpose=purpose,
                    territory=territory,
                    current_version_id=current_version.id if current_version else None,
                    current_version_no=current_version.version_no if current_version else None,
                )
                if not reason:
                    selected_license = license_row
                    break
                reasons.append(reason)
            if not selected_license:
                denial_reason = reasons[0] if reasons else '无下载权限'

    return selected_license, denial_reason, (licenses[0].id if licenses else None)


def _record_denied_download(asset, user, user_id, purpose, territory,
                            denial_reason, license_id):
    from app.models.extra import DownloadRecord

    record = DownloadRecord(
        asset_id=asset.id,
        user_id=user_id,
        license_id=license_id,
        status='denied',
        denial_reason=denial_reason[:300],
        usage_purpose=purpose,
        territory=territory,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:500]
    )
    db.session.add(record)
    db.session.commit()
    OperationLog.log(
        user=user,
        action='download_denied',
        module='license',
        description=f'下载被拒: {asset.asset_code} · {denial_reason}',
        target_type='asset',
        target_id=asset.id,
        request=request,
        status='failed',
        error_message=denial_reason
    )


def _asset_file_path(asset):
    raw_path = asset.watermarked_path or asset.storage_path
    return raw_path or ''


def _download_file_path(asset, license_row, user):
    """生成（或复用）指纹副本并返回实际文件路径与指纹。"""
    fingerprint = None
    if license_row and asset.asset_type == 'image':
        try:
            from app.services.fingerprint_service import get_or_create_fingerprint
            # 指纹生成失败只回滚指纹保存点，不能污染外层授权/配额事务
            with db.session.begin_nested():
                fingerprint, _ = get_or_create_fingerprint(
                    asset, license_row, user
                )
        except Exception:
            fingerprint = None
            current_app.logger.warning(
                '生成下载指纹失败，回退到普通水印副本', exc_info=True
            )

    file_path = (
        fingerprint.file_path if fingerprint else _asset_file_path(asset)
    )
    return file_path, fingerprint


def _download_display_name(asset, file_path):
    actual_ext = os.path.splitext(file_path)[1].lstrip('.').lower()
    download_ext = actual_ext or (asset.file_format or '').lower()
    if not download_ext:
        return asset.asset_code
    return f'{asset.asset_code}.{download_ext}'


class AssetDownloadResource(Resource):
    """资产下载（支持 JWT 或短时下载票据，浏览器可直接流式落盘）"""

    @jwt_required(optional=True)
    def get(self, asset_id):
        """下载资产"""
        ticket = (request.args.get('ticket') or '').strip()
        if ticket:
            payload = _verify_download_ticket(ticket)
            if not payload or payload.get('asset_id') != asset_id:
                return {
                    'code': 401,
                    'message': '下载凭证无效或已过期，请重新发起下载'
                }, 401
            user_id = payload.get('user_id')
            user = User.query.get(user_id)
            if not user or user.status != 'active':
                return {'code': 401, 'message': '账号不可用，请重新登录'}, 401
            purpose = payload.get('purpose') or None
            territory = payload.get('territory') or None
        else:
            user_id = get_jwt_identity()
            if not user_id:
                return {'code': 401, 'message': '未授权访问'}, 401
            user = User.query.get(user_id)
            if not user:
                return {'code': 401, 'message': '账号不存在或已被禁用'}, 401
            purpose = (request.args.get('purpose') or '').strip() or None
            territory = (request.args.get('territory') or '').strip() or None
            from app.services.license_scope import PURPOSE_OPTIONS, TERRITORY_OPTIONS
            if purpose and purpose not in PURPOSE_OPTIONS:
                return {'code': 400, 'message': '使用目的选项无效'}, 400
            if territory and territory not in TERRITORY_OPTIONS:
                return {'code': 400, 'message': '使用地域选项无效'}, 400

        asset = Asset.query.get(asset_id)
        error = _asset_download_error(asset, user, user_id)
        if error:
            return error

        # 检查下载权限：有效授权未过期且在授权范围内，或本人/管理员
        from app.models.extra import DownloadRecord

        selected_license, denial_reason, fallback_license_id = (
            _download_scope_decision(asset, user_id, user, purpose, territory)
        )
        if denial_reason:
            _record_denied_download(
                asset, user, user_id, purpose, territory,
                denial_reason, fallback_license_id
            )
            return {'code': 403, 'message': denial_reason}, 403

        # 先确认原始文件存在，避免“下载失败但配额已经占用”
        base_path = _asset_file_path(asset)
        if not base_path or not ref_exists(base_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        # 原子占用一次授权下载配额，防止并发请求同时越过上限
        if selected_license:
            quota = db.session.execute(
                update(License)
                .where(
                    License.id == selected_license.id,
                    or_(
                        License.max_downloads.is_(None),
                        License.download_count < License.max_downloads,
                    ),
                )
                .values(download_count=License.download_count + 1)
            )
            if quota.rowcount != 1:
                db.session.rollback()
                reason = (
                    '该授权下载次数已用完'
                    f'（上限 {selected_license.max_downloads} 次）'
                )
                _record_denied_download(
                    asset, user, user_id, purpose, territory,
                    reason, selected_license.id
                )
                return {'code': 403, 'message': reason}, 403

        file_path, fingerprint = _download_file_path(
            asset, selected_license, user
        )
        if not file_path or not ref_exists(file_path):
            db.session.rollback()
            return {'code': 404, 'message': '文件不存在'}, 404

        # 先构造发送响应；send_ref 在这一步会检查文件是否可读，
        # 失败时不会留下“已扣次数但没有文件”的成功台账。
        try:
            response = send_ref(
                file_path,
                _download_display_name(asset, file_path),
                as_attachment=True,
            )
        except Exception:
            db.session.rollback()
            current_app.logger.warning('下载文件读取失败', exc_info=True)
            return {'code': 502, 'message': '文件读取失败，请稍后重试'}, 502

        # 记录下载（关联本次使用的授权与指纹副本，便于后续审计）
        record = DownloadRecord(
            asset_id=asset_id,
            user_id=user_id,
            license_id=selected_license.id if selected_license else None,
            fingerprint_id=fingerprint.id if fingerprint else None,
            status='success',
            usage_purpose=purpose,
            territory=territory,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(record)
        # 使用 SQL 表达式自增，避免并发下载互相覆盖计数
        asset.download_count = Asset.download_count + 1
        try:
            db.session.commit()
        except Exception:
            response.close()
            raise

        try:
            OperationLog.log(
                user=user,
                action='download',
                module='asset',
                description=f'下载资产: {asset.asset_code}',
                target_type='asset',
                target_id=asset_id,
                request=request
            )
        except Exception:
            # 审计日志异常不能阻断已经构造好的合法下载
            current_app.logger.warning('记录下载日志失败', exc_info=True)

        if fingerprint:
            response.headers['X-Download-Fingerprint'] = (
                fingerprint.fingerprint_code
            )
        return response


class AssetDownloadTicketResource(Resource):
    """签发短时下载票据，供浏览器直接流式下载大文件"""

    @rate_limit(limit=30, window=60)
    @jwt_required()
    def post(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 401, 'message': '账号不存在或已被禁用'}, 401

        asset = Asset.query.get(asset_id)
        error = _asset_download_error(asset, user, user_id)
        if error:
            return error

        data = request.get_json(silent=True) or {}
        purpose = (data.get('purpose') or '').strip() or None
        territory = (data.get('territory') or '').strip() or None
        from app.services.license_scope import PURPOSE_OPTIONS, TERRITORY_OPTIONS
        if purpose and purpose not in PURPOSE_OPTIONS:
            return {'code': 400, 'message': '使用目的选项无效'}, 400
        if territory and territory not in TERRITORY_OPTIONS:
            return {'code': 400, 'message': '使用地域选项无效'}, 400

        selected_license, denial_reason, fallback_license_id = (
            _download_scope_decision(asset, user_id, user, purpose, territory)
        )
        if denial_reason:
            _record_denied_download(
                asset, user, user_id, purpose, territory,
                denial_reason, fallback_license_id
            )
            return {'code': 403, 'message': denial_reason}, 403

        file_path = _asset_file_path(asset)
        if not file_path or not ref_exists(file_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        fingerprint_code = None
        if selected_license and asset.asset_type == 'image':
            try:
                from app.services.fingerprint_service import (
                    get_or_create_fingerprint
                )
                with db.session.begin_nested():
                    fingerprint, _ = get_or_create_fingerprint(
                        asset, selected_license, user
                    )
                # 签票请求结束后 session 会被回收；必须显式提交，
                # 否则指纹记录回滚而副本文件保留，指纹码与文件不一致。
                db.session.commit()
                fingerprint_code = fingerprint.fingerprint_code
            except Exception:
                current_app.logger.warning(
                    '生成下载指纹失败，下载时将回退到普通水印副本',
                    exc_info=True
                )

        payload = {
            'asset_id': asset_id,
            'user_id': user_id,
            'purpose': purpose,
            'territory': territory,
            'nonce': uuid.uuid4().hex,
        }
        ticket = _download_ticket_serializer().dumps(payload)
        return {
            'code': 200,
            'data': {
                'ticket': ticket,
                'expires_in': _download_ticket_max_age(),
                'fingerprint_code': fingerprint_code,
            }
        }, 200


PREVIEW_TICKET_MAX_AGE = 3600


def _preview_ticket_serializer():
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='asset-preview-ticket'
    )


def _preview_ticket_max_age():
    return int(current_app.config.get(
        'PREVIEW_TICKET_MAX_AGE', PREVIEW_TICKET_MAX_AGE
    ))


def _verify_preview_ticket(ticket):
    try:
        return _preview_ticket_serializer().loads(
            ticket, max_age=_preview_ticket_max_age()
        )
    except Exception:
        return None


def _preview_asset_error(asset, user, user_id):
    """预览权限：草稿仅所有者/管理员；已发布需有效授权且版本匹配。"""
    if not asset:
        return {'code': 404, 'message': '资产不存在'}, 404

    is_owner = user_id in (asset.creator_id, asset.owner_id, asset.uploader_id)
    is_admin = user.role in ADMIN_ROLES
    if asset.status == 'deleted' and not is_admin:
        return {'code': 404, 'message': '资产不存在'}, 404
    if asset.status != 'published' and not (is_owner or is_admin):
        return {'code': 403, 'message': '资产未发布'}, 403

    if asset.status == 'published' and not (is_owner or is_admin):
        now = datetime.utcnow()
        license_row = License.query.filter(
            License.asset_id == asset.id,
            License.licensee_id == user_id,
            License.status == 'active',
            License.start_time <= now,
            or_(License.end_time.is_(None), License.end_time > now),
        ).first()
        if not license_row:
            return {'code': 403, 'message': '获得授权后可在线预览'}, 403
        current_version = AssetVersion.query.filter_by(
            asset_id=asset.id
        ).order_by(AssetVersion.version_no.desc()).first()
        if (
            license_row.version_id
            and (
                not current_version
                or current_version.id != license_row.version_id
            )
        ):
            return {
                'code': 403,
                'message': '授权对应历史版本，请重新申请后再预览'
            }, 403

    return None


def _send_preview_file(asset, file_path):
    ext = os.path.splitext(file_path)[1].lstrip('.').lower()
    download_name = f'{asset.asset_code}.{ext}' if ext else asset.asset_code
    mimetype = {
        'gltf': 'model/gltf+json',
        'glb': 'model/gltf-binary',
        'stl': 'model/stl',
        'obj': 'text/plain',
    }.get(ext) or mimetypes.guess_type(download_name)[0]
    return send_ref_range(file_path, download_name, mimetype=mimetype)


class AssetPreviewResource(Resource):
    """在线预览（支持 JWT 或预览票据，视频/PDF 可直接 Range 流式加载）

    预览不写入下载台账、不增加下载量；已发布资产需要有效授权才能预览，
    草稿仅所有者与管理员可用。
    """

    @jwt_required(optional=True)
    def get(self, asset_id):
        ticket = (request.args.get('ticket') or '').strip()
        if ticket:
            payload = _verify_preview_ticket(ticket)
            if not payload or payload.get('asset_id') != asset_id:
                return {
                    'code': 401,
                    'message': '预览凭证无效或已过期，请刷新页面重试'
                }, 401
            user_id = payload.get('user_id')
            user = User.query.get(user_id)
            if not user or user.status != 'active':
                return {'code': 401, 'message': '账号不可用，请重新登录'}, 401
        else:
            user_id = get_jwt_identity()
            if not user_id:
                return {'code': 401, 'message': '未授权访问'}, 401
            user = User.query.get(user_id)
            if not user:
                return {'code': 401, 'message': '账号不存在或已被禁用'}, 401

        asset = Asset.query.get(asset_id)
        error = _preview_asset_error(asset, user, user_id)
        if error:
            return error

        file_path = _asset_file_path(asset)
        if not file_path or not ref_exists(file_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        return _send_preview_file(asset, file_path)


class AssetPreviewTicketResource(Resource):
    """签发预览票据，供 video/iframe/三维加载器直接按 Range 读取"""

    @rate_limit(limit=60, window=60)
    @jwt_required()
    def post(self, asset_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'code': 401, 'message': '账号不存在或已被禁用'}, 401

        asset = Asset.query.get(asset_id)
        error = _preview_asset_error(asset, user, user_id)
        if error:
            return error

        file_path = _asset_file_path(asset)
        if not file_path or not ref_exists(file_path):
            return {'code': 404, 'message': '文件不存在'}, 404

        ticket = _preview_ticket_serializer().dumps({
            'asset_id': asset_id,
            'user_id': user_id,
            'nonce': uuid.uuid4().hex,
        })
        return {
            'code': 200,
            'data': {
                'ticket': ticket,
                'expires_in': _preview_ticket_max_age(),
            }
        }, 200


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
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        from app.resources.comments import can_view_asset
        if not can_view_asset(user, user_id, asset):
            return {'code': 404, 'message': '资产不存在'}, 404

        favorited = Favorite.query.filter_by(user_id=user_id, asset_id=asset_id).first() is not None
        count = Favorite.query.filter_by(asset_id=asset_id).count()
        return {'code': 200, 'data': {'favorited': favorited, 'count': count}}, 200

    @jwt_required()
    def post(self, asset_id):
        """添加收藏"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        from app.resources.comments import can_view_asset
        if not can_view_asset(user, user_id, asset):
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
        # 最近活动只展示业务操作；登录/登出次数多且信息量低
        recent_activities = OperationLog.query.filter(
            OperationLog.status == 'success',
            OperationLog.action.notin_(('login', 'logout')),
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
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        asset = Asset.query.get(asset_id)
        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        from app.resources.comments import can_view_asset
        if not can_view_asset(user, user_id, asset):
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
            values = {
                'status': 'published',
                'approver_id': user_id,
                'approve_time': datetime.utcnow(),
                'publish_at': datetime.utcnow(),
            }
        elif action == 'reject':
            values = {
                'status': 'rejected',
                'reject_reason': reason,
            }
        else:
            return {'code': 400, 'message': '无效操作'}, 400

        # 条件更新：审批期间资产若被删除，不能再把它改回 published
        updated = db.session.execute(
            update(Asset)
            .where(
                Asset.id == asset_id,
                Asset.status == 'pending',
                Asset.deleted_at.is_(None),
            )
            .values(**values)
        )
        if updated.rowcount != 1:
            db.session.rollback()
            return {
                'code': 409,
                'message': '资产状态已变更，请刷新后重试',
            }, 409

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