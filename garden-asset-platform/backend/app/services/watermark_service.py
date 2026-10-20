"""
水印服务模块
提供水印嵌入和提取的业务逻辑封装
"""
import os
import logging
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename

from algorithm.vector.embed import embed_vector_watermark
from algorithm.vector.extract import extract_vector_watermark
from algorithm.raster.embed import embed_raster_watermark, embed_raster_watermark_color
from algorithm.raster.extract import extract_raster_watermark
from app.extensions import db
from app.models.asset import Asset
from app.models.log import OperationLog


logger = logging.getLogger(__name__)


class WatermarkService:
    """水印服务类"""

    @staticmethod
    def _ensure_default_watermark(path):
        """默认水印缺失时自动生成，保证全新环境开箱可用。"""
        if os.path.exists(path):
            return path

        try:
            from PIL import Image, ImageDraw, ImageFont

            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            img = Image.new('RGBA', (128, 128), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype('arial.ttf', 22)
            except Exception:
                font = ImageFont.load_default()

            text = 'SZGARDEN'
            bbox = draw.textbbox((0, 0), text, font=font)
            x = (128 - (bbox[2] - bbox[0])) // 2
            y = (128 - (bbox[3] - bbox[1])) // 2
            draw.text((x, y), text, fill=(128, 128, 128, 128), font=font)
            img.save(path, 'PNG')
            logger.info('已生成默认水印: %s', path)
        except Exception as exc:
            logger.warning('生成默认水印失败: %s', exc)

        return path

    @staticmethod
    def get_watermark_path():
        """获取默认水印路径（缺失时自动生成）"""
        try:
            path = current_app.config.get('WATERMARK_DEFAULT_PATH')
            if path:
                return WatermarkService._ensure_default_watermark(path)
        except RuntimeError:
            pass

        default_path = os.path.join(os.getcwd(), 'data', 'watermark', 'default.png')
        return WatermarkService._ensure_default_watermark(default_path)

    @staticmethod
    def resolve_vector_path(path):
        """矢量资产上传的是 zip 时，安全解压并返回其中的 .shp 路径"""
        if not path or not path.lower().endswith('.zip'):
            return path

        import shutil
        import zipfile
        import tempfile

        base_dir = current_app.config.get('UPLOAD_FOLDER', './uploads')
        os.makedirs(base_dir, exist_ok=True)
        extract_dir = tempfile.mkdtemp(prefix='vector_', dir=base_dir)
        root_real = os.path.realpath(extract_dir)
        max_total = current_app.config.get('VECTOR_EXTRACT_MAX_BYTES', 200 * 1024 * 1024)

        try:
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                if len(infos) > 1000:
                    raise ValueError('矢量压缩包文件数量过多')
                if sum(item.file_size for item in infos) > max_total:
                    raise ValueError('矢量压缩包解压后体积超过限制')
                for member in infos:
                    target = os.path.realpath(os.path.join(extract_dir, member.filename))
                    if not target.startswith(root_real + os.sep) and target != root_real:
                        raise ValueError('矢量压缩包包含非法路径')
                archive.extractall(extract_dir)

            for root, _, files in os.walk(extract_dir):
                for name in files:
                    if name.lower().endswith('.shp'):
                        return os.path.join(root, name)

            raise ValueError('矢量压缩包中未找到 .shp 文件')
        except Exception:
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise

    @staticmethod
    def cleanup_vector_temp(path):
        """删除 resolve_vector_path 产生的临时解压目录。"""
        if not path or not path.lower().endswith('.shp'):
            return
        parent = os.path.dirname(path)
        if os.path.basename(parent).startswith('vector_'):
            import shutil
            shutil.rmtree(parent, ignore_errors=True)

    @staticmethod
    def embed_watermark(asset, user=None, watermark_path=None):
        """
        为资产嵌入水印

        Args:
            asset: 资产对象
            user: 操作用户
            watermark_path: 水印图片路径（可选）

        Returns:
            嵌入结果字典
        """
        if asset.watermark_status == 'embedded':
            return {
                'success': False,
                'message': '资产已嵌入水印'
            }

        # 获取水印图片
        if not watermark_path:
            watermark_path = WatermarkService.get_watermark_path()

        if not os.path.exists(watermark_path):
            return {
                'success': False,
                'message': '水印图片不存在'
            }

        # 获取输出目录
        output_folder = current_app.config.get('WATERMARK_FOLDER', './watermarks')
        os.makedirs(output_folder, exist_ok=True)

        # 获取园林编码
        from app.models.garden import Garden
        garden = Garden.query.get(asset.garden_id) if asset.garden_id else None
        garden_code = garden.code if garden else 'GEN'

        # 资产类型编码
        type_map = {
            'image': 'IMG',
            'model': 'MDL',
            'vector': 'VEC',
            'document': 'DOC',
            'video': 'VID'
        }
        asset_type_code = type_map.get(asset.asset_type, 'OTH')

        try:
            # 根据资产类型选择嵌入算法
            if asset.asset_type == 'vector':
                # 矢量数据水印嵌入（ZIP 解压到临时目录，用完立即清理）
                vector_source = WatermarkService.resolve_vector_path(asset.storage_path)
                try:
                    result = embed_vector_watermark(
                        shpfile_path=vector_source,
                        watermark_path=watermark_path,
                        output_folder=output_folder,
                        garden_code=garden_code,
                        asset_type_code=asset_type_code
                    )
                finally:
                    WatermarkService.cleanup_vector_temp(vector_source)

                asset.watermarked_path = os.path.abspath(result['zip_file_path'])
                asset.vr_value = str(result['vr'])  # 存储验证值

            elif asset.asset_type == 'image':
                # 栅格图像水印嵌入：彩色图保留颜色，灰度图走单通道
                from PIL import Image as PILImage

                with PILImage.open(asset.storage_path) as source:
                    is_color = source.mode in ('RGB', 'RGBA')

                if is_color:
                    result = embed_raster_watermark_color(
                        image_path=asset.storage_path,
                        watermark_path=watermark_path,
                        output_folder=output_folder,
                        method='dct',
                        garden_code=garden_code
                    )
                else:
                    result = embed_raster_watermark(
                        image_path=asset.storage_path,
                        watermark_path=watermark_path,
                        output_folder=output_folder,
                        method='dct',
                        garden_code=garden_code
                    )

                asset.watermarked_path = os.path.abspath(result['watermarked_path'])

            else:
                return {
                    'success': False,
                    'message': f'不支持的资产类型: {asset.asset_type}'
                }

            # 更新资产状态
            asset.watermark_id = result['watermark_id']
            asset.watermark_status = 'embedded'
            asset.watermark_embedded_at = datetime.utcnow()

            db.session.commit()

            # 记录操作日志
            if user:
                OperationLog.log(
                    user=user,
                    action='watermark_embed',
                    module='watermark',
                    description=f'嵌入水印: {asset.asset_code}',
                    target_type='asset',
                    target_id=asset.id
                )

            logger.info(f"水印嵌入成功: {asset.asset_code}, 水印ID: {result['watermark_id']}")

            return {
                'success': True,
                'message': '水印嵌入成功',
                'watermark_id': result['watermark_id'],
                'watermarked_path': asset.watermarked_path,
                'psnr': result.get('psnr')
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"水印嵌入失败: {str(e)}")
            return {
                'success': False,
                'message': f'水印嵌入失败: {str(e)}'
            }

    @staticmethod
    def extract_watermark(asset, user=None, original_watermark_path=None):
        """
        从资产提取水印

        Args:
            asset: 资产对象
            user: 操作用户
            original_watermark_path: 原始水印路径（用于比对）

        Returns:
            提取结果字典
        """
        if asset.watermark_status != 'embedded':
            return {
                'success': False,
                'message': '资产未嵌入水印'
            }

        if not asset.watermarked_path or not os.path.exists(asset.watermarked_path):
            return {
                'success': False,
                'message': '水印文件不存在'
            }

        # 获取输出目录
        output_folder = current_app.config.get('EXTRACTED_FOLDER', './extracted')
        os.makedirs(output_folder, exist_ok=True)

        # 获取原始水印
        if not original_watermark_path:
            original_watermark_path = WatermarkService.get_watermark_path()

        try:
            if asset.asset_type == 'vector':
                # 矢量数据水印提取
                import ast
                vr = ast.literal_eval(asset.vr_value) if asset.vr_value else None

                vector_source = WatermarkService.resolve_vector_path(asset.watermarked_path)
                try:
                    result = extract_vector_watermark(
                        watermarked_shpfile_path=vector_source,
                        vr=vr,
                        output_folder=output_folder
                    )
                finally:
                    WatermarkService.cleanup_vector_temp(vector_source)

            elif asset.asset_type == 'image':
                # 栅格图像水印提取
                result = extract_raster_watermark(
                    watermarked_path=asset.watermarked_path,
                    original_watermark_path=original_watermark_path,
                    output_folder=output_folder
                )

            else:
                return {
                    'success': False,
                    'message': f'不支持的资产类型: {asset.asset_type}'
                }

            # 记录操作日志
            if user:
                OperationLog.log(
                    user=user,
                    action='watermark_extract',
                    module='watermark',
                    description=f'提取水印: {asset.asset_code}',
                    target_type='asset',
                    target_id=asset.id
                )

            logger.info(f"水印提取成功: {asset.asset_code}")

            return {
                'success': True,
                'message': '水印提取成功',
                'watermark_path': result.get('extracted_watermark_path') or result.get('watermark_path'),
                'nc_value': result.get('nc_value')
            }

        except Exception as e:
            logger.error(f"水印提取失败: {str(e)}")
            return {
                'success': False,
                'message': f'水印提取失败: {str(e)}'
            }

    @staticmethod
    def verify_watermark(asset, watermark_id):
        """
        验证水印ID

        Args:
            asset: 资产对象
            watermark_id: 待验证的水印ID

        Returns:
            验证结果
        """
        if not asset.watermark_id:
            return {
                'verified': False,
                'message': '资产未嵌入水印'
            }

        if asset.watermark_id == watermark_id:
            return {
                'verified': True,
                'message': '水印验证通过',
                'asset_code': asset.asset_code,
                'watermark_id': asset.watermark_id
            }
        else:
            return {
                'verified': False,
                'message': '水印ID不匹配',
                'expected': asset.watermark_id,
                'provided': watermark_id
            }

    @staticmethod
    def trace_from_file(file_path, original_watermark_path=None):
        """
        从文件中提取水印并溯源

        Args:
            file_path: 待溯源文件路径
            original_watermark_path: 原始水印路径（用于比对）

        Returns:
            溯源结果字典
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'message': '文件不存在'
            }

        # 获取输出目录
        output_folder = current_app.config.get('EXTRACTED_FOLDER', './extracted')
        os.makedirs(output_folder, exist_ok=True)

        # 获取原始水印
        if not original_watermark_path:
            original_watermark_path = WatermarkService.get_watermark_path()

        try:
            # 判断文件类型
            ext = os.path.splitext(file_path)[1].lower()

            if ext in ['.shp', '.zip']:
                # 矢量数据水印提取（临时解压目录用完立即清理）
                vector_source = WatermarkService.resolve_vector_path(file_path)
                try:
                    result = extract_vector_watermark(
                        watermarked_shpfile_path=vector_source,
                        vr=None,  # 溯源时未知vr值
                        output_folder=output_folder
                    )
                finally:
                    WatermarkService.cleanup_vector_temp(vector_source)
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']:
                # 栅格图像水印提取
                result = extract_raster_watermark(
                    watermarked_path=file_path,
                    original_watermark_path=original_watermark_path,
                    output_folder=output_folder
                )
            else:
                return {
                    'success': False,
                    'message': f'不支持的文件类型: {ext}'
                }

            # 从结果中解析水印ID
            watermark_id = result.get('watermark_id')

            if not watermark_id:
                # 尝试从提取的水印图片中识别
                # 这里简化处理，实际可能需要OCR或其他识别方法
                return {
                    'success': False,
                    'message': '未能提取有效水印ID',
                    'nc_value': result.get('nc_value', 0)
                }

            logger.info(f"水印溯源: 提取到水印ID {watermark_id}")

            return {
                'success': True,
                'watermark_id': watermark_id,
                'nc_value': result.get('nc_value', 0)
            }

        except Exception as e:
            logger.error(f"水印溯源失败: {str(e)}")
            return {
                'success': False,
                'message': f'水印溯源失败: {str(e)}'
            }