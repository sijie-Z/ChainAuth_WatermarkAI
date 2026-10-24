/**
 * 生成文档用截图与演示视频。
 *
 * 用法：
 *   node scripts/capture-media.mjs screenshots
 *   node scripts/capture-media.mjs video
 *
 * 需要后端 :5000 与前端 :5173 已启动；演示库需包含 ZZY-IMG-20261021-D16。
 * 截图输出到 docs/assets/screenshots，视频输出到 docs/assets/video。
 */
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(scriptDir, '..', '..')
const worktreeRoot = path.resolve(repoRoot, '..')
const baseURL = process.env.DEMO_BASE_URL || 'http://127.0.0.1:5173'
const apiBase = process.env.DEMO_API_URL || 'http://127.0.0.1:5000/api'
const photoPath = process.env.DEMO_PHOTO
  || path.join(worktreeRoot, '.scratch', 'demo', 'photos', 'CLT-01.jpg')
const screenshotDir = path.join(repoRoot, 'docs', 'assets', 'screenshots')
const videoDir = path.join(repoRoot, 'docs', 'assets', 'video')
const scratchDir = path.join(worktreeRoot, '.scratch', 'demo-media')
const ffmpeg = process.env.FFMPEG_PATH || 'ffmpeg'

const mode = process.argv[2] || 'screenshots'

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true })
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function apiLogin(username, password) {
  const response = await fetch(`${apiBase}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const body = await response.json()
  if (!response.ok || body.code !== 200) {
    throw new Error(`登录失败: ${body.message || response.status}`)
  }
  return body.data
}

async function findPublishedAsset(token, assetCode) {
  const response = await fetch(`${apiBase}/assets?per_page=100&status=published`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const body = await response.json()
  const items = body.data?.items || []
  const asset = items.find(item => item.asset_code === assetCode)
  if (!asset) throw new Error(`未找到演示资产 ${assetCode}`)
  return asset
}

async function createShare(token, assetId) {
  const response = await fetch(`${apiBase}/assets/${assetId}/shares`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      expires_in_days: 1,
      access_code: 'GARDEN2026',
      allow_download: true
    })
  })
  const body = await response.json()
  if (!body.data?.token) throw new Error(body.message || '创建分享失败')
  return body.data
}

async function deleteShare(token, shareId) {
  await fetch(`${apiBase}/shares/${shareId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` }
  })
}

async function downloadEvidencePackage(token, assetId, target) {
  const response = await fetch(`${apiBase}/assets/${assetId}/evidence-package`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!response.ok) throw new Error(`证据包导出失败: ${response.status}`)
  const buffer = Buffer.from(await response.arrayBuffer())
  fs.writeFileSync(target, buffer)
  return target
}

async function loginPage(page, username, password, expected) {
  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => localStorage.clear())
  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.locator('.login-btn').click()
  await page.waitForURL(expected, { timeout: 20000 })
}

async function setCaption(page, text) {
  await page.evaluate(({ text }) => {
    let element = document.getElementById('demo-caption')
    if (!element) {
      element = document.createElement('div')
      element.id = 'demo-caption'
      document.body.appendChild(element)
    }
    element.textContent = text
    element.style.cssText = [
      'position:fixed',
      'left:0',
      'right:0',
      'bottom:0',
      'z-index:2147483647',
      'padding:14px 26px',
      'background:rgba(15,26,21,.86)',
      'color:#fff',
      'font:500 18px/1.5 "Microsoft YaHei","PingFang SC",sans-serif',
      'letter-spacing:.02em',
      'border-top:1px solid rgba(255,255,255,.16)',
      'box-shadow:0 -8px 30px rgba(0,0,0,.18)',
      'pointer-events:none'
    ].join(';')
  }, { text })
}

async function pulse(page, locator) {
  try {
    await locator.scrollIntoViewIfNeeded()
    const box = await locator.boundingBox()
    if (!box) return
    await page.evaluate(({ x, y }) => {
      const dot = document.createElement('div')
      dot.style.cssText = [
        'position:fixed',
        `left:${x}px`,
        `top:${y}px`,
        'width:26px',
        'height:26px',
        'margin:-13px 0 0 -13px',
        'border-radius:50%',
        'background:rgba(255,196,0,.92)',
        'box-shadow:0 0 0 9px rgba(255,196,0,.28)',
        'z-index:2147483646',
        'pointer-events:none',
        'transition:transform .55s ease,opacity .55s ease'
      ].join(';')
      document.body.appendChild(dot)
      requestAnimationFrame(() => {
        dot.style.transform = 'scale(1.9)'
        dot.style.opacity = '0'
      })
      setTimeout(() => dot.remove(), 650)
    }, { x: box.x + box.width / 2, y: box.y + box.height / 2 })
    await sleep(420)
  } catch {
    // 动画不是关键路径，失败时直接继续点击
  }
}

async function clickWithPulse(page, locator) {
  await pulse(page, locator)
  await locator.click()
}

async function gotoWithCaption(page, url, caption) {
  await page.goto(url, { waitUntil: 'domcontentloaded' })
  await setCaption(page, caption)
}

async function shot(page, name, { fullPage = false, delay = 500 } = {}) {
  if (fullPage) {
    await page.evaluate(() => window.scrollTo(0, 0))
    await sleep(350)
  }
  await sleep(delay)
  const target = path.join(screenshotDir, `${name}.png`)
  await page.screenshot({ path: target, fullPage })
  console.log(`  截图 ${name}.png (${Math.round(fs.statSync(target).size / 1024)} KB)`)
}

async function captureScreenshots() {
  ensureDir(screenshotDir)
  ensureDir(scratchDir)
  const admin = await apiLogin('admin', 'admin123')
  const asset = await findPublishedAsset(admin.access_token, 'ZZY-IMG-20261021-D16')
  console.log(`演示资产：${asset.title} / ${asset.asset_code}`)

  const browser = await chromium.launch()
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN'
  })
  const page = await context.newPage()

  console.log('1/14 首页')
  await page.goto(`${baseURL}/home`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { level: 1 }).waitFor()
  await shot(page, '01-home', { delay: 1200 })

  console.log('2/14 资产档案')
  await loginPage(page, 'user1', '123456', /\/assets/)
  await page.goto(`${baseURL}/assets`, { waitUntil: 'domcontentloaded' })
  await page.locator('.asset-card:not(.asset-card-skeleton)').first().waitFor({ timeout: 20000 })
  await shot(page, '02-asset-archive', { delay: 900 })

  console.log('3/14 资产详情')
  await page.goto(`${baseURL}/assets/${asset.id}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.sheet-title').first().waitFor({ timeout: 20000 })
  await page.locator('.asset-photo img').first().waitFor({ timeout: 20000 })
  await shot(page, '03-asset-detail', { delay: 900 })

  console.log('4/14 证据链')
  await page.getByRole('tab', { name: '证据链' }).click()
  await page.locator('.evidence-chain .timeline-item').first().waitFor({ timeout: 20000 })
  await page.evaluate(() => {
    const element = document.querySelector('.evidence-chain')
    if (element) {
      window.scrollTo({
        top: element.getBoundingClientRect().top + window.scrollY - 90,
        behavior: 'instant'
      })
    }
  })
  await shot(page, '04-evidence-chain', { delay: 800 })

  console.log('5/14 存证证书')
  await page.goto(`${baseURL}/certificate/${asset.certificate_id}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.cert-qr img').waitFor({ timeout: 20000 })
  await shot(page, '05-certificate', { fullPage: true, delay: 1000 })

  console.log('6/14 水印实验室')
  await page.goto(`${baseURL}/watermark-lab`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: '水印鲁棒性实验室' }).waitFor()
  await page.locator('.lab-upload input[type=file]').setInputFiles(photoPath)
  await page.locator('.sample-preview img').waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: '开始鲁棒性实验' }).click()
  await page.locator('.summary-strip').waitFor({ timeout: 90000 })
  await page.locator('.attack-row').first().waitFor({ timeout: 20000 })
  await page.locator('.attack-row').nth(7).waitFor({ timeout: 20000 })
  await shot(page, '06-watermark-lab', { fullPage: true, delay: 1000 })

  console.log('7/14 溯源结果')
  await page.goto(`${baseURL}/trace`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('tab', { name: '水印ID溯源' }).click()
  await page.locator('.watermark-input input').fill(asset.watermark_id)
  await page.getByRole('button', { name: '开始溯源' }).click()
  await page.locator('.result-card').waitFor({ timeout: 30000 })
  await shot(page, '07-trace-result', { fullPage: true, delay: 900 })

  console.log('8/14 管理仪表盘')
  await loginPage(page, 'admin', 'admin123', /\/admin/)
  await page.goto(`${baseURL}/admin`, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 2, null, { timeout: 30000 })
  await shot(page, '08-admin-dashboard', { delay: 1200 })

  console.log('9/14 授权使用报表')
  await page.goto(`${baseURL}/admin/license/usage`, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 1, null, { timeout: 30000 })
  await shot(page, '09-license-usage', { delay: 1000 })

  console.log('10/14 任务队列')
  await page.goto(`${baseURL}/admin/tasks`, { waitUntil: 'domcontentloaded' })
  await page.locator('.health-strip').waitFor({ timeout: 30000 })
  await page.locator('.health-strip').screenshot({
    path: path.join(screenshotDir, '10-task-health.png')
  })
  await page.locator('.filter-card .el-select').first().click()
  await page.getByRole('option', { name: '已完成' }).click()
  await page.getByRole('button', { name: '查询' }).click()
  await page.waitForTimeout(1200)
  await page.locator('.table-card .el-table__row').first().waitFor({ timeout: 20000 })
  await page.locator('.table-card').screenshot({
    path: path.join(screenshotDir, '10-task-queue.png')
  })
  console.log('  截图 10-task-health.png / 10-task-queue.png')

  console.log('11/14 审计日志完整性')
  await page.goto(`${baseURL}/admin/logs`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '校验日志完整性' }).click()
  await page.locator('.integrity-card.ok').waitFor({ timeout: 30000 })
  await shot(page, '11-audit-integrity', { delay: 800 })

  console.log('12/14 公开分享核验')
  const share = await createShare(admin.access_token, asset.id)
  await page.goto(`${baseURL}/share/${share.token}`, { waitUntil: 'domcontentloaded' })
  await page.getByPlaceholder('访问码').fill('GARDEN2026')
  await page.getByRole('button', { name: '查看分享' }).click()
  await page.locator('.share-title').waitFor({ timeout: 20000 })
  await shot(page, '12-public-share', { delay: 900 })
  await deleteShare(admin.access_token, share.id)

  console.log('13/14 证据包公开核验')
  const evidenceZip = path.join(scratchDir, 'evidence-package.zip')
  await downloadEvidencePackage(admin.access_token, asset.id, evidenceZip)
  await page.goto(`${baseURL}/verify-package`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: '证据包核验' }).waitFor()
  await page.setInputFiles('.verify-upload input[type=file]', evidenceZip)
  await page.locator('.file-summary').waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: '开始核验' }).click()
  await page.getByRole('heading', { name: '证据包核验通过' }).waitFor({ timeout: 30000 })
  await shot(page, '13-evidence-verify', { fullPage: true, delay: 1000 })

  await browser.close()
  console.log(`截图完成：${screenshotDir}`)
}

async function captureVideo() {
  ensureDir(videoDir)
  ensureDir(scratchDir)
  const rawDir = path.join(scratchDir, 'raw')
  ensureDir(rawDir)
  const admin = await apiLogin('admin', 'admin123')
  const asset = await findPublishedAsset(admin.access_token, 'ZZY-IMG-20261021-D16')
  const share = await createShare(admin.access_token, asset.id)
  const evidenceZip = path.join(scratchDir, 'evidence-package-video.zip')
  await downloadEvidencePackage(admin.access_token, asset.id, evidenceZip)

  const browser = await chromium.launch()
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    locale: 'zh-CN',
    recordVideo: {
      dir: rawDir,
      size: { width: 1280, height: 720 }
    }
  })
  const page = await context.newPage()
  const video = page.video()

  await gotoWithCaption(page, `${baseURL}/home`, '苏州园林数字资产平台 · 水印、存证、授权与溯源的完整演示')
  await sleep(2600)
  await setCaption(page, '园林影像、矢量图纸与三维资产的权属档案')
  await page.evaluate(() => window.scrollTo({ top: 560, behavior: 'smooth' }))
  await sleep(1800)
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
  await sleep(800)

  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await setCaption(page, '普通用户登录，进入资产档案')
  await pulse(page, page.getByPlaceholder('请输入用户名'))
  await page.getByPlaceholder('请输入用户名').fill('user1')
  await pulse(page, page.getByPlaceholder('请输入密码'))
  await page.getByPlaceholder('请输入密码').fill('123456')
  await clickWithPulse(page, page.locator('.login-btn'))
  await page.waitForURL(/\/assets/, { timeout: 20000 })
  await sleep(1200)

  await setCaption(page, '资产档案：按园林、类型、标签与上传时间检索')
  await page.locator('.asset-card:not(.asset-card-skeleton)').first().waitFor({ timeout: 20000 })
  await page.getByPlaceholder('搜索标题、编码或描述...').fill('拙政园')
  await page.getByRole('button', { name: '搜索' }).click().catch(async () => {
    await page.keyboard.press('Enter')
  })
  await sleep(1400)
  await page.getByPlaceholder('搜索标题、编码或描述...').fill('')
  await page.keyboard.press('Enter')
  await sleep(1000)

  await setCaption(page, '打开拙政园影像：水印 ID、存证哈希与证书编号集中展示')
  await page.goto(`${baseURL}/assets/${asset.id}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.asset-photo img').first().waitFor({ timeout: 20000 })
  await setCaption(page, '所有者与授权用户可在线预览，预览不消耗下载次数')
  await sleep(2000)
  await setCaption(page, '证据链：上传 → 水印 → 存证 → 证书 → 发布 → 授权 → 下载')
  await clickWithPulse(page, page.getByRole('tab', { name: '证据链' }))
  await page.locator('.evidence-chain .timeline-item').first().waitFor({ timeout: 20000 })
  await page.evaluate(() => {
    const element = document.querySelector('.evidence-chain')
    if (element) {
      window.scrollTo({
        top: element.getBoundingClientRect().top + window.scrollY - 90,
        behavior: 'smooth'
      })
    }
  })
  await sleep(2600)

  await setCaption(page, '存证证书按文件版本签发，可扫码核验')
  await page.goto(`${baseURL}/certificate/${asset.certificate_id}`, { waitUntil: 'domcontentloaded' })
  await page.locator('.cert-qr img').waitFor({ timeout: 20000 })
  await sleep(2400)

  await setCaption(page, '溯源查询：输入水印 ID，即可定位资产与链上记录')
  await page.goto(`${baseURL}/trace`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('tab', { name: '水印ID溯源' }).click()
  await pulse(page, page.locator('.watermark-input input'))
  await page.locator('.watermark-input input').fill(asset.watermark_id)
  await clickWithPulse(page, page.getByRole('button', { name: '开始溯源' }))
  await page.locator('.result-card').waitFor({ timeout: 30000 })
  await sleep(2600)

  await setCaption(page, '水印实验室：对上传图片真实执行 8 项攻击')
  await page.goto(`${baseURL}/watermark-lab`, { waitUntil: 'domcontentloaded' })
  await page.locator('.lab-upload input[type=file]').setInputFiles(photoPath)
  await page.locator('.sample-preview img').waitFor({ timeout: 20000 })
  await sleep(1000)
  await setCaption(page, '真实嵌入后计算 PSNR、NC、水印 ID 恢复情况与每项耗时')
  await clickWithPulse(page, page.getByRole('button', { name: '开始鲁棒性实验' }))
  await page.locator('.summary-strip').waitFor({ timeout: 90000 })
  await page.locator('.attack-row').nth(7).waitFor({ timeout: 20000 })
  await page.locator('.summary-strip').scrollIntoViewIfNeeded()
  await sleep(2200)
  await setCaption(page, '结果来自本次计算；JPEG 50 或组合攻击失败会如实标注')
  await page.evaluate(() => window.scrollBy({ top: 420, behavior: 'smooth' }))
  await sleep(2200)

  await setCaption(page, '管理后台：真实统计、图表与系统能力状态')
  await loginPage(page, 'admin', 'admin123', /\/admin/)
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 2, null, { timeout: 30000 })
  await sleep(2400)

  await setCaption(page, '授权使用报表：配额消耗、超范围拒绝与版本待重审')
  await page.goto(`${baseURL}/admin/license/usage`, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => document.querySelectorAll('canvas').length >= 1, null, { timeout: 30000 })
  await sleep(2400)

  await setCaption(page, '任务队列：worker 心跳、积压、超时与失败重试')
  await page.goto(`${baseURL}/admin/tasks`, { waitUntil: 'domcontentloaded' })
  await page.locator('.health-strip').waitFor({ timeout: 30000 })
  await sleep(2200)

  await setCaption(page, '操作日志写入服务端 HMAC，可一键校验是否被篡改')
  await page.goto(`${baseURL}/admin/logs`, { waitUntil: 'domcontentloaded' })
  await clickWithPulse(page, page.getByRole('button', { name: '校验日志完整性' }))
  await page.locator('.integrity-card.ok').waitFor({ timeout: 30000 })
  await sleep(2200)

  await setCaption(page, '公开分享核验：免登录查看资产与完整证据链')
  await page.goto(`${baseURL}/share/${share.token}`, { waitUntil: 'domcontentloaded' })
  await page.getByPlaceholder('访问码').fill('GARDEN2026')
  await clickWithPulse(page, page.getByRole('button', { name: '查看分享' }))
  await page.locator('.share-title').waitFor({ timeout: 20000 })
  await sleep(2400)

  await setCaption(page, '证据包公开核验：完整性与平台登记分别判定')
  await page.goto(`${baseURL}/verify-package`, { waitUntil: 'domcontentloaded' })
  await page.setInputFiles('.verify-upload input[type=file]', evidenceZip)
  await page.locator('.file-summary').waitFor({ timeout: 20000 })
  await clickWithPulse(page, page.getByRole('button', { name: '开始核验' }))
  await page.getByRole('heading', { name: '证据包核验通过' }).waitFor({ timeout: 30000 })
  await sleep(2600)

  await gotoWithCaption(page, `${baseURL}/home`, '水印 · 存证 · 授权 · 溯源 —— 苏州园林数字资产平台')
  await sleep(3200)

  await context.close()
  const rawPath = await video.path()
  await browser.close()
  await deleteShare(admin.access_token, share.id)

  const mp4 = path.join(videoDir, 'suzhou-garden-demo.mp4')
  const poster = path.join(videoDir, 'demo-poster.jpg')
  const gif = path.join(videoDir, 'demo-preview.gif')
  console.log('转码 MP4…')
  execFileSync(ffmpeg, [
    '-y', '-i', rawPath,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an',
    mp4
  ], { stdio: 'inherit' })
  console.log('生成封面与 GIF 预览…')
  execFileSync(ffmpeg, [
    '-y', '-ss', '00:00:04', '-i', mp4,
    '-frames:v', '1', '-q:v', '2', poster
  ], { stdio: 'inherit' })
  execFileSync(ffmpeg, [
    '-y', '-ss', '00:00:30', '-t', '12', '-i', mp4,
    '-vf', 'fps=8,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=160[p];[s1][p]paletteuse=dither=bayer',
    '-loop', '0', gif
  ], { stdio: 'inherit' })

  console.log(`视频完成：${mp4}`)
  console.log(`封面：${poster}`)
  console.log(`GIF：${gif}`)
}

if (mode === 'video') {
  captureVideo().catch(error => {
    console.error(error)
    process.exit(1)
  })
} else {
  captureScreenshots().catch(error => {
    console.error(error)
    process.exit(1)
  })
}
