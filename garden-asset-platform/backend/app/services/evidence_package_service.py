"""资产证据包导出

把一个资产的当前文件、证据链、证书、版本记录与 SHA-256 清单打成
ZIP，供权利人或资产管理员留档、离线核验或提交给第三方。

证据包不会修改资产状态，也不写入下载台账；临时文件在响应结束后清理。
"""
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from flask import current_app

from app.models.asset import AssetVersion
from app.models.blockchain import Certificate
from app.services.evidence_service import build_evidence

PACKAGE_SCHEMA = 'chainauth-evidence-package/1'
DEFAULT_MAX_BYTES = 200 * 1024 * 1024


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')


def _iso(value):
    return value.isoformat() if value else None


def _display_name(user):
    if not user:
        return None
    return user.nickname or user.username


def _safe_code(value):
    cleaned = ''.join(
        ch if ch.isalnum() or ch in '-_' else '-'
        for ch in (value or 'asset')
    )
    return cleaned[:80] or 'asset'


def _current_version(asset):
    return AssetVersion.query.filter_by(
        asset_id=asset.id
    ).order_by(AssetVersion.version_no.desc()).first()


def _file_candidates(asset, current_version):
    """返回当前原文件与水印副本的候选信息，按真实路径去重。"""
    candidates = []
    seen = set()

    def add(role, path, recorded_hash, file_name=None, file_format=None):
        if not path:
            return
        absolute = os.path.abspath(path)
        key = os.path.normcase(absolute)
        if key in seen:
            return
        seen.add(key)
        exists = os.path.isfile(absolute)
        candidates.append({
            'role': role,
            'path': absolute,
            'exists': exists,
            'recorded_hash': recorded_hash,
            'file_name': file_name or os.path.basename(path),
            'file_format': file_format or os.path.splitext(path)[1].lstrip('.').upper(),
            'size': os.path.getsize(absolute) if exists else None,
        })

    if current_version and current_version.file_path:
        add(
            'original',
            current_version.file_path,
            current_version.file_hash,
            current_version.file_name,
            current_version.file_format,
        )
    if asset.storage_path and (
        not candidates or not candidates[0]['exists']
    ):
        add('original', asset.storage_path, asset.file_hash,
            None, asset.file_format)
    add('watermarked', asset.watermarked_path, None, None, None)

    return candidates


def _version_payload(asset, current_version):
    versions = AssetVersion.query.filter_by(
        asset_id=asset.id
    ).order_by(AssetVersion.version_no.asc()).all()
    return [
        version.to_dict(
            is_current=bool(current_version and version.id == current_version.id)
        )
        for version in versions
    ]


def _certificate_payloads(asset, current_version, base_url):
    certificates = Certificate.query.filter_by(
        asset_id=asset.id
    ).order_by(Certificate.id.desc()).all()
    payloads = []
    for certificate in certificates:
        payload = certificate.to_dict()
        payload['is_current'] = bool(
            current_version
            and certificate.version_id == current_version.id
        )
        payload['certificate_url'] = (
            f'{base_url}/certificate/{certificate.certificate_id}'
        )
        payloads.append(payload)
    return payloads


def _readme(manifest):
    asset = manifest['asset']
    verification = manifest['verification']
    lines = [
        '苏州园林数字资产平台 · 资产证据包',
        '====================================',
        '',
        f"资产编码：{asset['asset_code']}",
        f"资产标题：{asset['title']}",
        f"水印编号：{asset.get('watermark_id') or '未嵌入'}",
        f"生成时间：{manifest['generated_at']}",
        f"生成人：{manifest.get('generated_by') or '平台用户'}",
        '',
        '包含内容',
        '--------',
        '- manifest.json：资产、版本、水印、存证、证书与文件哈希清单',
        '- evidence-chain.json：上传、水印、存证、证书、发布、授权与下载台账',
        '- certificates/：按版本签发的证书记录（如有）',
        '- files/：当前版本原文件与水印副本（受大小限制，见 manifest）',
        '- SHA256SUMS：包内文件的 SHA-256 校验值',
        '',
        '核验步骤',
        '--------',
        '1. 校验文件哈希：Linux/macOS 执行 `sha256sum -c SHA256SUMS`；',
        '   Windows 可对每个文件执行 `certutil -hashfile <文件> SHA256` 后与清单比对。',
        f"2. 打开溯源页 {verification['trace_url']}，上传 files/ 中的水印副本，核对水印编号与资产。",
    ]
    if verification.get('certificate_url'):
        lines.append(
            f"3. 打开证书 {verification['certificate_url']}，核对证书编号、文件哈希与版本。"
        )
    else:
        lines.append('3. 当前资产尚未签发证书，证据链中会标记缺失环节。')
    lines.extend([
        '4. 证据链中的“授权记录 / 使用台账”属于平台业务台账；',
        '   只有“水印、存证、证书”等核心存证环节才属于不可篡改证据。',
        '',
        '边界说明',
        '--------',
        f"- 当前区块链模式：{manifest['chain']['mode']}。",
        '- 本地模拟存证不能用于链上复核；接入 FISCO BCOS 后需按交易哈希在链上验证。',
        '- 证据包只证明平台记录与文件在导出时的对应关系，不替代司法鉴定或版权登记。',
        '- 历史版本文件不随包导出，版本记录与对应证书仍保留在清单中。',
        '',
        f"清单校验值：{manifest.get('checksum', '见 SHA256SUMS')}",
    ])
    return '\n'.join(lines) + '\n'


def build_evidence_package(asset, user=None, include_files=True):
    """构建证据包 ZIP。

    Returns:
        dict: path、filename、workdir、included_files、omitted、manifest

    Raises:
        Exception: 构建失败时抛出，临时目录会被清理。
    """
    upload_root = os.path.abspath(os.path.join(
        current_app.config.get('UPLOAD_FOLDER', './uploads'), 'evidence_tmp'
    ))
    os.makedirs(upload_root, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix='evidence_', dir=upload_root)

    max_bytes = int(current_app.config.get(
        'EVIDENCE_PACKAGE_MAX_BYTES', DEFAULT_MAX_BYTES
    ))
    base_url = str(current_app.config.get(
        'PUBLIC_BASE_URL', 'http://localhost:5173'
    )).rstrip('/')
    current_version = _current_version(asset)
    candidates = _file_candidates(asset, current_version)
    existing = [item for item in candidates if item['exists']]
    total_bytes = sum(item['size'] or 0 for item in existing)

    omitted_reason = None
    include_binaries = bool(include_files and existing)
    if not include_files:
        omitted_reason = '请求仅导出清单（include_files=0）'
    elif existing and total_bytes > max_bytes:
        include_binaries = False
        omitted_reason = f'文件总大小超过 {max_bytes // 1024 // 1024}MB 限制'
    elif not existing:
        omitted_reason = '服务器上未找到当前文件'

    files_meta = []
    binary_entries = []
    for item in candidates:
        arc_ext = (
            os.path.splitext(item['path'])[1]
            or (f".{(item['file_format'] or 'bin').lower()}")
        )
        arcname = f"files/{_safe_code(asset.asset_code)}-{item['role']}{arc_ext.lower()}"
        included = bool(include_binaries and item['exists'])
        entry = {
            'role': item['role'],
            'name': arcname,
            'file_name': item['file_name'],
            'file_format': item['file_format'],
            'size': item['size'],
            'sha256': item['recorded_hash'],
            'hash_source': 'record' if item['recorded_hash'] else None,
            'included': included,
        }
        if included:
            actual_hash = _sha256_file(item['path'])
            entry['sha256'] = actual_hash
            entry['hash_source'] = 'computed'
            entry['hash_matches_record'] = (
                actual_hash == item['recorded_hash']
                if item['recorded_hash'] else None
            )
            binary_entries.append((arcname, item['path'], actual_hash))
        else:
            entry['reason'] = omitted_reason or '未包含'
        files_meta.append(entry)

    versions = _version_payload(asset, current_version)
    certificates = _certificate_payloads(asset, current_version, base_url)
    certificate_url = (
        f"{base_url}/certificate/{asset.certificate_id}"
        if asset.certificate_id else None
    )
    evidence = build_evidence(asset, include_private=True)

    manifest = {
        'schema': PACKAGE_SCHEMA,
        'generated_at': _iso(datetime.utcnow()),
        'generated_by': _display_name(user),
        'platform': {
            'name': '苏州园林数字资产平台',
            'trace_url': f'{base_url}/trace',
        },
        'asset': {
            'id': asset.id,
            'asset_code': asset.asset_code,
            'title': asset.title,
            'description': asset.description,
            'asset_type': asset.asset_type,
            'file_format': asset.file_format,
            'file_size': asset.file_size,
            'file_hash': (
                current_version.file_hash if current_version
                else asset.file_hash
            ),
            'status': asset.status,
            'watermark_id': asset.watermark_id,
            'watermark_status': asset.watermark_status,
            'chain_status': asset.chain_status,
            'certificate_id': asset.certificate_id,
            'garden': (
                {'code': asset.garden.code, 'name': asset.garden.name}
                if asset.garden else None
            ),
            'owner': _display_name(asset.owner),
            'uploader': _display_name(asset.uploader),
            'tags': [tag.tag_name for tag in asset.tags],
            'created_at': _iso(asset.created_at),
            'publish_at': _iso(asset.publish_at),
            'view_count': asset.view_count or 0,
            'download_count': asset.download_count or 0,
            'license_count': asset.license_count or 0,
        },
        'current_version': (
            current_version.to_dict(is_current=True) if current_version else None
        ),
        'versions': versions,
        'watermark': {
            'status': asset.watermark_status,
            'watermark_id': asset.watermark_id,
            'embedded_at': _iso(asset.watermark_embedded_at),
        },
        'chain': {
            'status': asset.chain_status,
            'tx_hash': asset.chain_tx_hash,
            'timestamp': _iso(asset.chain_timestamp),
            'certificate_id': asset.certificate_id,
            'mode': (
                'fisco-bcos'
                if current_app.config.get('BLOCKCHAIN_ENABLED') else
                'local-simulated'
            ),
            'simulated': not current_app.config.get('BLOCKCHAIN_ENABLED', False),
        },
        'certificates': certificates,
        'evidence': evidence,
        'files': files_meta,
        'binary_policy': {
            'include_files': include_files,
            'max_bytes': max_bytes,
            'existing_bytes': total_bytes,
            'included': include_binaries,
            'omitted_reason': omitted_reason,
        },
        'verification': {
            'trace_url': f'{base_url}/trace',
            'certificate_url': certificate_url,
            'hash_algorithm': 'SHA-256',
            'instructions': [
                '按 SHA256SUMS 校验包内文件，先确认 manifest.json 未被篡改。',
                '将 files/ 中的水印副本上传到溯源页，核对水印编号与资产编码。',
                '打开证书地址，核对证书编号、文件哈希与版本号。',
                '业务台账（授权/下载）不等同于不可篡改存证，需结合核心存证环节判断。',
            ],
        },
        'disclaimer': (
            '本地模拟存证不能用于链上复核；证据包证明平台记录与文件在导出时的对应关系，'
            '不替代司法鉴定或版权登记。'
        ),
    }

    filename = (
        f"{_safe_code(asset.asset_code)}-evidence-"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    )
    zip_path = os.path.join(workdir, filename)

    text_entries = {
        'README.txt': b'',
        'evidence-chain.json': _json_bytes(evidence),
        'manifest.json': b'',
    }
    for certificate in certificates:
        text_entries[
            f"certificates/{certificate['certificate_id']}.json"
        ] = _json_bytes(certificate)

    contents = [
        'README.txt', 'manifest.json', 'evidence-chain.json',
        *[f"certificates/{certificate['certificate_id']}.json" for certificate in certificates],
        *[entry[0] for entry in binary_entries],
        'SHA256SUMS',
    ]
    manifest['contents'] = contents
    manifest['checksum'] = (
        'SHA-256 见 SHA256SUMS（manifest.json 的校验值也在其中）'
    )
    text_entries['manifest.json'] = _json_bytes(manifest)
    text_entries['README.txt'] = _readme(manifest).encode('utf-8')

    try:
        checksum_lines = []
        for name, data in text_entries.items():
            checksum_lines.append(
                f"{hashlib.sha256(data).hexdigest()}  {name}"
            )
        checksum_lines.extend(
            f"{digest}  {arcname}"
            for arcname, _, digest in binary_entries
        )
        checksum_bytes = ('\n'.join(sorted(checksum_lines)) + '\n').encode('utf-8')

        with zipfile.ZipFile(
            zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for name, data in text_entries.items():
                archive.writestr(name, data)
            for arcname, source_path, _ in binary_entries:
                archive.write(source_path, arcname)
            archive.writestr('SHA256SUMS', checksum_bytes)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    return {
        'path': zip_path,
        'filename': filename,
        'workdir': workdir,
        'included_files': len(binary_entries),
        'omitted': not include_binaries,
        'manifest': manifest,
    }
