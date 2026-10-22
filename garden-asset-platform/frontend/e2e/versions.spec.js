import { test, expect } from '@playwright/test'

const API = 'http://127.0.0.1:5000/api'
const PNG_V1 = 'iVBORw0KGgoAAAANSUhEUgAAAEsAAAA5CAIAAADxxkF3AAAAYklEQVR4nO3PAQ3AIADAMI4LDN3G/bu4CkJKVgXbs753XG2eDtiuQ1+Hvg59Hfo69HXo69DXoa9DX4e+Dn0d+jr0dejr0Nehr0Nfh74OfR36OvR16OvQ16GvQ1+Hvg599x/+wJcBMB0j+nIAAAAASUVORK5CYII='
const PNG_V2 = 'iVBORw0KGgoAAAANSUhEUgAAAE0AAAA7CAIAAACxEJA7AAAAY0lEQVR4nO3PAQ3AIADAMI4GhF3d9d4FJGVVsD3fu8YF5umATfq09Gnp09KnpU9Ln5Y+LX1a+rT0aenT0qelT0uflj4tfVr6tPRp6dPSp6VPS5+WPi19Wvq09Gnp09Kn5ZbPH8GeAXAAlnDWAAAAAElFTkSuQmCC'

function uniquePng(base64) {
  return Buffer.concat([
    Buffer.from(base64, 'base64'),
    Buffer.from(`
${Date.now()}-${Math.random()}`)
  ])
}

test.describe('资产版本', () => {
  test('上传新版本并恢复历史版本', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    const assetId = await page.evaluate(async (base64) => {
      const token = localStorage.getItem('token')
      const bytes = Uint8Array.from(atob(base64), char => char.charCodeAt(0))
      const form = new FormData()
      form.append('file', new File([bytes], 'version-e2e.png', { type: 'image/png' }))
      form.append('title', 'VERSION-E2E')
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
    }, uniquePng(PNG_V1).toString('base64'))

    await page.goto(`/assets/${assetId}`)
    await expect(page.locator('.version-item')).toHaveCount(1)
    await expect(page.locator('.version-item .version-no')).toHaveText('v1')

    await page.getByRole('button', { name: '上传新版本' }).click()
    await page.locator('.el-dialog input[type="file"]').setInputFiles({
      name: 'version-e2e-v2.png',
      mimeType: 'image/png',
      buffer: uniquePng(PNG_V2)
    })
    await page.locator('.version-note-input textarea').fill('E2E 第二版')
    await page.getByRole('button', { name: '上传并保存' }).click()

    await expect(page.locator('.version-item')).toHaveCount(2, { timeout: 20000 })
    await expect(page.locator('.version-item.current .version-no')).toHaveText('v2')
    await expect(page.getByText('E2E 第二版')).toBeVisible()

    const v1Item = page.locator('.version-item').filter({ hasText: '初始版本' })
    await v1Item.getByRole('button', { name: '恢复为此版本' }).click()
    await page.locator('.el-message-box__btns .el-button--primary').click()

    await expect(page.locator('.version-item')).toHaveCount(3, { timeout: 20000 })
    await expect(page.locator('.version-item.current .version-no')).toHaveText('v3')
    await expect(page.getByText('恢复自 v1')).toBeVisible()

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
