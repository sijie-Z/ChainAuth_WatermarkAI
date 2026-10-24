import { assetApi } from '@/api/modules'

/**
 * 先向服务端申请短时票据，再让浏览器直接访问下载地址。
 * 大文件由浏览器流式写入磁盘，不再整包读入 JS 内存。
 */
export async function startAssetDownload(assetId, params = {}) {
  const response = await assetApi.createDownloadTicket(assetId, params)
  const data = response.data?.data
  if (!data?.ticket) {
    throw new Error(response.data?.message || '下载凭证签发失败')
  }

  const baseURL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
  const link = document.createElement('a')
  link.href = `${baseURL}/assets/${assetId}/download?ticket=${encodeURIComponent(data.ticket)}`
  link.rel = 'noopener'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  link.remove()

  return data
}

/**
 * 预览票据直接作为 video/iframe/三维加载器的 URL，让浏览器按 Range 读取，
 * 避免把整段视频或 PDF 读进 JS 内存。
 */
export async function getAssetPreviewUrl(assetId) {
  const response = await assetApi.createPreviewTicket(assetId)
  const data = response.data?.data
  if (!data?.ticket) {
    throw new Error(response.data?.message || '预览凭证签发失败')
  }

  const baseURL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
  return `${baseURL}/assets/${assetId}/preview?ticket=${encodeURIComponent(data.ticket)}`
}
