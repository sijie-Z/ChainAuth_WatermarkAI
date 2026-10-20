import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  formatDate,
  formatFileSize,
  debounce,
  throttle,
  generateUUID,
  getAssetTypeName,
  getLicenseTypeName,
  getStatusTagType,
  getStatusText
} from '@/utils'

describe('formatDate', () => {
  it('returns empty string for empty input', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate('')).toBe('')
  })

  it('formats YYYY-MM-DD and time tokens', () => {
    const date = new Date(2026, 0, 2, 3, 4, 5)
    expect(formatDate(date)).toBe('2026-01-02')
    expect(formatDate(date, 'YYYY/MM/DD HH:mm:ss')).toBe('2026/01/02 03:04:05')
  })
})

describe('formatFileSize', () => {
  it('handles zero and bytes', () => {
    expect(formatFileSize(0)).toBe('0 B')
    expect(formatFileSize(512)).toBe('512 B')
  })

  it('converts to KB / MB / GB', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
    expect(formatFileSize(1536)).toBe('1.5 KB')
    expect(formatFileSize(1048576)).toBe('1 MB')
    expect(formatFileSize(1073741824)).toBe('1 GB')
  })
})

describe('asset / license name mapping', () => {
  it('maps known asset types', () => {
    expect(getAssetTypeName('image')).toBe('影像')
    expect(getAssetTypeName('model')).toBe('三维模型')
    expect(getAssetTypeName('vector')).toBe('矢量数据')
  })

  it('falls back to the raw value for unknown types', () => {
    expect(getAssetTypeName('unknown')).toBe('unknown')
    expect(getLicenseTypeName('unknown')).toBe('unknown')
  })

  it('maps license types', () => {
    expect(getLicenseTypeName('academic')).toBe('学术研究')
    expect(getLicenseTypeName('commercial')).toBe('商业使用')
  })
})

describe('status mapping', () => {
  it('maps known statuses', () => {
    expect(getStatusText('embedded')).toBe('已嵌入')
    expect(getStatusTagType('embedded')).toBe('success')
    expect(getStatusTagType('rejected')).toBe('danger')
  })

  it('falls back safely', () => {
    expect(getStatusText('mystery')).toBe('mystery')
    expect(getStatusTagType('mystery')).toBe('info')
  })
})

describe('generateUUID', () => {
  it('generates RFC4122 v4 shaped ids', () => {
    const uuid = generateUUID()
    expect(uuid).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
    expect(generateUUID()).not.toBe(uuid)
  })
})

describe('debounce / throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounce only calls the last invocation', () => {
    const fn = vi.fn()
    const debounced = debounce(fn, 100)
    debounced('a')
    debounced('b')
    expect(fn).not.toHaveBeenCalled()
    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('b')
  })

  it('throttle calls at most once per window', () => {
    const fn = vi.fn()
    const throttled = throttle(fn, 100)
    throttled('a')
    throttled('b')
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(100)
    throttled('c')
    expect(fn).toHaveBeenCalledTimes(2)
  })
})
