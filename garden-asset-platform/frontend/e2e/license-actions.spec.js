import { test, expect } from '@playwright/test'

test.describe('授权履约操作', () => {
  test('已生效授权提供续期与撤销入口', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('admin')
    await page.getByPlaceholder('请输入密码').fill('admin123')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/admin', { timeout: 15000 })

    await page.goto('/admin/license/approved')
    await expect(page.getByRole('heading', { name: '已审批申请' })).toBeVisible()

    const activeRow = page.locator('.el-table__row').filter({ hasText: '生效' }).first()
    await expect(activeRow).toBeVisible()
    await activeRow.getByRole('button', { name: '续期' }).click()
    await expect(page.getByRole('dialog', { name: '授权续期' })).toBeVisible()
    await expect(page.getByPlaceholder('选择新的到期日期')).toBeVisible()
    await page.getByRole('dialog', { name: '授权续期' }).getByRole('button', { name: '取消' }).click()

    await activeRow.getByRole('button', { name: '撤销' }).click()
    await expect(page.getByRole('dialog', { name: '撤销授权' })).toBeVisible()
    await expect(page.getByPlaceholder('撤销原因（可选）')).toBeVisible()
    await page.getByRole('dialog', { name: '撤销授权' }).getByRole('button', { name: '取消' }).click()
  })
})
