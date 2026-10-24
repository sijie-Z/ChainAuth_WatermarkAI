"""审计日志完整性校验与补签"""
import logging
from datetime import datetime

from app.extensions import db
from app.models import OperationLog
from app.utils.audit import get_audit_key, sign_log

logger = logging.getLogger(__name__)


def verify_audit_logs():
    """逐条重算 HMAC 并返回统计。

    Returns:
        dict: total / signed / unsigned / valid / invalid / status / samples
    """
    key = get_audit_key()
    logs = OperationLog.query.order_by(OperationLog.id.asc()).all()

    signed = 0
    unsigned = 0
    valid = 0
    invalid = 0
    samples = []

    for log in logs:
        if not log.integrity_hash:
            unsigned += 1
            continue
        signed += 1
        if not key:
            continue
        expected = sign_log(log, key=key)
        if expected == log.integrity_hash:
            valid += 1
        else:
            invalid += 1
            if len(samples) < 20:
                samples.append({
                    'id': log.id,
                    'action': log.action,
                    'module': log.module,
                    'created_at': (
                        log.created_at.isoformat() if log.created_at else None
                    ),
                })

    if not key:
        status = 'unavailable'
        label = '未配置审计签名密钥'
    elif invalid:
        status = 'invalid'
        label = f'发现 {invalid} 条日志签名不一致'
    elif unsigned:
        status = 'unsigned'
        label = f'有 {unsigned} 条历史日志尚未签名'
    else:
        status = 'ok'
        label = '全部日志签名有效'

    return {
        'status': status,
        'label': label,
        'total': len(logs),
        'signed': signed,
        'unsigned': unsigned,
        'valid': valid,
        'invalid': invalid,
        'samples': samples,
        'generated_at': datetime.utcnow().isoformat(),
    }


def rebuild_audit_signatures(batch_size=500):
    """为全部日志重算签名（用于历史数据补签或密钥轮换后重建）。"""
    key = get_audit_key()
    if not key:
        raise RuntimeError('未配置审计签名密钥')

    logs = OperationLog.query.order_by(OperationLog.id.asc()).all()
    updated = 0
    for index, log in enumerate(logs, start=1):
        log.integrity_hash = sign_log(log, key=key)
        updated += 1
        if index % max(1, batch_size) == 0:
            db.session.commit()
    db.session.commit()
    logger.info('审计日志补签完成: %s 条', updated)
    return {'updated': updated, 'total': len(logs)}
