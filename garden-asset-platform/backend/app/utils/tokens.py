"""Token 失效辅助

不修改 users 表结构：用 system_configs 记录每个用户的“token 失效时间点”，
密码修改/被管理员重置后，签发自该时间之前的 access/refresh token 全部失效。
"""
from datetime import datetime

from app.extensions import db
from app.models.extra import SystemConfig


def token_invalid_before_key(user_id):
    return f'token_invalid_before:{user_id}'


def invalidate_user_tokens(user_id):
    """让该用户当前已签发的所有 token 失效"""
    key = token_invalid_before_key(user_id)
    # 截断到秒，避免同一秒内新登录的 token 被误伤（比较时使用严格小于）
    cutoff = datetime.utcnow().replace(microsecond=0)
    config = SystemConfig.query.filter_by(key=key).first()
    if config:
        config.value = cutoff.isoformat()
    else:
        config = SystemConfig(
            key=key,
            value=cutoff.isoformat(),
            description=f'用户 {user_id} 的 token 失效时间点'
        )
        db.session.add(config)
    return cutoff


def user_token_invalid_before(user_id):
    config = SystemConfig.query.filter_by(
        key=token_invalid_before_key(user_id)
    ).first()
    if not config or not config.value:
        return None
    try:
        return datetime.fromisoformat(config.value)
    except (TypeError, ValueError):
        return None
