import { test, expect } from '@playwright/test'

const PNG_A = 'iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAU0lEQVR4nO3PQQ3AIADAQEASb2QjcCJ4XJb0FLTznj3+bOmAVw1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgf7I8Bgkm73pQAAAAASUVORK5CYII='
const PNG_B = 'iVBORw0KGgoAAAANSUhEUgAAAEAAAAAwCAIAAAAuKetIAAAAU0lEQVR4nO3PQQ3AIADAQEANmtCE6IngcVnSU9DOfe74s6UDXjWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaA1oDWgNaB9F/MBbpe8HJwAAAAASUVORK5CYII='

function uniquePng(base64) {
  return Buffer.concat([
    Buffer.from(base64, 'base64'),
    Buffer.from(`
${Date.now()}-${Math.random()}`)
  ])
}

test.describe('批量上传', () => {
  test('一次选择多个文件并生成草稿', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    await page.goto('/assets/upload')
    await expect(page.getByRole('heading', { name: '上传资产' })).toBeVisible()

    await page.locator('input[type="file"]').setInputFiles([
      { name: 'batch-a.png', mimeType: 'image/png', buffer: uniquePng(PNG_A) },
      { name: 'batch-b.png', mimeType: 'image/png', buffer: uniquePng(PNG_B) }
    ])
    await expect(page.locator('.queue-item')).toHaveCount(2)

    // 测试图很小，水印可能失败，但上传流程仍应完成；这里不额外切换水印开关
    await page.getByText('请选择园林', { exact: true }).click()
    await page.getByRole('option', { name: '拙政园' }).click()

    await page.getByRole('button', { name: /开始上传 2 个文件/ }).click()
    await expect(page.locator('.queue-item.status-done')).toHaveCount(2, { timeout: 60000 })
    await expect(page.getByText(/处理完成：成功 2 件/)).toBeVisible()

    // 清理测试资产
    await page.evaluate(async () => {
      const token = localStorage.getItem('token')
      const headers = { Authorization: `Bearer ${token}` }
      const response = await fetch('/api/assets/my?per_page=100', { headers })
      const body = await response.json()
      for (const item of body.data.items) {
        if (['batch-a', 'batch-b'].includes(item.title)) {
          await fetch(`/api/assets/${item.id}`, { method: 'DELETE', headers })
        }
      }
    })
  })

  test('刷新页面后显示未完成的大文件上传并可放弃', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    // 直接创建会话，模拟“上传中断后关闭页面”
    const created = await page.evaluate(async () => {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/assets/upload/session', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: 'resume-e2e.png',
          size: 9 * 1024 * 1024,
          asset_type: 'image',
          title: '断点续传恢复测试',
          tags: []
        })
      })
      return response.json()
    })
    expect(created.code).toBe(200)

    await page.goto('/assets/upload')
    const panel = page.locator('.resume-panel')
    await expect(panel).toBeVisible({ timeout: 15000 })
    await expect(panel.getByText('resume-e2e.png')).toBeVisible()
    await expect(panel.getByRole('button', { name: '选择文件继续' })).toBeVisible()

    await panel.getByRole('button', { name: '放弃' }).click()
    await page.locator('.el-message-box')
      .getByRole('button', { name: '放弃' })
      .click()
    await expect(panel).toBeHidden({ timeout: 15000 })

    // 服务端会话已取消
    const status = await page.evaluate(async (uploadId) => {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/assets/upload/session/${uploadId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      return response.json()
    }, created.data.upload_id)
    expect(status.data.status).toBe('cancelled')
  })
})
