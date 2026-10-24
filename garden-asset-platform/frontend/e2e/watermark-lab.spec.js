import { test, expect } from '@playwright/test'

async function loginAsUser(page) {
  await page.goto('/login')
  await page.getByPlaceholder('请输入用户名').fill('user1')
  await page.getByPlaceholder('请输入密码').fill('123456')
  await page.locator('.login-btn').click()
  await page.waitForURL('**/assets', { timeout: 15000 })
}

test.describe('水印鲁棒性实验室', () => {
  // 真实嵌入与多项攻击在低配/并发环境下可能超过默认 30s
  test.setTimeout(90000)

  test('上传图片后真实执行攻击并返回指标', async ({ page }) => {
    await loginAsUser(page)
    await page.goto('/watermark-lab')

    await expect(page.getByRole('heading', { name: '水印鲁棒性实验室' })).toBeVisible()
    await expect(page.getByText('8 项可复现攻击')).toBeVisible()

    // 在浏览器内生成一张包含平滑渐变与硬边缘的图片，避免仓库内放二进制样例
    const uploaded = await page.evaluate(async () => {
      const canvas = document.createElement('canvas')
      canvas.width = 640
      canvas.height = 480
      const ctx = canvas.getContext('2d')
      const gradient = ctx.createLinearGradient(0, 0, 640, 480)
      gradient.addColorStop(0, '#dce8df')
      gradient.addColorStop(1, '#7ea48f')
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, 640, 480)
      ctx.fillStyle = '#3d5f50'
      ctx.fillRect(120, 140, 160, 220)
      ctx.beginPath()
      ctx.arc(430, 250, 120, 0, Math.PI * 2)
      ctx.fillStyle = '#b45f3f'
      ctx.fill()

      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
      const file = new File([blob], 'lab-e2e.png', { type: 'image/png' })
      const input = document.querySelector('.lab-upload input[type=file]')
      if (!input) return false
      const transfer = new DataTransfer()
      transfer.items.add(file)
      input.files = transfer.files
      input.dispatchEvent(new Event('change', { bubbles: true }))
      return true
    })
    expect(uploaded).toBe(true)

    await expect(page.locator('.sample-preview img')).toBeVisible()
    await page.getByRole('button', { name: '开始鲁棒性实验' }).click()

    await expect(page.locator('.summary-strip')).toBeVisible({ timeout: 70000 })
    await expect(page.locator('.summary-strip')).toContainText('LAB-IMG-')
    await expect(page.locator('.attack-row')).toHaveCount(8)
    await expect(page.locator('.attack-row.recovered').first()).toBeVisible()
    await expect(page.locator('.nc-value').first()).toHaveText(/^\d+\.\d{4}$/)

    // 提取出的水印缩略图来自真实结果，使用 data URI 渲染
    const previews = page.locator('.wm-grid img')
    await expect(previews.first()).toBeVisible()
    await expect(previews.first()).toHaveAttribute('src', /^data:image\/png;base64,/)

    // 实验报告可导出，文件名带本次真实水印 ID
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '下载实验报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/^watermark-lab-LAB-IMG-\d{14}-[0-9A-F]{4}\.md$/)
  })
})
