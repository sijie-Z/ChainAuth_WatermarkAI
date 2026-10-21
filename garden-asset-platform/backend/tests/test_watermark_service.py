"""
水印服务单元测试

覆盖 WatermarkService 的正常分支、错误分支与资源清理逻辑；
算法调用一律用假实现替代，不产生大图/大文件。
"""
import ast
import os
import uuid
import zipfile

import pytest
from PIL import Image

from app.extensions import db
from app.models.asset import Asset
from app.models.log import OperationLog
from app.models.user import User
from app.services import watermark_service as watermark_service_module
from app.services.watermark_service import WatermarkService


def create_user(username='wmuser'):
    user = User(username=username, email=f'{username}@test.com', role='user')
    user.set_password('pass1234')
    db.session.add(user)
    db.session.commit()
    return user


def create_asset(asset_type='image', **overrides):
    data = {
        'asset_code': f'WMT-{uuid.uuid4().hex[:10].upper()}',
        'title': '水印服务测试资产',
        'asset_type': asset_type,
        'file_format': 'PNG',
        'status': 'published',
    }
    data.update(overrides)
    asset = Asset(**data)
    db.session.add(asset)
    db.session.commit()
    return asset


def write_png(path, mode='RGB', size=(8, 8)):
    color = (10, 20, 30) if mode in ('RGB', 'RGBA') else 128
    Image.new(mode, size, color).save(path)
    return str(path)


class TestDefaultWatermark:
    def test_generates_default_watermark_when_missing(self, app, tmp_path, monkeypatch):
        # 模拟无系统字体（CI/无头环境）时退回 PIL 内置字体。
        # load_default() 内部也会调用 truetype()，因此只让首次调用失败。
        from PIL import ImageFont

        real_truetype = ImageFont.truetype
        attempts = []

        def flaky_truetype(*args, **kwargs):
            attempts.append(args)
            if len(attempts) == 1:
                raise OSError('arial.ttf not found')
            return real_truetype(*args, **kwargs)

        monkeypatch.setattr(ImageFont, 'truetype', flaky_truetype)
        path = tmp_path / 'nested' / 'default.png'

        result = WatermarkService._ensure_default_watermark(str(path))

        assert result == str(path)
        assert path.exists()
        assert len(attempts) >= 2
        with Image.open(path) as image:
            assert image.size == (128, 128)

    def test_returns_existing_file_without_regenerating(self, app, tmp_path):
        path = write_png(tmp_path / 'existing.png')

        assert WatermarkService._ensure_default_watermark(path) == path

    def test_generation_failure_is_non_fatal(self, app, tmp_path, monkeypatch):
        def broken_new(*args, **kwargs):
            raise OSError('no display surface')

        monkeypatch.setattr(Image, 'new', broken_new)
        path = tmp_path / 'never-created.png'

        assert WatermarkService._ensure_default_watermark(str(path)) == str(path)
        assert not path.exists()

    def test_get_watermark_path_uses_configured_path(self, app, tmp_path):
        configured = tmp_path / 'configured.png'
        app.config['WATERMARK_DEFAULT_PATH'] = str(configured)

        result = WatermarkService.get_watermark_path()

        assert result == str(configured)
        assert configured.exists()

    def test_get_watermark_path_falls_back_without_app_context(self, app, monkeypatch):
        class BrokenApp:
            @property
            def config(self):
                raise RuntimeError('working outside of application context')

        monkeypatch.setattr(watermark_service_module, 'current_app', BrokenApp())

        result = WatermarkService.get_watermark_path()

        assert result.endswith(os.path.join('data', 'watermark', 'default.png'))


class TestResolveVectorPath:
    def test_non_zip_path_is_returned_unchanged(self, app, tmp_path):
        path = str(tmp_path / 'layer.shp')
        assert WatermarkService.resolve_vector_path(path) == path

    def test_empty_path_is_returned_unchanged(self, app):
        assert WatermarkService.resolve_vector_path('') == ''
        assert WatermarkService.resolve_vector_path(None) is None

    def test_extracts_shp_from_zip_and_cleans_up(self, app, tmp_path):
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        archive_path = tmp_path / 'layer.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('points.shp', b'fake-shp')
            archive.writestr('points.dbf', b'fake-dbf')

        shp_path = WatermarkService.resolve_vector_path(str(archive_path))
        extract_dir = os.path.dirname(shp_path)

        assert shp_path.endswith('.shp')
        assert os.path.exists(shp_path)

        WatermarkService.cleanup_vector_temp(shp_path)
        assert not os.path.exists(extract_dir)

    def test_zip_without_shp_is_rejected(self, app, tmp_path):
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        archive_path = tmp_path / 'empty.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('readme.txt', b'no shapes here')

        with pytest.raises(ValueError, match='未找到'):
            WatermarkService.resolve_vector_path(str(archive_path))
        assert os.listdir(tmp_path / 'uploads') == []

    def test_zip_with_path_traversal_is_rejected(self, app, tmp_path):
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        archive_path = tmp_path / 'evil.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('../evil.shp', b'fake-shp')

        with pytest.raises(ValueError, match='非法路径'):
            WatermarkService.resolve_vector_path(str(archive_path))
        assert os.listdir(tmp_path / 'uploads') == []

    def test_zip_with_too_many_entries_is_rejected(self, app, tmp_path):
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        archive_path = tmp_path / 'many.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            for index in range(1001):
                archive.writestr(f'part_{index}.txt', b'')

        with pytest.raises(ValueError, match='数量过多'):
            WatermarkService.resolve_vector_path(str(archive_path))

    def test_zip_exceeding_size_limit_is_rejected(self, app, tmp_path):
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        app.config['VECTOR_EXTRACT_MAX_BYTES'] = 10
        archive_path = tmp_path / 'big.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('data.shp', b'x' * 100)

        with pytest.raises(ValueError, match='体积超过限制'):
            WatermarkService.resolve_vector_path(str(archive_path))

    def test_cleanup_ignores_unregistered_paths(self, app, tmp_path):
        # 未由 resolve_vector_path 登记的路径必须原样保留，避免调用方误删文件
        foreign_file = tmp_path / 'keep-me.shp'
        foreign_file.write_bytes(b'keep')

        WatermarkService.cleanup_vector_temp(str(foreign_file))
        WatermarkService.cleanup_vector_temp(None)

        assert foreign_file.exists()


class TestEmbedWatermark:
    def test_already_embedded_is_rejected(self, app):
        asset = create_asset(watermark_status='embedded')

        result = WatermarkService.embed_watermark(asset)

        assert result == {'success': False, 'message': '资产已嵌入水印'}

    def test_missing_watermark_file_is_rejected(self, app, tmp_path):
        asset = create_asset()
        missing = tmp_path / 'missing.png'

        result = WatermarkService.embed_watermark(asset, watermark_path=str(missing))

        assert result == {'success': False, 'message': '水印图片不存在'}

    def test_unsupported_asset_type_is_rejected(self, app, tmp_path):
        asset = create_asset(asset_type='document')
        watermark = write_png(tmp_path / 'wm.png')

        result = WatermarkService.embed_watermark(asset, watermark_path=watermark)

        assert result['success'] is False
        assert '不支持的资产类型' in result['message']

    def test_embed_color_image_commits_asset_and_logs(self, app, tmp_path, sample_garden, monkeypatch):
        app.config['WATERMARK_FOLDER'] = str(tmp_path / 'out')
        watermark = write_png(tmp_path / 'wm.png')
        source = write_png(tmp_path / 'source.png', 'RGB')
        asset = create_asset(storage_path=source, garden_id=sample_garden)
        user = create_user()
        output = tmp_path / 'watermarked.png'
        captured = {}

        def fake_embed(**kwargs):
            captured.update(kwargs)
            output.write_bytes(b'fake-image')
            return {
                'watermarked_path': str(output),
                'watermark_id': 'ZY-IMG-20260101000000-ABCD',
                'psnr': 42.5,
            }

        monkeypatch.setattr(watermark_service_module, 'embed_raster_watermark_color', fake_embed)

        result = WatermarkService.embed_watermark(asset, user, watermark_path=watermark)

        assert result['success'] is True
        assert result['watermark_id'] == 'ZY-IMG-20260101000000-ABCD'
        assert result['psnr'] == 42.5
        assert captured['garden_code'] == 'ZY'
        assert captured['image_path'] == source
        assert asset.watermark_status == 'embedded'
        assert asset.watermarked_path == os.path.abspath(str(output))
        assert asset.watermark_embedded_at is not None

        log = OperationLog.query.filter_by(action='watermark_embed').one()
        assert log.user_id == user.id
        assert log.target_id == asset.id

    def test_embed_grayscale_image_uses_single_channel_algorithm(self, app, tmp_path, monkeypatch):
        app.config['WATERMARK_FOLDER'] = str(tmp_path / 'out')
        watermark = write_png(tmp_path / 'wm.png')
        source = write_png(tmp_path / 'gray.png', 'L')
        asset = create_asset(storage_path=source)
        calls = []

        def fake_gray(**kwargs):
            calls.append(kwargs)
            return {'watermarked_path': str(tmp_path / 'gray-out.png'), 'watermark_id': 'ZY-IMG-GRAY'}

        def fail_color(**kwargs):  # pragma: no cover - 断言不会走到彩色分支
            raise AssertionError('灰度图不应使用彩色水印算法')

        monkeypatch.setattr(watermark_service_module, 'embed_raster_watermark', fake_gray)
        monkeypatch.setattr(watermark_service_module, 'embed_raster_watermark_color', fail_color)

        result = WatermarkService.embed_watermark(asset, watermark_path=watermark)

        assert result['success'] is True
        assert len(calls) == 1
        assert calls[0]['method'] == 'dct'

    def test_embed_vector_asset_records_vr_value(self, app, tmp_path, monkeypatch):
        app.config['WATERMARK_FOLDER'] = str(tmp_path / 'out')
        watermark = write_png(tmp_path / 'wm.png')
        asset = create_asset(asset_type='vector', storage_path=str(tmp_path / 'fake.shp'))

        def fake_embed(**kwargs):
            assert kwargs['shpfile_path'].endswith('fake.shp')
            assert kwargs['asset_type_code'] == 'VEC'
            return {
                'zip_file_path': str(tmp_path / 'watermarked.zip'),
                'vr': [0.1, 0.2, 0.3],
                'watermark_id': 'ZY-VEC-20260101000000-ABCD',
            }

        monkeypatch.setattr(watermark_service_module, 'embed_vector_watermark', fake_embed)

        result = WatermarkService.embed_watermark(asset, watermark_path=watermark)

        assert result['success'] is True
        assert asset.vr_value == str([0.1, 0.2, 0.3])

    def test_embed_uses_configured_default_watermark(self, app, tmp_path, monkeypatch):
        app.config['WATERMARK_FOLDER'] = str(tmp_path / 'out')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'default.png')
        source = write_png(tmp_path / 'source.png', 'RGB')
        asset = create_asset(storage_path=source)
        captured = {}

        def fake_embed(**kwargs):
            captured.update(kwargs)
            return {'watermarked_path': str(tmp_path / 'out.png'), 'watermark_id': 'ZY-IMG-DEFAULT'}

        monkeypatch.setattr(watermark_service_module, 'embed_raster_watermark_color', fake_embed)

        result = WatermarkService.embed_watermark(asset)

        assert result['success'] is True
        assert captured['watermark_path'].endswith('default.png')

    def test_embed_algorithm_exception_returns_failure(self, app, tmp_path, monkeypatch):
        app.config['WATERMARK_FOLDER'] = str(tmp_path / 'out')
        watermark = write_png(tmp_path / 'wm.png')
        source = write_png(tmp_path / 'source.png', 'RGB')
        asset = create_asset(storage_path=source)

        def broken(**kwargs):
            raise RuntimeError('algorithm exploded')

        monkeypatch.setattr(watermark_service_module, 'embed_raster_watermark_color', broken)

        result = WatermarkService.embed_watermark(asset, watermark_path=watermark)

        assert result['success'] is False
        assert '水印嵌入失败' in result['message']
        assert 'algorithm exploded' in result['message']
        assert asset.watermark_status == 'none'


class TestExtractWatermark:
    def test_asset_without_watermark_is_rejected(self, app):
        asset = create_asset(watermark_status='none')

        result = WatermarkService.extract_watermark(asset)

        assert result == {'success': False, 'message': '资产未嵌入水印'}

    def test_missing_watermarked_file_is_rejected(self, app, tmp_path):
        asset = create_asset(watermark_status='embedded', watermarked_path=str(tmp_path / 'gone.png'))

        result = WatermarkService.extract_watermark(asset)

        assert result == {'success': False, 'message': '水印文件不存在'}

    def test_unsupported_asset_type_is_rejected(self, app, tmp_path):
        watermarked = write_png(tmp_path / 'marked.png')
        asset = create_asset(
            asset_type='document', watermark_status='embedded', watermarked_path=watermarked
        )

        result = WatermarkService.extract_watermark(asset)

        assert result['success'] is False
        assert '不支持的资产类型' in result['message']

    def test_extract_image_success_logs_operation(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        watermark = write_png(tmp_path / 'wm.png')
        watermarked = write_png(tmp_path / 'marked.png')
        asset = create_asset(watermark_status='embedded', watermarked_path=watermarked)
        user = create_user()

        def fake_extract(**kwargs):
            assert kwargs['watermarked_path'] == watermarked
            return {'extracted_watermark_path': str(tmp_path / 'extracted.png'), 'nc_value': 0.93}

        monkeypatch.setattr(watermark_service_module, 'extract_raster_watermark', fake_extract)

        result = WatermarkService.extract_watermark(asset, user, original_watermark_path=watermark)

        assert result['success'] is True
        assert result['watermark_path'] == str(tmp_path / 'extracted.png')
        assert result['nc_value'] == 0.93
        log = OperationLog.query.filter_by(action='watermark_extract').one()
        assert log.target_id == asset.id

    def test_extract_vector_success_parses_vr_value(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        watermarked = str(tmp_path / 'marked.shp')
        with open(watermarked, 'wb') as handle:
            handle.write(b'fake-shp')
        asset = create_asset(
            asset_type='vector',
            watermark_status='embedded',
            watermarked_path=watermarked,
            vr_value='[1.5, 2.5, 3.5]',
        )
        captured = {}

        def fake_extract(**kwargs):
            captured.update(kwargs)
            return {'watermark_path': str(tmp_path / 'wm-out.png'), 'nc_value': 0.8}

        monkeypatch.setattr(watermark_service_module, 'extract_vector_watermark', fake_extract)

        result = WatermarkService.extract_watermark(asset)

        assert result['success'] is True
        assert captured['vr'] == [1.5, 2.5, 3.5]
        assert captured['watermarked_shpfile_path'] == watermarked

    def test_extract_algorithm_exception_returns_failure(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        watermarked = write_png(tmp_path / 'marked.png')
        asset = create_asset(watermark_status='embedded', watermarked_path=watermarked)

        def broken(**kwargs):
            raise RuntimeError('extractor exploded')

        monkeypatch.setattr(watermark_service_module, 'extract_raster_watermark', broken)

        result = WatermarkService.extract_watermark(asset)

        assert result['success'] is False
        assert '水印提取失败' in result['message']


class TestVerifyWatermark:
    def test_asset_without_watermark_id(self, app):
        asset = create_asset(watermark_id=None)

        result = WatermarkService.verify_watermark(asset, 'anything')

        assert result['verified'] is False
        assert result['message'] == '资产未嵌入水印'

    def test_matching_watermark_id(self, app):
        asset = create_asset(watermark_id='ZY-IMG-20260101000000-ABCD')

        result = WatermarkService.verify_watermark(asset, 'ZY-IMG-20260101000000-ABCD')

        assert result['verified'] is True
        assert result['asset_code'] == asset.asset_code

    def test_mismatched_watermark_id(self, app):
        asset = create_asset(watermark_id='ZY-IMG-20260101000000-ABCD')

        result = WatermarkService.verify_watermark(asset, 'ZY-IMG-20260101000000-FFFF')

        assert result['verified'] is False
        assert result['expected'] == 'ZY-IMG-20260101000000-ABCD'
        assert result['provided'] == 'ZY-IMG-20260101000000-FFFF'


class TestTraceFromFile:
    def test_missing_file_is_rejected(self, app, tmp_path):
        result = WatermarkService.trace_from_file(str(tmp_path / 'missing.png'))

        assert result == {'success': False, 'message': '文件不存在'}

    def test_unsupported_extension_is_rejected(self, app, tmp_path):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'wm.png')
        text_file = tmp_path / 'notes.txt'
        text_file.write_text('hello')

        result = WatermarkService.trace_from_file(str(text_file))

        assert result['success'] is False
        assert '不支持的文件类型' in result['message']

    def test_trace_image_returns_watermark_id(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'wm.png')
        image_path = write_png(tmp_path / 'probe.png')

        def fake_extract(**kwargs):
            assert kwargs['watermarked_path'] == image_path
            return {'watermark_id': 'ZY-IMG-20260101000000-ABCD', 'nc_value': 0.91}

        monkeypatch.setattr(watermark_service_module, 'extract_raster_watermark', fake_extract)

        result = WatermarkService.trace_from_file(str(image_path))

        assert result['success'] is True
        assert result['watermark_id'] == 'ZY-IMG-20260101000000-ABCD'
        assert result['nc_value'] == 0.91

    def test_trace_without_extractable_id_returns_nc_value(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'wm.png')
        image_path = write_png(tmp_path / 'probe.png')

        monkeypatch.setattr(
            watermark_service_module,
            'extract_raster_watermark',
            lambda **kwargs: {'nc_value': 0.12},
        )

        result = WatermarkService.trace_from_file(str(image_path))

        assert result['success'] is False
        assert result['message'] == '未能提取有效水印ID'
        assert result['nc_value'] == 0.12

    def test_trace_vector_zip_extracts_and_cleans_temp_dir(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'wm.png')
        app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
        archive_path = tmp_path / 'probe.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('layer.shp', b'fake-shp')

        captured = {}

        def fake_extract(**kwargs):
            captured.update(kwargs)
            captured['shp_exists'] = os.path.exists(kwargs['watermarked_shpfile_path'])
            return {'watermark_id': 'ZY-VEC-20260101000000-ABCD', 'nc_value': 0.77}

        monkeypatch.setattr(watermark_service_module, 'extract_vector_watermark', fake_extract)

        result = WatermarkService.trace_from_file(str(archive_path))

        assert result['success'] is True
        assert captured['vr'] is None
        assert captured['shp_exists'] is True
        assert os.listdir(tmp_path / 'uploads') == []

    def test_trace_exception_returns_failure(self, app, tmp_path, monkeypatch):
        app.config['EXTRACTED_FOLDER'] = str(tmp_path / 'extracted')
        app.config['WATERMARK_DEFAULT_PATH'] = write_png(tmp_path / 'wm.png')
        image_path = write_png(tmp_path / 'probe.png')

        def broken(**kwargs):
            raise RuntimeError('trace exploded')

        monkeypatch.setattr(watermark_service_module, 'extract_raster_watermark', broken)

        result = WatermarkService.trace_from_file(str(image_path))

        assert result['success'] is False
        assert '水印溯源失败' in result['message']
        assert 'trace exploded' in result['message']
