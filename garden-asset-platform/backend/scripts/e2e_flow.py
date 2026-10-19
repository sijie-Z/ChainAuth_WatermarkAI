"""
端到端业务流程验证（针对本地运行的后端 127.0.0.1:5000）
覆盖：注册/登录 → 上传 → 发布审核 → 水印嵌入/提取/验证 → 上链 → 证书
      → 授权申请 → adm1/adm2 双审批 → 下载 → 溯源 → 统计
"""
import io
import sys
import time
import json
import random

import requests
from PIL import Image, ImageDraw

BASE = 'http://127.0.0.1:5000/api'


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    print(f'[{status}] {name}' + (f' — {detail}' if detail else ''))
    if not condition:
        failures.append(name)


def login(username, password):
    r = requests.post(f'{BASE}/login', json={'username': username, 'password': password}, timeout=20)
    data = r.json()
    if r.status_code != 200 or data.get('code') != 200:
        raise RuntimeError(f'login failed for {username}: {r.status_code} {data}')
    return data['data']['access_token'], data['data']['user']


def headers(token):
    return {'Authorization': f'Bearer {token}'}


failures = []

# ---------- 0. 健康检查 ----------
r = requests.get('http://127.0.0.1:5000/health', timeout=10)
check('health endpoint', r.status_code == 200 and r.json().get('status') == 'healthy', str(r.json()))

# ---------- 1. 登录种子账号 ----------
admin_token, admin_user = login('admin', 'admin123')
adm1_token, _ = login('adm1', '123456')
adm2_token, _ = login('adm2', '123456')
user1_token, user1 = login('user1', '123456')
check('seed accounts login', all([admin_token, adm1_token, adm2_token, user1_token]), f'user1={user1["username"]}')

# ---------- 2. 注册新用户并登录 ----------
suffix = str(int(time.time()))[-6:]
new_username = f'e2e_user_{suffix}'
r = requests.post(f'{BASE}/register', json={
    'username': new_username,
    'password': 'e2e_pass_123',
    'email': f'{new_username}@example.com',
    'phone': f'139{suffix.zfill(8)}'
}, timeout=20)
check('register new user', r.status_code == 200 and r.json().get('code') == 200, r.text[:200])
creator_token, creator = login(new_username, 'e2e_pass_123')
check('new user login', creator.get('role') == 'user', f'role={creator.get("role")}')

# ---------- 3. 生成测试图片并上传 ----------
img = Image.new('RGB', (512, 512))
px = img.load()
for y in range(512):
    for x in range(512):
        px[x, y] = (30 + x // 4, 80 + y // 4, 60 + (x + y) // 8)
draw = ImageDraw.Draw(img)
draw.rectangle([80, 80, 432, 432], outline=(240, 240, 235), width=6)
draw.ellipse([176, 176, 336, 336], outline=(166, 64, 47), width=8)
draw.text((150, 400), f'SUZHOU GARDEN E2E {suffix}', fill=(245, 245, 240))
for _ in range(4000):
    x = random.randrange(512)
    y = random.randrange(512)
    px[x, y] = (random.randrange(256), random.randrange(256), random.randrange(256))
buf = io.BytesIO()
img.save(buf, format='PNG')
image_bytes = buf.getvalue()

r = requests.post(f'{BASE}/assets/upload',
                  headers=headers(creator_token),
                  files={'file': (f'e2e_{suffix}.png', image_bytes, 'image/png')},
                  data={'title': f'E2E 测试资产 {suffix}', 'asset_type': 'image',
                        'garden_id': '1', 'description': '端到端验证资产',
                        'tags': json.dumps(['E2E', '测试'])},
                  timeout=30)
up = r.json()
check('asset upload', r.status_code == 200 and up.get('code') == 200, r.text[:200])
asset_id = up.get('data', {}).get('asset_id')
asset_code = up.get('data', {}).get('asset_code')
check('asset id/code returned', bool(asset_id and asset_code), f'{asset_id} / {asset_code}')

# ---------- 4. 发布 + 审核 ----------
r = requests.post(f'{BASE}/assets/{asset_id}/publish', headers=headers(creator_token), timeout=20)
check('asset submit for publish', r.status_code == 200 and r.json().get('code') == 200, r.text[:200])

r = requests.post(f'{BASE}/assets/{asset_id}/approve', headers=headers(adm1_token),
                  json={'action': 'approve'}, timeout=20)
check('asset approve by adm1', r.status_code == 200 and r.json().get('code') == 200, r.text[:200])

r = requests.get(f'{BASE}/assets/{asset_id}', headers=headers(creator_token), timeout=20)
asset = r.json().get('data', {})
check('asset published', asset.get('status') == 'published', f'status={asset.get("status")}')

# ---------- 5. 水印嵌入 / 提取 / 验证 ----------
r = requests.post(f'{BASE}/watermark/embed', headers=headers(creator_token),
                  json={'asset_id': asset_id}, timeout=120)
embed = r.json()
check('watermark embed', r.status_code == 200 and embed.get('code') == 200, r.text[:300])
watermark_id = embed.get('data', {}).get('watermark_id')
watermarked_path = embed.get('data', {}).get('watermarked_path')
psnr = embed.get('data', {}).get('psnr')
check('watermark id + psnr', bool(watermark_id) and psnr is not None,
      f'id={watermark_id} psnr={psnr}')

r = requests.post(f'{BASE}/watermark/extract', headers=headers(creator_token),
                  json={'asset_id': asset_id}, timeout=120)
extract = r.json()
check('watermark extract', r.status_code == 200 and extract.get('code') == 200, r.text[:300])
nc_value = extract.get('data', {}).get('nc_value')
check('watermark NC value', nc_value is not None, f'nc={nc_value}')

if watermark_id:
    r = requests.post(f'{BASE}/watermark/verify', json={'watermark_id': watermark_id}, timeout=20)
    verify = r.json()
    verified = verify.get('verified') is True or verify.get('data', {}).get('verified') is True
    check('watermark verify', r.status_code == 200 and verified, r.text[:300])

# ---------- 6. 区块链存证 + 证书 ----------
r = requests.post(f'{BASE}/blockchain/register', headers=headers(creator_token),
                  json={'asset_id': asset_id}, timeout=60)
chain = r.json()
check('blockchain register', r.status_code == 200 and chain.get('code') == 200, r.text[:300])
certificate_id = chain.get('data', {}).get('certificate_id')
tx_hash = chain.get('data', {}).get('tx_hash')
check('certificate id + tx hash', bool(certificate_id and tx_hash),
      f'cert={certificate_id} tx={str(tx_hash)[:16]}...')

if certificate_id:
    r = requests.get(f'{BASE}/blockchain/certificate/{certificate_id}', timeout=20)
    cert = r.json()
    check('certificate fetch', r.status_code == 200 and cert.get('code') == 200, r.text[:300])

# ---------- 7. 授权申请 + 双审批 ----------
r = requests.post(f'{BASE}/license/apply', headers=headers(user1_token), json={
    'asset_id': asset_id,
    'license_type': 'personal',
    'purpose': 'E2E 授权流程验证',
    'valid_period': '1m',
    'territory': '中国大陆'
}, timeout=20)
apply_res = r.json()
check('license apply', r.status_code == 200 and apply_res.get('code') == 200, r.text[:300])
application_id = apply_res.get('data', {}).get('id')
check('license application id', bool(application_id), f'id={application_id}')

r = requests.get(f'{BASE}/license/pending', headers=headers(adm1_token), timeout=20)
pending = r.json()
pending_items = pending.get('data', {}).get('items', pending.get('data', [])) if isinstance(pending.get('data'), dict) else pending.get('data', [])
found = any(str(item.get('id')) == str(application_id) for item in pending_items) if isinstance(pending_items, list) else False
check('license appears in pending', found, f'pending_count={len(pending_items) if isinstance(pending_items, list) else "?"}')

r = requests.post(f'{BASE}/license/approve/{application_id}', headers=headers(adm1_token),
                  json={'action': 'approve', 'comment': 'E2E adm1 通过'}, timeout=20)
check('license approve adm1', r.status_code == 200 and r.json().get('code') == 200, r.text[:200])

r = requests.post(f'{BASE}/license/approve/{application_id}', headers=headers(adm2_token),
                  json={'action': 'approve', 'comment': 'E2E adm2 通过'}, timeout=20)
check('license approve adm2', r.status_code == 200 and r.json().get('code') == 200, r.text[:200])

r = requests.get(f'{BASE}/license/my', headers=headers(user1_token), timeout=20)
my = r.json()
my_items = my.get('data', {}).get('items', []) if isinstance(my.get('data'), dict) else my.get('data', [])
approved = [item for item in my_items if str(item.get('asset_id')) == str(asset_id)]
check('license visible to user', len(approved) >= 1,
      f'status={approved[0].get("status") if approved else "none"}')

# ---------- 8. 下载 ----------
r = requests.get(f'{BASE}/assets/{asset_id}/download', headers=headers(user1_token), timeout=30)
check('asset download', r.status_code == 200 and len(r.content) > 0,
      f'{r.status_code}, {len(r.content)} bytes')
if r.status_code == 200 and r.content:
    downloaded = Image.open(io.BytesIO(r.content))
    check('downloaded asset keeps color', downloaded.mode == 'RGB', f'mode={downloaded.mode}')

# ---------- 9. 溯源 ----------
trace_source = image_bytes
if watermarked_path:
    try:
        with open(watermarked_path, 'rb') as fh:
            trace_source = fh.read()
    except OSError:
        pass

r = requests.post(f'{BASE}/watermark/trace', files={'file': ('trace.png', trace_source, 'image/png')}, timeout=120)
trace = r.json()
check('watermark trace', r.status_code == 200 and trace.get('code') == 200, r.text[:300])
if trace.get('data'):
    check('trace matched asset', str(trace['data'].get('asset_id')) == str(asset_id),
          f"asset={trace['data'].get('asset_code')} verified={trace.get('verified')}")

# ---------- 10. 公共统计 / 列表 ----------
r = requests.get(f'{BASE}/stats', timeout=20)
stats = r.json()
check('public stats', r.status_code == 200 and stats.get('code') == 200 and stats['data'].get('total_assets', 0) >= 1,
      f"assets={stats.get('data', {}).get('total_assets')}")

r = requests.get(f'{BASE}/assets', headers=headers(user1_token), params={'status': 'published'}, timeout=20)
listing = r.json()
items = listing.get('data', {}).get('items', [])
check('published asset listing', any(str(a.get('id')) == str(asset_id) for a in items), f'count={len(items)}')

print('\n================ E2E SUMMARY ================')
print(f'asset: {asset_code} (id={asset_id})')
print(f'watermark: {watermark_id}  nc={nc_value}  psnr={psnr}')
print(f'certificate: {certificate_id}  tx={tx_hash}')
print(f'license application: {application_id}')
print(f'failures: {len(failures)}')
if failures:
    print('FAILED STEPS: ' + ', '.join(failures))
    sys.exit(1)
print('ALL E2E STEPS PASSED')
