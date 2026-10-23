import { test, expect } from '@playwright/test'

const API = 'http://127.0.0.1:5000/api'

test.describe('用户合集', () => {
  test('可以创建合集并进入详情', async ({ page, request }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    const token = await page.evaluate(() => localStorage.getItem('token'))
    const created = await request.post(`${API}/collections`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: `E2E 合集 ${Date.now()}`,
        description: 'Playwright 创建',
        is_public: false
      }
    })
    expect(created.ok()).toBeTruthy()
    const collection = (await created.json()).data

    await page.goto('/collections')
    await expect(page.getByRole('heading', { name: '我的合集' })).toBeVisible()
    const card = page.locator('.collection-card').filter({ hasText: collection.name })
    await expect(card).toBeVisible()
    // 点击标题，避免落在卡片右侧的操作按钮上
    await card.locator('.collection-name').click()
    await expect(page).toHaveURL(new RegExp(`/collections/${collection.id}$`))

    await expect(page.locator('.collection-title')).toHaveText(collection.name)
    await expect(page.getByText('合集里还没有资产')).toBeVisible()

    // 清理测试数据
    await request.delete(`${API}/collections/${collection.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
  })
})
