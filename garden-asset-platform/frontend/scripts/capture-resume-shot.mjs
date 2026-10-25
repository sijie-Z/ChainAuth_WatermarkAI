/**
 * 生成“未完成的上传”面板截图（v1.11.0 文档用）。
 *
 * 需要本地演示环境已启动：
 *   backend  http://127.0.0.1:5000
 *   frontend http://127.0.0.1:5173
 *
 * 用法：node scripts/capture-resume-shot.mjs
 */
import { chromium } from 'playwright'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const base = (process.env.BASE_URL || 'http://127.0.0.1:5173').replace(/\/$/, '')
const output = process.env.OUT || path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../docs/assets/screenshots/17-resume-upload.png'
)

const browser = await chromium.launch()
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1
})

try {
  await page.goto(`${base}/login`)
  await page.getByPlaceholder('请输入用户名').fill('user1')
  await page.getByPlaceholder('请输入密码').fill('123456')
  await page.locator('.login-btn').click()
  await page.waitForURL('**/assets', { timeout: 15000 })

  const created = await page.evaluate(async () => {
    const token = localStorage.getItem('token')
    const headers = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
    const response = await fetch('/api/assets/upload/session', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        filename: '拙政园-荷花厅-高清扫描.png',
        size: 9 * 1024 * 1024,
        asset_type: 'image',
        title: '拙政园荷花厅高清扫描',
        description: '演示断点续传：关闭页面后重新选择同名文件即可继续',
        tags: ['古典建筑']
      })
    })
    const body = await response.json()
    if (body.code !== 200) throw new Error(body.message)
    const chunk = new Uint8Array(2 * 1024 * 1024)
    await fetch(`/api/assets/upload/session/${body.data.upload_id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/octet-stream',
        'X-Upload-Offset': '0'
      },
      body: chunk
    })
    return body.data.upload_id
  })

  await page.goto(`${base}/assets/upload`)
  await page.locator('.resume-panel').waitFor({ timeout: 15000 })
  await page.waitForTimeout(600)
  await page.screenshot({ path: output })

  await page.evaluate(async (uploadId) => {
    const token = localStorage.getItem('token')
    await fetch(`/api/assets/upload/session/${uploadId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
  }, created)
  console.log(`saved: ${output}`)
} finally {
  await browser.close()
}
