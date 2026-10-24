"""后台任务入口（兼容旧调用）

实际队列在 app/services/task_service.py：任务写入 async_tasks 表，
由进程内 worker 或 `flask tasks run` 领取执行。历史上的 Celery 版本
从未部署 worker，已移除，避免两套队列并存。
"""
from app.models.asset import Asset
from app.services import task_service
from app.services.ai_service import ai_service
from app.services.watermark_service import WatermarkService


def embed_watermark_task(asset_id):
    """把水印嵌入加入持久化队列"""
    asset = Asset.query.get(asset_id)
    if not asset:
        return {'success': False, 'message': '资产不存在'}
    task, created = task_service.enqueue_task('watermark_embed', asset)
    return {'success': True, 'task_id': task.id, 'created': created}


def extract_watermark_task(asset_id):
    """提取水印（同步执行，供脚本/内部调用）"""
    asset = Asset.query.get(asset_id)
    if not asset:
        return {'success': False, 'message': '资产不存在'}
    result = WatermarkService.extract_watermark(asset)
    return {'success': result['success'], 'message': result['message']}


def analyze_asset_task(asset_id):
    """AI 分析（同步执行；AI 未启用时由服务返回明确失败）"""
    asset = Asset.query.get(asset_id)
    if not asset:
        return {'success': False, 'message': '资产不存在'}
    result = ai_service.process_asset(asset)
    return {'success': result['success'], 'data': result.get('data')}


def batch_process_assets(asset_ids, operation='watermark'):
    """批量入队水印或存证任务，返回任务编号列表"""
    task_ids = []
    skipped = []
    for asset_id in asset_ids:
        asset = Asset.query.get(asset_id)
        if not asset:
            skipped.append(asset_id)
            continue
        task_type = 'watermark_embed' if operation == 'watermark' else 'blockchain_register'
        task, _created = task_service.enqueue_task(task_type, asset)
        task_ids.append(task.id)
    return {
        'success': True,
        'task_ids': task_ids,
        'count': len(task_ids),
        'skipped': skipped
    }
