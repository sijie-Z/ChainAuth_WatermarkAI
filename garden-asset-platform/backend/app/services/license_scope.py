"""授权范围定义与执行

usage_scope 文本用于合同描述；真正可执行的是结构化字段：
使用目的、使用渠道、可下载格式、地域与下载次数上限。
历史授权这些字段为空时视为不限制，保持兼容。
"""

PURPOSE_OPTIONS = {
    'personal_learning': '个人学习',
    'teaching_research': '教学科研',
    'commercial_marketing': '商业宣传',
    'publication': '出版发行',
    'exhibition': '公开展览',
    'derivative': '衍生创作',
    'other': '其他',
}

TERRITORY_OPTIONS = ('中国大陆', '中国港澳台', '全球', '海外')

CHANNEL_OPTIONS = {
    'online': '网络发布',
    'print': '印刷出版',
    'exhibition': '公开展览',
    'broadcast': '广播传播',
}

FORMAT_LIMITS = {
    'image': ('JPG', 'PNG', 'TIFF', 'WEBP'),
    'vector': ('ZIP', 'SHP', 'GEOJSON', 'KML'),
    'document': ('PDF', 'DOC', 'DOCX', 'DWG', 'DXF'),
    'video': ('MP4', 'MOV', 'AVI', 'MKV'),
    'model': ('OBJ', 'FBX', 'GLTF', 'GLB', 'STL', 'ZIP'),
}


def normalize_list(value, allowed=None):
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        return None
    result = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        if allowed is not None and text not in allowed:
            return None
        if text not in result:
            result.append(text)
    return result


def format_options(asset):
    """按资产类型给出可申请的下载格式"""
    options = list(FORMAT_LIMITS.get(asset.asset_type, ()))
    current = (asset.file_format or '').upper()
    if current and current not in options:
        options.insert(0, current)
    return options


def validate_application_scope(data, asset):
    """校验申请中的结构化范围，返回 (fields, error)。"""
    purpose_code = (data.get('usage_purpose_code') or '').strip() or None
    if purpose_code and purpose_code not in PURPOSE_OPTIONS:
        return None, '使用目的选项无效'

    channels = normalize_list(data.get('allowed_channels'), set(CHANNEL_OPTIONS))
    if channels is None:
        return None, '使用渠道选项无效'

    allowed_formats = normalize_list(data.get('allowed_formats'))
    if allowed_formats is None:
        return None, '可下载格式格式错误'
    allowed_formats = [item.upper() for item in allowed_formats]
    available = set(format_options(asset))
    invalid = [item for item in allowed_formats if item not in available]
    if invalid:
        return None, f'可下载格式不属于该资产: {", ".join(invalid)}'
    if len(allowed_formats) > 10:
        return None, '可下载格式不能超过 10 项'

    max_downloads = data.get('max_downloads')
    if max_downloads in (None, ''):
        max_downloads = None
    else:
        try:
            max_downloads = int(max_downloads)
        except (TypeError, ValueError):
            return None, '下载次数上限必须是整数'
        if max_downloads < 1 or max_downloads > 10000:
            return None, '下载次数上限需在 1-10000 之间'

    territory = (data.get('territory') or '').strip() or '中国大陆'
    if len(territory) > 100:
        return None, '授权地域过长'

    return {
        'usage_purpose_code': purpose_code,
        'allowed_channels': channels,
        'allowed_formats': allowed_formats,
        'max_downloads': max_downloads,
        'territory': territory,
    }, None


def scope_violation(license_row, *, source_format=None, purpose=None,
                    territory=None, current_version_id=None,
                    current_version_no=None):
    """检查一次下载是否在授权范围内；返回拒绝原因或 None。"""
    if not license_row:
        return '无有效授权'

    if license_row.version_id and license_row.version_id != current_version_id:
        licensed = (
            f'v{license_row.version_no}' if license_row.version_no else '历史版本'
        )
        current = f'v{current_version_no}' if current_version_no else '当前版本'
        return f'该授权对应 {licensed}，资产当前为 {current}，请重新申请授权'

    allowed_formats = [str(item).upper() for item in (license_row.allowed_formats or [])]
    if allowed_formats and source_format:
        if str(source_format).upper() not in allowed_formats:
            return f'当前授权仅允许下载 {"/".join(allowed_formats)} 格式'

    required_purpose = license_row.usage_purpose_code
    if required_purpose:
        if not purpose:
            return f'请声明使用目的（授权用途：{PURPOSE_OPTIONS.get(required_purpose, required_purpose)}）'
        if purpose != required_purpose:
            return (
                f'申报用途与授权不符：授权用途为 '
                f'{PURPOSE_OPTIONS.get(required_purpose, required_purpose)}'
            )

    licensed_territory = (license_row.territory or '').strip()
    if licensed_territory in TERRITORY_OPTIONS:
        if not territory:
            return f'请声明使用地域（授权地域：{licensed_territory}）'
        if licensed_territory != '全球' and territory != licensed_territory:
            return f'申报地域与授权不符：授权地域为 {licensed_territory}'
        if territory not in TERRITORY_OPTIONS:
            return '使用地域选项无效'

    if (
        license_row.max_downloads is not None
        and (license_row.download_count or 0) >= license_row.max_downloads
    ):
        return f'该授权下载次数已用完（上限 {license_row.max_downloads} 次）'

    return None


def scope_summary(license_row):
    """合同/详情中展示的结构化范围摘要"""
    parts = []
    if license_row.version_no:
        parts.append(f"授权版本：v{license_row.version_no}")
    if license_row.usage_purpose_code:
        parts.append(
            f"使用目的：{PURPOSE_OPTIONS.get(license_row.usage_purpose_code, license_row.usage_purpose_code)}"
        )
    channels = [
        CHANNEL_OPTIONS.get(item, item)
        for item in (license_row.allowed_channels or [])
    ]
    if channels:
        parts.append(f"使用渠道：{'、'.join(channels)}")
    if license_row.allowed_formats:
        parts.append(f"可下载格式：{'、'.join(license_row.allowed_formats)}")
    if license_row.max_downloads is not None:
        parts.append(f"下载次数上限：{license_row.max_downloads} 次")
    if license_row.territory:
        parts.append(f"授权地域：{license_row.territory}")
    return '；'.join(parts) or '按授权合同约定'
