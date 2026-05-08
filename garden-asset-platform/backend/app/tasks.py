"""
后台任务模块
用于处理异步任务，如批量水印处理、AI分析等
"""
from celery import Celery
from app.extensions import db
from app.services.watermark_service import WatermarkService
from app.services.ai_service import ai_service
from app.models.asset import Asset

celery = Celery('garden_asset')


def init_celery(app):
    """初始化Celery"""
    celery.conf.update(
        broker_url=app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
        result_backend=app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask


@celery.task
def embed_watermark_task(asset_id):
    """异步嵌入水印"""
    asset = Asset.query.get(asset_id)
    if asset:
        result = WatermarkService.embed_watermark(asset)
        return {'success': result['success'], 'message': result['message']}
    return {'success': False, 'message': '资产不存在'}


@celery.task
def extract_watermark_task(asset_id):
    """异步提取水印"""
    asset = Asset.query.get(asset_id)
    if asset:
        result = WatermarkService.extract_watermark(asset)
        return {'success': result['success'], 'message': result['message']}
    return {'success': False, 'message': '资产不存在'}


@celery.task
def analyze_asset_task(asset_id):
    """异步分析资产"""
    asset = Asset.query.get(asset_id)
    if asset:
        result = ai_service.process_asset(asset)
        return {'success': result['success'], 'data': result.get('data')}
    return {'success': False, 'message': '资产不存在'}


@celery.task
def batch_process_assets(asset_ids, operation='watermark'):
    """批量处理资产"""
    results = []
    for asset_id in asset_ids:
        if operation == 'watermark':
            result = embed_watermark_task.delay(asset_id)
            results.append(result.id)
    return {'task_ids': results, 'count': len(results)}
