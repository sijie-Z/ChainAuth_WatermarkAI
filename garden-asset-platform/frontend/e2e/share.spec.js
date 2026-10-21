import { test, expect } from '@playwright/test'

const API = 'http://127.0.0.1:5000/api'

async function adminHeaders(request) {
  const response = await request.post(`${API}/login`, {
    data: { username: 'admin', password: 'admin123' }
  })
  const body = await response.json()
  return { Authorization: `Bearer ${body.data.access_token}` }
}

test.describe('公开分享核验', () => {
  test('访问码校验通过后展示资产与证据链', async ({ page, request }) => {
    const headers = await adminHeaders(request)

    const assetsResponse = await request.get(`${API}/assets?per_page=100`, { headers })
    const assets = (await assetsResponse.json()).data.items
    const asset = assets.find(item => item.chain_status === 'confirmed') || assets[0]
    expect(asset).toBeTruthy()

    const shareResponse = await request.post(
      `${API}/assets/${asset.id}/shares`,
      {
        headers,
        data: {
          expires_in_days: 1,
          access_code: 'E2E2026',
          allow_download: false
        }
      }
    )
    expect(shareResponse.ok()).toBeTruthy()
    const share = (await shareResponse.json()).data

    await page.goto(`/share/${share.token}`)
    await expect(page.getByText('该分享需要访问码')).toBeVisible()

    await page.getByPlaceholder('访问码').fill('E2E2026')
    await page.getByRole('button', { name: '查看分享' }).click()

    await expect(page.locator('.share-title')).toContainText(asset.title)
    await expect(page.getByRole('heading', { name: '溯源证据链' })).toBeVisible()
    await expect(page.locator('.summary-title')).toBeVisible()
    await expect(page.getByText('仅可在线查看')).toBeVisible()

    // 清理临时分享链接
    await request.delete(`${API}/shares/${share.id}`, { headers })
  })
})
