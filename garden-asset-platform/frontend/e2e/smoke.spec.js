import { test, expect } from '@playwright/test'

test.describe('公开页面', () => {
  test('首页、工序、园林与技术台账正常渲染', async ({ page }) => {
    await page.goto('/home')

    await expect(page.getByRole('heading', { level: 1 })).toContainText('让每一件园林资产')
    await expect(page.getByText('一件资产的四道工序')).toBeVisible()
    await expect(page.getByText('四类保护能力')).toBeVisible()
    await expect(page.getByText('园林档案')).toBeVisible()
    await expect(page.getByText('技术台账')).toBeVisible()
    await expect(page.getByRole('link', { name: '资产档案' }).first()).toBeVisible()
  })

  test('移动端导航可以打开', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/home')

    await page.locator('.mobile-nav-toggle').click()
    await expect(page.locator('.mobile-nav')).toBeVisible()
    await expect(page.locator('.mobile-nav').getByRole('link', { name: '资产档案' })).toBeVisible()
  })

  test('溯源页展示两种查询方式', async ({ page }) => {
    await page.goto('/trace')

    await expect(page.getByRole('heading', { name: '溯源查询' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '上传图片溯源' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '水印ID溯源' })).toBeVisible()
  })

  test('使用指南展示流程、角色与功能入口', async ({ page }) => {
    await page.goto('/guide')

    await expect(page.getByRole('heading', { level: 1 })).toContainText('从一件园林影像')
    await expect(page.getByRole('heading', { name: '角色与演示账号' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '一条完整流程' })).toBeVisible()
    await expect(page.getByRole('link', { name: '进入资产档案' })).toBeVisible()
  })
})

test.describe('登录与业务流程', () => {
  test('管理员登录后进入后台并打开资产管理', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('admin123')
    await page.locator('.login-btn').click()

    await page.waitForURL('**/admin', { timeout: 15000 })
    await expect(page.getByText('仪表盘').first()).toBeVisible()

    await page.goto('/admin/assets')
    await expect(page.getByRole('heading', { name: '资产管理' })).toBeVisible()
    await expect(page.getByPlaceholder('搜索标题/编码')).toBeVisible()
  })

  test('普通用户登录后可以浏览已发布资产', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()

    await page.waitForURL('**/assets', { timeout: 15000 })
    await expect(page.getByRole('heading', { name: '资产中心' })).toBeVisible()

    // 后端已初始化并灌入已发布资产
    await expect(page.locator('.asset-card, .asset-info-cell').first()).toBeVisible({ timeout: 15000 })
  })

  test('导航切换为无刷新 SPA 跳转且内容及时出现', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    await page.goto('/home')
    await page.evaluate(() => { window.__spaMarker = 'alive' })

    const started = Date.now()
    await page.getByRole('link', { name: '资产档案' }).first().click()

    await expect(page).toHaveURL(/\/assets$/)
    await expect(page.getByRole('heading', { name: '资产中心' })).toBeVisible({ timeout: 8000 })
    expect(Date.now() - started).toBeLessThan(8000)

    // 页面没有整页刷新（内存标记仍在），且切换期间使用档案纸色背景而不是白屏
    expect(await page.evaluate(() => window.__spaMarker)).toBe('alive')
    const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
    expect(background).not.toBe('rgb(255, 255, 255)')
  })

  test('个人资产、收藏与申请记录入口可用', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    await page.goto('/my-assets')
    await expect(page.getByRole('heading', { name: '我的资产' })).toBeVisible()

    await page.goto('/favorites')
    await expect(page.getByRole('heading', { name: '我的收藏' })).toBeVisible()

    await page.goto('/license/my')
    const applicationTab = page.locator('.header-filters').getByText('申请记录', { exact: true })
    await expect(applicationTab).toBeVisible()
    await applicationTab.click()
    await expect(page.locator('.card-title')).toHaveText('我的申请')
  })
})
