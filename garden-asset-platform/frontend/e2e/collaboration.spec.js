import { test, expect } from '@playwright/test'

const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAE8AAAA9CAIAAACxEJA7AAAAZUlEQVR4nO3PAQ3AIADAMI4GhF3d9d4FJGVVsD3fu8YF5umATfq09Gnp09KnpU9Ln5Y+LX1a+rT0aenT0qelT0uflj4tfVr6tPRp6dPSp6VPS5+WPi19Wvq09Gnp09Kn5ZbPH8GeAXAAlnDWAAAAAElFTkSuQmCC'

function uniquePng(base64) {
  return Buffer.concat([
    Buffer.from(base64, 'base64'),
    Buffer.from(`${Date.now()}-${Math.random()}`)
  ])
}

test.describe('评论与图纸标注', () => {
  test('发表评论、回复并完成一次区域标注', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    const assetId = await page.evaluate(async (base64) => {
      const token = localStorage.getItem('token')
      const bytes = Uint8Array.from(atob(base64), char => char.charCodeAt(0))
      const form = new FormData()
      form.append('file', new File([bytes], 'collab-e2e.png', { type: 'image/png' }))
      form.append('title', 'COLLAB-E2E')
      form.append('asset_type', 'image')
      form.append('garden_id', '1')
      const response = await fetch('/api/assets/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form
      })
      const body = await response.json()
      if (body.code !== 200) throw new Error(body.message || 'upload failed')
      return body.data.asset_id
    }, uniquePng(PNG).toString('base64'))

    await page.goto(`/assets/${assetId}`)
    await expect(page.locator('.collab-tabs')).toBeVisible()

    // 评论
    await page.getByRole('tab', { name: '讨论' }).click()
    await page.locator('.comment-composer textarea').fill('这条资产的著录信息我确认过。')
    await page.getByRole('button', { name: '发表评论' }).click()
    await expect(page.locator('.comment-item')).toHaveCount(1)
    await expect(page.getByText('这条资产的著录信息我确认过。')).toBeVisible()

    await page.locator('.comment-item').first().getByRole('button', { name: '回复' }).click()
    await page.locator('.comment-composer textarea').fill('补充：拍摄于春季。')
    await page.getByRole('button', { name: '发送回复' }).click()
    await expect(page.locator('.comment-item')).toHaveCount(2)

    // 标注
    await page.getByRole('tab', { name: '标注' }).click()
    const stage = page.locator('.annotation-stage')
    await expect(stage).toBeVisible()
    await expect(stage.locator('img')).toBeVisible()
    await page.locator('.annotation-toolbar').getByRole('button', { name: '开始标注' }).click()

    const box = await stage.boundingBox()
    await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.2)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.55, { steps: 6 })
    await page.mouse.up()

    await page.getByPlaceholder('例如：斗拱缺角、需补充说明的位置').fill('E2E 标注：斗拱缺角')
    await page.getByRole('button', { name: '添加标注' }).click()

    await expect(page.locator('.annotation-entry')).toHaveCount(1, { timeout: 15000 })
    await expect(page.locator('.annotation-entry')).toContainText('E2E 标注：斗拱缺角')
    await expect(page.locator('.annotation-stage .annotation-box')).toHaveCount(1)

    await page.locator('.annotation-entry').getByRole('button', { name: '标记解决' }).click()
    await expect(page.locator('.annotation-entry')).toContainText('已解决')

    // 清理测试资产
    await page.evaluate(async (id) => {
      const token = localStorage.getItem('token')
      await fetch(`/api/assets/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
    }, assetId)
  })
})
