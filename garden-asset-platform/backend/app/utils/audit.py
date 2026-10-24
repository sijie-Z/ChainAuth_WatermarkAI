"""审计日志完整性签名

每条操作日志在写入时用一个只存在于服务端的密钥计算 HMAC-SHA256。
后台校验时重新计算并比对，发现日志字段被修改会立即暴露。

这是“防篡改检测”，不是防删除：拥有数据库写权限的人仍可删除整条日志，
因此审计日志的删除权限仍需独立控制。
"""
import hashlib
import hmac
import json

from flask import current_app, has_app_context


def get_audit_key():
    """返回审计签名密钥；优先使用独立配置，否则回退到 SECRET_KEY。"""
    if not has_app_context():
        return None
    key = (
        current_app.config.get('AUDIT_HMAC_KEY')
        or current_app.config.get('SECRET_KEY')
    )
    return str(key) if key else None


def canonical_log_payload(log):
    """把日志中参与签名的字段规范化为稳定 JSON。

    通过 JSON 往返把元组等对象变成数据库读回后的形态，避免写入端
    与校验端的序列化差异造成误报。
    """
    payload = {
        'user_id': log.user_id,
        'user_name': log.user_name,
        'user_role': log.user_role,
        'action': log.action,
        'module': log.module,
        'description': log.description,
        'target_type': log.target_type,
        'target_id': log.target_id,
        'ip_address': log.ip_address,
        'user_agent': log.user_agent,
        'request_url': log.request_url,
        'request_method': log.request_method,
        'status': log.status,
        'error_message': log.error_message,
        'extra_data': log.extra_data,
        'created_at': log.created_at.isoformat() if log.created_at else None,
    }
    normalized = json.loads(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, default=str
    ))
    return json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')


def sign_log(log, key=None):
    """计算一条日志的 HMAC；无密钥时返回 None。"""
    key = key or get_audit_key()
    if not key:
        return None
    return hmac.new(
        key.encode('utf-8'),
        canonical_log_payload(log),
        hashlib.sha256,
    ).hexdigest()
