"""证据链汇总

把资产的上传、水印、链上存证、证书、发布审核、授权与下载记录
整理成一条按时间推进的证据链，供资产详情、公开分享页和溯源报告复用。

设计约定：
- 只展示真实存在的数据，缺失节点明确标为 missing，不补造；
- 链上存证与平台业务台账分开标识，避免把可变的授权/下载数据
  与不可篡改的存证混为一谈；
- 公开视图（include_private=False）不输出用户身份、IP、授权方等敏感字段。
"""
from datetime import datetime

from flask import current_app

from app.models.asset import Asset
from app.models.blockchain import BlockchainTransaction, Certificate
from app.models.extra import DownloadRecord
from app.models.license import License
from app.models.user import User


STATE_DONE = 'done'
STATE_PENDING = 'pending'
STATE_WARNING = 'warning'
STATE_MISSING = 'missing'

CORE_KEYS = ('watermark', 'chain', 'certificate')


def _iso(value):
    return value.isoformat() if value else None


def _display_name(user):
    if not user:
        return None
    return user.nickname or user.username


def _item(key, title, state, time=None, description=None, fields=None, link=None,
          ledger=False):
    return {
        'key': key,
        'title': title,
        'state': state,
        'time': _iso(time),
        'description': description,
        'fields': fields or {},
        'link': link,
        'ledger': ledger
    }


def _watermark_item(asset):
    status = asset.watermark_status or 'none'
    if status in ('embedded', 'verified'):
        state = STATE_DONE
        description = '水印已写入文件，可作为副本归属比对的依据'
    elif status == 'pending':
        state = STATE_PENDING
        description = '水印处理中'
    elif status == 'failed':
        state = STATE_WARNING
        description = '水印处理失败，请查看操作日志后重试'
    else:
        state = STATE_MISSING
        description = '尚未嵌入水印'

    fields = {}
    if asset.watermark_id:
        fields['水印编号'] = asset.watermark_id
    if asset.watermark_id:
        fields['算法'] = 'DCT + QIM 盲水印' if asset.asset_type == 'image' else '矢量坐标水印'
    if asset.vr_value:
        try:
            import json
            parsed = json.loads(asset.vr_value)
            if isinstance(parsed, (int, float)):
                fields['校验值'] = f'{parsed:.4f}'
        except (TypeError, ValueError):
            pass

    return _item(
        'watermark',
        '水印嵌入',
        state,
        asset.watermark_embedded_at,
        description,
        fields
    )


def _chain_item(asset):
    tx = BlockchainTransaction.query.filter_by(
        asset_id=asset.id, tx_type='asset_register'
    ).order_by(BlockchainTransaction.id.desc()).first()

    status = asset.chain_status or 'none'
    if status == 'confirmed':
        state = STATE_DONE
        description = '文件指纹与水印编号已写入链上存证记录'
    elif status == 'pending':
        state = STATE_PENDING
        description = '存证交易等待确认'
    elif status == 'failed':
        state = STATE_WARNING
        description = '存证失败，可重新提交'
    else:
        state = STATE_MISSING
        description = '尚未上链存证'

    fields = {}
    if asset.chain_tx_hash:
        fields['交易哈希'] = asset.chain_tx_hash
    if tx and tx.block_number:
        fields['区块高度'] = str(tx.block_number)
    if asset.chain_timestamp:
        fields['确认时间'] = asset.chain_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    if not current_app.config.get('BLOCKCHAIN_ENABLED', False):
        fields['存证环境'] = '本地模拟链（未连接 FISCO BCOS 节点）'

    link = f'/certificate/{asset.certificate_id}' if asset.certificate_id else None
    return _item('chain', '链上存证', state, asset.chain_timestamp, description, fields, link)


def _certificate_item(asset):
    certificate = Certificate.query.filter_by(asset_id=asset.id).first()
    if not certificate:
        return _item(
            'certificate', '存证证书', STATE_MISSING,
            description='存证确认后才会签发证书'
        )

    expired = bool(certificate.valid_until and certificate.valid_until <= datetime.utcnow())
    if certificate.status == 'valid' and not expired:
        state = STATE_DONE
        description = '证书在有效期内'
    elif expired:
        state = STATE_WARNING
        description = '证书已过期'
    elif certificate.status == 'revoked':
        state = STATE_WARNING
        description = '证书已被撤销'
    else:
        state = STATE_WARNING
        description = '证书当前不可用'

    fields = {
        '证书编号': certificate.certificate_id,
        '状态': {'valid': '有效', 'revoked': '已撤销', 'expired': '已过期'}.get(
            certificate.status, certificate.status or '未知'
        )
    }
    if certificate.valid_until:
        fields['有效期至'] = certificate.valid_until.strftime('%Y-%m-%d')
    if certificate.file_hash:
        fields['证书文件指纹'] = certificate.file_hash

    return _item(
        'certificate',
        '证书签发',
        state,
        certificate.created_at,
        description,
        fields,
        f'/certificate/{certificate.certificate_id}'
    )


def _publish_item(asset):
    status = asset.status
    approver = User.query.get(asset.approver_id) if asset.approver_id else None

    if status == 'published':
        state = STATE_DONE
        description = '已通过审核并进入公开档案'
    elif status == 'pending':
        state = STATE_PENDING
        description = '等待资产管理员审核'
    elif status == 'rejected':
        state = STATE_WARNING
        description = asset.reject_reason or '审核未通过'
    elif status == 'deleted':
        state = STATE_WARNING
        description = '资产已删除'
    else:
        state = STATE_MISSING
        description = '草稿尚未提交发布'

    fields = {}
    if approver:
        fields['审核人'] = _display_name(approver)
    if asset.publish_at:
        fields['发布时间'] = asset.publish_at.strftime('%Y-%m-%d %H:%M:%S')
    if asset.reject_reason and status == 'rejected':
        fields['驳回原因'] = asset.reject_reason

    time_value = asset.publish_at or asset.approve_time
    return _item('publish', '审核发布', state, time_value, description, fields)


def _license_item(asset, include_private):
    count = License.query.filter_by(asset_id=asset.id).count()
    latest = License.query.filter_by(asset_id=asset.id).order_by(License.id.desc()).first()

    if count:
        state = STATE_DONE
        description = f'平台已生成 {count} 条授权记录'
    else:
        state = STATE_MISSING
        description = '尚未产生授权记录'

    fields = {'授权次数': str(count)}
    if latest:
        fields['最近授权'] = latest.license_code
        type_labels = {
            'personal': '个人学习', 'educational': '教学科研',
            'commercial': '商业使用', 'media': '媒体传播'
        }
        fields['授权类型'] = type_labels.get(latest.license_type, latest.license_type or '未注明')
        if latest.end_time:
            fields['授权到期'] = latest.end_time.strftime('%Y-%m-%d')
        if include_private:
            licensee = User.query.get(latest.licensee_id)
            if licensee:
                fields['被授权方'] = _display_name(licensee)

    return _item(
        'license', '授权记录', state,
        latest.created_at if latest else None,
        description, fields, ledger=True
    )


def _download_item(asset, include_private):
    count = asset.download_count or 0
    latest = DownloadRecord.query.filter_by(asset_id=asset.id).order_by(
        DownloadRecord.id.desc()
    ).first()

    if count:
        state = STATE_DONE
        description = f'平台累计记录 {count} 次下载'
    else:
        state = STATE_MISSING
        description = '暂无下载记录'

    fields = {'累计下载': str(count)}
    if latest:
        fields['最近下载'] = latest.created_at.strftime('%Y-%m-%d %H:%M:%S') if latest.created_at else ''
        if include_private and latest.user:
            fields['最近下载人'] = _display_name(latest.user)

    return _item(
        'download', '使用台账', state,
        latest.created_at if latest else None,
        description, fields, ledger=True
    )


def build_evidence(asset, include_private=False):
    """构建资产的证据链。

    Args:
        asset: Asset 实例
        include_private: 是否包含被授权方、下载人等内部信息
    """
    items = [
        _item(
            'upload', '上传登记', STATE_DONE, asset.created_at,
            '文件进入平台并生成唯一资产编码',
            {
                '资产编码': asset.asset_code,
                '文件指纹': asset.file_hash or '',
                '文件格式': asset.file_format or '',
                '上传者': _display_name(asset.uploader) or _display_name(asset.creator) or '',
            }
        ),
        _watermark_item(asset),
        _chain_item(asset),
        _certificate_item(asset),
        _publish_item(asset),
        _license_item(asset, include_private),
        _download_item(asset, include_private),
    ]

    states = {item['key']: item['state'] for item in items}
    core_done = all(states.get(key) == STATE_DONE for key in CORE_KEYS)
    core_started = any(states.get(key) != STATE_MISSING for key in CORE_KEYS)

    if core_done:
        level = 'complete'
        label = '证据链完整'
        description = '水印、链上存证与证书均已就绪，可用于副本比对与核验。'
    elif core_started:
        level = 'partial'
        label = '部分存证'
        description = '部分存证环节尚未完成，具体进度见下方时间线。'
    else:
        level = 'incomplete'
        label = '尚未存证'
        description = '该资产还未完成水印与链上存证。'

    return {
        'items': items,
        'summary': {
            'level': level,
            'label': label,
            'description': description,
            'verified': core_done,
            'watermark': states.get('watermark'),
            'chain': states.get('chain'),
            'certificate': states.get('certificate'),
            'file_hash': asset.file_hash,
            'generated_at': datetime.utcnow().isoformat()
        }
    }
