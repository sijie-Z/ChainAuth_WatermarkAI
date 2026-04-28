"""
资产相关API资源
"""
import os
import uuid
import hashlib
from datetime import datetime
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.user import User
from app.models.asset import Asset, AssetTag, AssetFeature
from app.models.garden import Garden
from app.models.license import LicenseApplication, License
from app.models.log import OperationLog
from sqlalchemy import func


class PublicStatsResource(Resource):
    """公开统计数据（无需登录）"""

    def get(self):
        total = Asset.query.filter(Asset.status != 'deleted').count()
        watermarked = Asset.query.filter(Asset.watermark_id.isnot(None)).count()
        chained = Asset.query.filter(Asset.chain_tx_hash.isnot(None)).count()
        total_licenses = License.query.count()

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
    'vector': ['shp', 'geojson', 'kml', 'kmz'],
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


class AssetListResource(Resource):
    """资产列表"""

    @jwt_required()
    def get(self):
        """获取资产列表"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        asset_type = request.args.get('asset_type')
        garden_id = request.args.get('garden_id', type=int)
        status = request.args.get('status', 'published')
        keyword = request.args.get('keyword')

        query = Asset.query

        # 过滤条件
        if asset_type:
            query = query.filter_by(asset_type=asset_type)
        if garden_id:
            query = query.filter_by(garden_id=garden_id)
        if status:
            query = query.filter_by(status=status)
        if keyword:
            query = query.filter(Asset.title.ilike(f'%{keyword}%'))

        # 排序
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
        asset = Asset.query.get(asset_id)

        if not asset:
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
        if asset.creator_id != user_id and user.role not in ['admin', 'adm1', 'adm2', 'adm3']:
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
        if asset.creator_id != user_id and user.role not in ['admin', 'adm1', 'adm2', 'adm3']:
            return {'code': 403, 'message': '无权限删除'}, 403

        asset.status = 'deleted'
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

        ext = file.filename.rsplit('.', 1)[1].lower()
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

        # 检查是否已存在相同文件
        existing = Asset.query.filter_by(file_hash=file_hash).first()
        if existing:
            return {
                'code': 400,
                'message': '文件已存在',
                'data': {'existing_asset_id': existing.id}
            }, 400

        # 生成文件名和路径
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
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
            owner_id=user_id,
            status='draft'
        )

        db.session.add(asset)
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

        if asset.status != 'published':
            return {'code': 403, 'message': '资产未发布'}, 403

        # 检查下载权限
        from app.models.license import License
        has_license = License.query.filter_by(
            asset_id=asset_id,
            licensee_id=user_id,
            status='active'
        ).first()

        if not has_license and asset.creator_id != user_id and user.role not in ['admin', 'adm1', 'adm2', 'adm3']:
            return {'code': 403, 'message': '无下载权限，请先申请授权'}, 403

        # 记录下载
        from app.models.extra import DownloadRecord
        record = DownloadRecord(
            asset_id=asset_id,
            user_id=user_id,
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

        return {
            'code': 200,
            'data': {
                'download_url': f'/api/assets/{asset_id}/file',
                'asset_code': asset.asset_code,
                'file_format': asset.file_format
            }
        }, 200


class AssetFavoriteResource(Resource):
    """资产收藏"""

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
            return {'code': 400, 'message': '已收藏'}, 400

        favorite = Favorite(
            user_id=user_id,
            asset_id=asset_id,
            created_at=datetime.utcnow()
        )
        db.session.add(favorite)
        asset.favorite_count += 1
        db.session.commit()

        return {'code': 200, 'message': '收藏成功'}, 200

    @jwt_required()
    def delete(self, asset_id):
        """取消收藏"""
        user_id = get_jwt_identity()

        from app.models.extra import Favorite
        favorite = Favorite.query.filter_by(
            user_id=user_id,
            asset_id=asset_id
        ).first()

        if not favorite:
            return {'code': 404, 'message': '收藏不存在'}, 404

        asset = Asset.query.get(asset_id)
        if asset:
            asset.favorite_count -= 1

        db.session.delete(favorite)
        db.session.commit()

        return {'code': 200, 'message': '取消收藏成功'}, 200


class AssetStatsResource(Resource):
    """资产统计（管理后台仪表盘数据）"""

    @jwt_required()
    def get(self):
        """获取资产统计数据"""
        from datetime import datetime, timedelta

        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if user.role not in ['admin', 'adm1', 'adm2', 'adm3']:
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

        # 水印嵌入趋势（最近7天）
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        watermark_trends = db.session.query(
            func.date(Asset.watermark_embedded_at).label('date'),
            func.count(Asset.id).label('count')
        ).filter(
            Asset.watermark_embedded_at >= seven_days_ago,
            Asset.watermark_status == 'embedded'
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
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')

        query = Asset.query.filter_by(creator_id=user_id)

        if status:
            query = query.filter_by(status=status)

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
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        data = request.get_json()
        tags = data.get('tags', [])

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

        return {'code': 200, 'message': '标签添加��功'}, 200


class AssetPublishResource(Resource):
    """资产发布"""

    @jwt_required()
    def post(self, asset_id):
        """提交发布申请"""
        user_id = get_jwt_identity()
        asset = Asset.query.get(asset_id)

        if not asset:
            return {'code': 404, 'message': '资产不存在'}, 404

        if asset.creator_id != user_id:
            return {'code': 403, 'message': '无权限'}, 403

        if asset.status != 'draft':
            return {'code': 400, 'message': '只有草稿状态才能提交发布'}, 400

        asset.status = 'pending'
        db.session.commit()

        # 发送通知给审核人员
        # TODO: 实现通知机制

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

        if user.role not in ['admin', 'adm1', 'adm2']:
            return {'code': 403, 'message': '无审核权限'}, 403

        if asset.status != 'pending':
            return {'code': 400, 'message': '只有待审核状态才能审核'}, 400

        data = request.get_json()
        action = data.get('action')  # approve 或 reject
        reason = data.get('reason', '')

        if action == 'approve':
            asset.status = 'published'
            asset.approver_id = user_id
            asset.approve_time = datetime.utcnow()
        elif action == 'reject':
            asset.status = 'rejected'
            asset.reject_reason = reason
        else:
            return {'code': 400, 'message': '无效操作'}, 400

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