import { test, expect } from '@playwright/test'

test.describe('大文件下载', () => {
  test('授权下载先申请短时票据再由浏览器直接下载', async ({ page }) => {
    test.setTimeout(60000)

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    await page.goto('/license/my')
    await expect(page.locator('.license-table')).toBeVisible({ timeout: 15000 })

    const buttons = page.getByRole('button', { name: '下载' })
    const count = await buttons.count()
    let target = null
    for (let index = 0; index < count; index += 1) {
      if (await buttons.nth(index).isEnabled()) {
        target = buttons.nth(index)
        break
      }
    }
    expect(target, '需要至少一条生效中的授权用于下载测试').not.toBeNull()

    const ticketRequest = page.waitForRequest(
      request => request.url().includes('/download-ticket') && request.method() === 'POST'
    )
    const downloadEvent = page.waitForEvent('download', { timeout: 30000 })

    await target.click()
    await ticketRequest
    const download = await downloadEvent

    expect(download.suggestedFilename()).toMatch(/\.[a-z0-9]{2,5}$/i)
    expect(page.url()).toContain('/license/my')
  })
})
