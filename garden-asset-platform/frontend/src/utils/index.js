/**
 * 前端公共工具函数
 */

/**
 * 解析后端日期。
 * 后端统一存 UTC 但 isoformat 不带时区（如 2026-10-21T09:30:00），
 * 直接 new Date() 会被浏览器当成本地时间；这里补 Z 后再解析。
 */
export function parseBackendDate(value) {
  if (!value) return null
  if (value instanceof Date) return value
  if (typeof value === 'string') {
    const naive = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/
    const normalized = naive.test(value) ? `${value}Z` : value
    const date = new Date(normalized)
    return Number.isNaN(date.getTime()) ? null : date
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/**
 * 格式化日期
 */
export function formatDate(date, format = 'YYYY-MM-DD') {
  const d = parseBackendDate(date)
  if (!d) return ''
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  const second = String(d.getSeconds()).padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second)
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 复制到剪贴板
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // fallback
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    return true
  }
}

/**
 * 防抖函数
 */
export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

/**
 * 节流函数
 */
export function throttle(fn, delay = 300) {
  let last = 0
  return function (...args) {
    const now = Date.now()
    if (now - last >= delay) {
      last = now
      fn.apply(this, args)
    }
  }
}

/**
 * 生成UUID
 */
export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * 获取资产类型名称
 */
export function getAssetTypeName(type) {
  const map = {
    image: '影像',
    model: '三维模型',
    vector: '矢量数据',
    document: '文献',
    video: '视频'
  }
  return map[type] || type
}

/**
 * 获取授权类型名称
 */
export function getLicenseTypeName(type) {
  const map = {
    personal: '个人使用',
    academic: '学术研究',
    commercial: '商业使用',
    display: '展览展示',
    derivative: '衍生创作'
  }
  return map[type] || type
}

/**
 * 获取状态标签类型
 */
export function getStatusTagType(status) {
  const map = {
    pending: 'warning',
    processing: 'info',
    embedded: 'success',
    confirmed: 'success',
    active: 'success',
    approved: 'success',
    rejected: 'danger',
    expired: 'info'
  }
  return map[status] || 'info'
}

/**
 * 获取状态文本
 */
export function getStatusText(status) {
  const map = {
    pending: '待处理',
    processing: '处理中',
    embedded: '已嵌入',
    confirmed: '已确认',
    active: '生效中',
    approved: '已通过',
    rejected: '已拒绝',
    expired: '已过期'
  }
  return map[status] || status
}