"""授权合同正文测试

合同按当前授权记录实时生成：类型与结构化范围使用中文，
续期后的起止时间以最新授权为准。
"""
from datetime import datetime
from types import SimpleNamespace

from app.resources.license import build_contract_content


def make_license(**overrides):
    data = {
        'license_code': 'LIC-TEST-001',
        'licensor': SimpleNamespace(username='owner'),
        'licensee': SimpleNamespace(username='user1'),
        'version_no': 2,
        'usage_scope': '用于课程教学',
        'license_type': 'non_commercial',
        'start_time': datetime(2026, 1, 1),
        'end_time': datetime(2027, 1, 1),
        'is_exclusive': False,
        'usage_purpose_code': 'teaching_research',
        'allowed_channels': ['online', 'print'],
        'allowed_formats': ['JPG', 'PNG'],
        'max_downloads': 20,
        'territory': '中国大陆',
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_contract_localizes_type_and_structured_scope():
    license_row = make_license()
    asset = SimpleNamespace(title='拙政园荷风四面亭', asset_code='ZZY-IMG-001')

    text = build_contract_content(license_row, asset)

    assert '合同编号：LIC-TEST-001' in text
    assert '授权类型：非商业使用' in text
    assert '授权版本：v2' in text
    assert '使用目的：教学科研' in text
    assert '使用渠道：网络发布、印刷出版' in text
    assert '可下载格式：JPG、PNG' in text
    assert '下载次数上限：20 次' in text
    assert '授权期限：2026-01-01 至 2027-01-01' in text


def test_contract_reflects_renewed_dates():
    license_row = make_license(end_time=datetime(2028, 6, 30))
    asset = SimpleNamespace(title='留园冠云峰', asset_code='LY-IMG-002')

    text = build_contract_content(license_row, asset)

    assert '2028-06-30' in text
    assert '2027-01-01' not in text
