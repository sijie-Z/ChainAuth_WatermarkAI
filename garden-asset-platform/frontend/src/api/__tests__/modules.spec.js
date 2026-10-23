import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import api from '@/api/index'
import {
  assetApi, blockchainApi, infringementApi, licenseApi, notificationApi,
  systemApi, taskApi, userApi
} from '@/api/modules'

describe('api modules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('assetApi.my fetches the current user assets', () => {
    assetApi.my({ page: 2 })

    expect(api.get).toHaveBeenCalledWith('/assets/my', { params: { page: 2 } })
  })

  it('assetApi.publish submits a draft for review', () => {
    assetApi.publish('asset-1')

    expect(api.post).toHaveBeenCalledWith('/assets/asset-1/publish')
  })

  it('assetApi.approve posts the review action', () => {
    assetApi.approve('asset-1', { action: 'approve' })

    expect(api.post).toHaveBeenCalledWith('/assets/asset-1/approve', { action: 'approve' })
  })

  it('licenseApi.myApplications fetches the user applications', () => {
    licenseApi.myApplications({ page: 1 })

    expect(api.get).toHaveBeenCalledWith('/license/my-applications', { params: { page: 1 } })
  })

  it('licenseApi.usageReport fetches admin usage metrics', () => {
    licenseApi.usageReport({ days: 30, version_outdated: '1' })

    expect(api.get).toHaveBeenCalledWith('/license/usage-report', {
      params: { days: 30, version_outdated: '1' }
    })
  })

  it('userApi.create posts a new user payload', () => {
    const payload = {
      username: 'new-user',
      password: 'secret',
      email: 'user@example.com',
      role: 'user',
      status: 'active'
    }

    userApi.create(payload)

    expect(api.post).toHaveBeenCalledWith('/users', payload)
  })

  it('blockchainApi.register forwards the async option', () => {
    blockchainApi.register('asset-1', { async: true })

    expect(api.post).toHaveBeenCalledWith(
      '/blockchain/register',
      { asset_id: 'asset-1', async: true }
    )
  })

  it('taskApi retries and cancels background tasks', () => {
    taskApi.retry('task-1')
    taskApi.cancel('task-1')

    expect(api.post).toHaveBeenCalledWith('/tasks/task-1/retry')
    expect(api.post).toHaveBeenCalledWith('/tasks/task-1/cancel')
  })

  it('assetApi.download forwards declared usage scope', () => {
    assetApi.download('asset-1', { purpose: 'teaching_research', territory: '中国大陆' })

    expect(api.get).toHaveBeenCalledWith('/assets/asset-1/download', {
      params: { purpose: 'teaching_research', territory: '中国大陆' },
      responseType: 'blob',
      timeout: 0
    })
  })

  it('notificationApi exposes server preferences and SSE URL', () => {
    notificationApi.updatePreferences({ email_enabled: true, email_groups: ['license'] })
    expect(api.put).toHaveBeenCalledWith('/notifications/preferences', {
      email_enabled: true,
      email_groups: ['license']
    })
    expect(notificationApi.streamUrl(12)).toContain('/notifications/stream?since_id=12')
  })

  it('infringementApi submits patrol batches', () => {
    const form = new FormData()
    infringementApi.patrol(form)

    expect(api.post).toHaveBeenCalledWith(
      '/infringements/patrol', form, { timeout: 0 }
    )
  })

  it('systemApi manages webhook config and test delivery', () => {
    systemApi.updateWebhook({ enabled: true, url: 'https://example.com/hook' })
    systemApi.testWebhook()

    expect(api.put).toHaveBeenCalledWith('/system/notification-webhook', {
      enabled: true,
      url: 'https://example.com/hook'
    })
    expect(api.post).toHaveBeenCalledWith('/system/notification-webhook/test')
  })

  it('keeps the existing method signatures', () => {
    assetApi.getList({ page: 1 })
    expect(api.get).toHaveBeenCalledWith('/assets', { params: { page: 1 } })

    assetApi.create('form-data')
    expect(api.post).toHaveBeenCalledWith('/assets/upload', 'form-data')

    licenseApi.getMyLicenses()
    expect(api.get).toHaveBeenCalledWith('/license/my', { params: undefined })

    userApi.updateUser(3, { role: 'admin' })
    expect(api.put).toHaveBeenCalledWith('/users/3', { role: 'admin' })
  })
})
