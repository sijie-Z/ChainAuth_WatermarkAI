import { test, expect } from '@playwright/test'

test.describe('资产证据包', () => {
  test('资产管理员可以从详情页导出 ZIP 证据包', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('admin123')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/admin', { timeout: 15000 })

    await page.goto('/assets')
    // 选择一个真实园林资产，避免演示库里用于预览测试的 PDF 草稿
    const targetCard = page.locator('.asset-card').filter({ hasText: '拙政园' }).first()
    await expect(targetCard).toBeVisible({ timeout: 15000 })
    // 点击标题而不是缩略图上的悬浮按钮，避免按钮拦截卡片点击
    await targetCard.locator('.asset-title').click()
    await page.waitForURL(/\/assets\/[0-9a-f-]{8,}/, { timeout: 15000 })

    const exportButton = page.getByRole('button', { name: '导出证据包' })
    await expect(exportButton).toBeVisible({ timeout: 15000 })

    const downloadPromise = page.waitForEvent(
      'download',
      item => item.suggestedFilename().endsWith('.zip')
    )
    await exportButton.click()
    await page.getByRole('button', { name: '生成并下载' }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/-evidence(-\d{14})?\.zip$/)
  })
})
