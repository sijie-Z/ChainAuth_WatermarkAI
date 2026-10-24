"""证据包核验

对用户上传的证据包 ZIP 做三层检查：
1. ZIP 结构与安全（路径、条目数、解压体积）；
2. 包内完整性（SHA256SUMS、manifest 中的文件哈希）；
3. 平台登记一致性（资产编码、水印编号、证书与当前版本哈希）。

核验不依赖平台私钥，也不证明司法意义上的真实性；它回答的是
“这个包是否完整，以及包内记录是否与平台台账一致”。
"""
import hashlib
import json
import zipfile
from pathlib import PurePosixPath

from app.models import Asset
from app.models.asset import AssetVersion
from app.models.blockchain import Certificate

SCHEMA = 'chainauth-evidence-package/1'
MAX_ENTRIES = 200
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024


def _check(key, label, status, detail):
    return {'key': key, 'label': label, 'status': status, 'detail': detail}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _normalize_name(name):
    if not isinstance(name, str):
        return None
    normalized = name.replace('\\', '/')
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith('/')
        or '..' in path.parts
        or any(part in ('', '.') for part in path.parts)
    ):
        return None
    return normalized


def _read_entry(archive, name, limit=MAX_UNCOMPRESSED_BYTES):
    info = archive.getinfo(name)
    if info.file_size > limit:
        raise ValueError(f'文件过大: {name}')
    try:
        return archive.read(name)
    except RuntimeError as exc:
        raise ValueError('证据包包含加密文件，无法核验') from exc


def _verify_checksums(archive, names):
    if 'SHA256SUMS' not in names:
        return False, '缺少 SHA256SUMS', []
    try:
        text = _read_entry(archive, 'SHA256SUMS', limit=1024 * 1024).decode('utf-8')
    except (UnicodeDecodeError, ValueError):
        return False, 'SHA256SUMS 无法解析', []

    errors = []
    checked = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            errors.append('校验行格式不正确')
            continue
        digest, name = parts
        name = _normalize_name(name.strip())
        if not name or name not in names:
            errors.append(f'校验文件不存在: {name or "非法路径"}')
            continue
        try:
            actual = _sha256(_read_entry(archive, name))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if actual.lower() != digest.lower():
            errors.append(f'哈希不一致: {name}')
            continue
        checked.append(name)

    if errors:
        return False, '；'.join(errors[:5]), checked
    return True, f'已校验 {len(checked)} 个文件', checked


def _verify_manifest_files(archive, manifest, names):
    entries = manifest.get('files')
    if not isinstance(entries, list):
        return False, 'manifest.files 格式不正确'
    errors = []
    checked = 0
    for item in entries:
        if not isinstance(item, dict) or not item.get('included'):
            continue
        name = _normalize_name(item.get('name'))
        expected = item.get('sha256')
        if not name or name not in names:
            errors.append(f"包内缺少文件: {item.get('name')}")
            continue
        try:
            actual = _sha256(_read_entry(archive, name))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not expected or actual.lower() != str(expected).lower():
            errors.append(f'文件哈希与清单不一致: {name}')
            continue
        checked += 1
    if errors:
        return False, '；'.join(errors[:5])
    return True, f'已核对 {checked} 个文件'


def _registry_checks(manifest):
    checks = []
    asset_info = manifest.get('asset') or {}
    asset_code = asset_info.get('asset_code')
    asset = Asset.query.filter_by(asset_code=asset_code).first() if asset_code else None

    if not asset:
        checks.append(_check(
            'asset_registry', '资产登记匹配', 'fail',
            f'平台未找到资产编码 {asset_code or "（缺失）"}'
        ))
        return checks, None, False

    detail = f'已找到资产 {asset.asset_code}'
    if asset.status == 'deleted':
        checks.append(_check('asset_registry', '资产登记匹配', 'warn', '资产已被删除'))
    elif asset.status != 'published':
        checks.append(_check('asset_registry', '资产登记匹配', 'warn', f'{detail}（当前状态：{asset.status}）'))
    else:
        checks.append(_check('asset_registry', '资产登记匹配', 'pass', detail))

    package_watermark = (manifest.get('watermark') or {}).get('watermark_id')
    if package_watermark and asset.watermark_id:
        if package_watermark == asset.watermark_id:
            checks.append(_check(
                'watermark', '水印编号匹配', 'pass',
                f'水印编号 {package_watermark} 与平台登记一致'
            ))
        else:
            checks.append(_check(
                'watermark', '水印编号匹配', 'fail',
                f'包内 {package_watermark}，平台为 {asset.watermark_id}'
            ))
    else:
        checks.append(_check(
            'watermark', '水印编号匹配', 'warn',
            '证据包或平台记录中没有水印编号'
        ))

    current_version = AssetVersion.query.filter_by(
        asset_id=asset.id
    ).order_by(AssetVersion.version_no.desc()).first()
    expected_hash = (
        current_version.file_hash if current_version
        else asset.file_hash
    )
    package_hash = asset_info.get('file_hash')
    if expected_hash and package_hash:
        if expected_hash.lower() == str(package_hash).lower():
            checks.append(_check(
                'version_hash', '当前版本文件哈希', 'pass',
                '证据包对应平台当前版本'
            ))
        else:
            historical = AssetVersion.query.filter_by(
                asset_id=asset.id, file_hash=str(package_hash)
            ).order_by(AssetVersion.version_no.desc()).first()
            if historical:
                checks.append(_check(
                    'version_hash', '当前版本文件哈希', 'warn',
                    f'证据包对应历史版本 v{historical.version_no}，平台已有更新版本'
                ))
            else:
                checks.append(_check(
                    'version_hash', '当前版本文件哈希', 'fail',
                    '包内文件哈希与平台当前及历史版本均不一致'
                ))
    elif not expected_hash and not package_hash:
        checks.append(_check(
            'version_hash', '当前版本文件哈希', 'warn',
            '双方都没有文件哈希，无法比对'
        ))
    else:
        checks.append(_check(
            'version_hash', '当前版本文件哈希', 'warn',
            '有一方缺少文件哈希，无法比对'
        ))

    package_certificates = manifest.get('certificates') or []
    current_certificates = [
        item for item in package_certificates
        if isinstance(item, dict) and item.get('is_current')
    ] or package_certificates
    if current_certificates:
        cert_errors = []
        for item in current_certificates[:5]:
            cert_id = item.get('certificate_id')
            certificate = Certificate.query.filter_by(
                certificate_id=cert_id
            ).first() if cert_id else None
            if not certificate:
                cert_errors.append(f'平台未找到证书 {cert_id or "（缺失）"}')
                continue
            expected = certificate.file_hash
            provided = item.get('file_hash')
            if expected and provided and expected.lower() != str(provided).lower():
                cert_errors.append(f'证书 {cert_id} 的文件哈希不一致')
        if cert_errors:
            checks.append(_check(
                'certificate', '存证证书匹配', 'fail', '；'.join(cert_errors[:3])
            ))
        else:
            checks.append(_check(
                'certificate', '存证证书匹配', 'pass',
                f'包内 {len(current_certificates)} 份证书与平台登记一致'
            ))
    elif asset.certificate_id:
        checks.append(_check(
            'certificate', '存证证书匹配', 'warn',
            '证据包未包含证书，平台已有证书记录'
        ))
    else:
        checks.append(_check(
            'certificate', '存证证书匹配', 'warn',
            '平台与证据包均没有证书'
        ))

    registry_ok = not any(item['status'] == 'fail' for item in checks)
    return checks, asset, registry_ok


def verify_evidence_package(zip_path):
    """核验证据包并返回结构化结果。

    Raises:
        ValueError: ZIP 结构/清单不可解析等无法继续核验的问题。
    """
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError) as exc:
        raise ValueError('不是有效的 ZIP 文件') from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ValueError('证据包文件数量过多')
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError('证据包解压后体积超过限制')

        names = set()
        for info in infos:
            safe = _normalize_name(info.filename)
            if not safe or info.filename != safe:
                raise ValueError('证据包包含非法路径')
            if info.is_dir():
                continue
            names.add(safe)

        if 'manifest.json' not in names:
            raise ValueError('证据包缺少 manifest.json')
        if 'SHA256SUMS' not in names:
            raise ValueError('证据包缺少 SHA256SUMS')

        try:
            manifest_bytes = _read_entry(
                archive, 'manifest.json', limit=MAX_JSON_BYTES
            )
            manifest = json.loads(manifest_bytes.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError('manifest.json 无法解析') from exc
        if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
            raise ValueError('manifest.json schema 不受支持')

        asset_info = manifest.get('asset')
        if not isinstance(asset_info, dict) or not asset_info.get('asset_code'):
            raise ValueError('manifest.json 缺少资产编码')

        checks = [
            _check('zip', 'ZIP 结构安全', 'pass', f'{len(names)} 个文件，路径与体积正常'),
            _check('manifest', '清单可解析', 'pass', f'格式 {SCHEMA}'),
        ]

        checksums_ok, checksum_detail, _ = _verify_checksums(archive, names)
        checks.append(_check(
            'checksums', 'SHA-256 校验', 'pass' if checksums_ok else 'fail',
            checksum_detail
        ))

        files_ok, files_detail = _verify_manifest_files(archive, manifest, names)
        checks.append(_check(
            'files', '文件完整性', 'pass' if files_ok else 'fail',
            files_detail
        ))

        registry_checks, asset, registry_ok = _registry_checks(manifest)
        checks.extend(registry_checks)

        integrity_ok = checksums_ok and files_ok
        verified = integrity_ok and registry_ok
        if not integrity_ok:
            label = '证据包完整性校验失败'
        elif not registry_ok:
            label = '包内记录与平台登记不一致'
        else:
            label = '证据包核验通过'

        warnings = []
        chain = manifest.get('chain') or {}
        if chain.get('simulated'):
            warnings.append('证据包使用本地模拟存证，交易哈希不能用于链上复核。')
        policy = manifest.get('binary_policy') or {}
        if policy.get('omitted'):
            warnings.append(
                policy.get('omitted_reason') or '证据包未包含二进制文件。'
            )
        if any(item['key'] == 'version_hash' and item['status'] == 'warn'
               for item in checks):
            warnings.append('证据包对应历史版本或缺少文件哈希，请结合版本记录判断。')
        if asset is not None and asset.status != 'published':
            warnings.append(
                f'平台资产当前状态为 {asset.status}，不是已发布状态。'
            )
        warnings.append(
            'SHA-256 只能证明包内文件与清单一致，不能防止有人重做整套包；'
            '平台登记匹配才表示内容与平台台账一致。'
        )

        return {
            'verified': verified,
            'label': label,
            'integrity_ok': integrity_ok,
            'registry_ok': registry_ok,
            'package': {
                'schema': manifest.get('schema'),
                'generated_at': manifest.get('generated_at'),
                'generated_by': manifest.get('generated_by'),
                'asset_code': asset_info.get('asset_code'),
                'asset_title': asset_info.get('title'),
            },
            'registry': {
                'asset_found': asset is not None,
                'asset_id': asset.id if asset else None,
                'status': asset.status if asset else None,
                'watermark_id': asset.watermark_id if asset else None,
                'certificate_id': asset.certificate_id if asset else None,
            } if asset else {'asset_found': False},
            'checks': checks,
            'warnings': warnings,
        }
