import { test, expect } from '@playwright/test'

const PNG = 'iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAU0lEQVR4nO3PQQ3AIADAQEASb2QjcCJ4XJb0FLTznj3+bOmAVw1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgf7I8Bgkm73pQAAAAASUVORK5CYII='

function uniquePng() {
  return Buffer.concat([
    Buffer.from(PNG, 'base64'),
    Buffer.from(`
${Date.now()}-${Math.random()}`)
  ])
}

test.describe('资产回收站', () => {
  test('用户删除资产后可在回收站恢复为草稿', async ({ page }) => {
    test.setTimeout(90000)
    const title = `recycle-e2e-${Date.now()}`

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    await page.goto('/assets/upload')
    await page.locator('input[type="file"]').setInputFiles([
      { name: `${title}.png`, mimeType: 'image/png', buffer: uniquePng() }
    ])
    await expect(page.locator('.queue-item')).toHaveCount(1)
    await page.getByText('请选择园林', { exact: true }).click()
    await page.getByRole('option', { name: '拙政园' }).click()
    await page.getByRole('button', { name: /开始上传 1 个文件/ }).click()
    await expect(page.locator('.queue-item.status-done')).toHaveCount(1, { timeout: 60000 })

    await page.goto('/my-assets')
    const card = page.locator('.my-card', { hasText: title })
    await expect(card).toBeVisible()
    await card.getByRole('button', { name: '删除' }).click()
    await page.locator('.el-message-box').getByRole('button', { name: '删除' }).click()
    await expect(page.getByText('资产已移入回收站，可在“回收站”中恢复')).toBeVisible()
    await expect(card).toHaveCount(0)

    await page.locator('.status-tabs').getByText('回收站', { exact: true }).click()
    const deletedCard = page.locator('.my-card', { hasText: title })
    await expect(deletedCard).toBeVisible()
    await expect(deletedCard.getByText('已删除')).toBeVisible()
    await expect(deletedCard.locator('.deleted-thumb')).toContainText('已移入回收站')

    await deletedCard.getByRole('button', { name: '恢复' }).click()
    await page.locator('.el-message-box').getByRole('button', { name: '恢复' }).click()
    await expect(page.getByText('资产已恢复为草稿，请重新水印/存证并提交发布')).toBeVisible()
    await expect(deletedCard).toHaveCount(0)

    await page.locator('.status-tabs').getByText('草稿', { exact: true }).click()
    await expect(page.locator('.my-card', { hasText: title })).toBeVisible()

    // 清理：再次移入回收站，避免污染草稿列表
    await page.evaluate(async assetTitle => {
      const token = localStorage.getItem('token')
      const headers = { Authorization: `Bearer ${token}` }
      const response = await fetch('/api/assets/my?per_page=100', { headers })
      const body = await response.json()
      for (const item of body.data.items) {
        if (item.title === assetTitle) {
          await fetch(`/api/assets/${item.id}`, { method: 'DELETE', headers })
        }
      }
    }, title)
  })
})
