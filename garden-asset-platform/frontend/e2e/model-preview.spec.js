import { test, expect } from '@playwright/test'

// 内嵌缓冲的最小三角面；extras 带随机标记，避免命中上传去重
const TRIANGLE_BUFFER =
  'AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAgD8AAAAAAAABAAIA'

function triangleGltf() {
  return {
    asset: { version: '2.0', generator: 'chainauth-e2e' },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 }, indices: 1 }] }],
    buffers: [{
      byteLength: 42,
      uri: `data:application/octet-stream;base64,${TRIANGLE_BUFFER}`
    }],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: 36, target: 34962 },
      { buffer: 0, byteOffset: 36, byteLength: 6, target: 34963 }
    ],
    accessors: [
      {
        bufferView: 0,
        componentType: 5126,
        count: 3,
        type: 'VEC3',
        max: [1, 1, 0],
        min: [0, 0, 0]
      },
      { bufferView: 1, componentType: 5123, count: 3, type: 'SCALAR' }
    ],
    extras: { e2e: `${Date.now()}-${Math.random()}` }
  }
}

test.describe('三维模型预览', () => {
  test('GLTF 模型在详情页加载并显示操作提示', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('user1')
    await page.getByPlaceholder('请输入密码').fill('123456')
    await page.locator('.login-btn').click()
    await page.waitForURL('**/assets', { timeout: 15000 })

    const payload = await page.evaluate(async (gltf) => {
      const token = localStorage.getItem('token')
      const form = new FormData()
      form.append(
        'file',
        new Blob([JSON.stringify(gltf)], { type: 'model/gltf+json' }),
        'e2e-triangle.gltf'
      )
      form.append('title', 'E2E 三维模型预览')
      form.append('asset_type', 'model')
      const response = await fetch('/api/assets/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form
      })
      const body = await response.json()
      return { id: body?.data?.asset_id, message: body?.message }
    }, triangleGltf())
    expect(payload.id, payload.message).toBeTruthy()

    const previewTicketRequest = page.waitForRequest(
      request => request.url().includes('/preview-ticket') && request.method() === 'POST'
    )
    await page.goto(`/assets/${payload.id}`)
    await previewTicketRequest
    await expect(page.getByText('拖拽旋转 · 滚轮缩放')).toBeVisible({ timeout: 20000 })
    await expect(page.getByText('模型解析失败，可下载后查看')).toHaveCount(0)
    await expect(page.locator('.model-viewer canvas')).toBeVisible()

    await page.evaluate(async (id) => {
      const token = localStorage.getItem('token')
      await fetch(`/api/assets/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
    }, payload.id)
  })
})
