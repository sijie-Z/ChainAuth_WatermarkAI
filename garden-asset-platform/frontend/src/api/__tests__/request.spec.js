import { describe, it, expect, beforeEach, vi } from 'vitest'

const { instance, axiosCreate, axiosPost, routerPush, clearAuth, messageError } = vi.hoisted(() => {
  const instance = vi.fn(() => Promise.resolve({ data: { code: 200 } }))
  instance.interceptors = {
    request: { use: vi.fn() },
    response: { use: vi.fn() }
  }
  instance.defaults = {}
  return {
    instance,
    axiosCreate: vi.fn(() => instance),
    axiosPost: vi.fn(),
    routerPush: vi.fn(),
    clearAuth: vi.fn(),
    messageError: vi.fn()
  }
})

vi.mock('axios', () => ({
  default: {
    create: axiosCreate,
    post: axiosPost
  }
}))

vi.mock('@/router', () => ({
  default: {
    push: routerPush,
    currentRoute: { value: { path: '/assets' } }
  }
}))

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ clearAuth })
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: messageError }
}))

import api from '@/api'

const createdConfig = { ...axiosCreate.mock.calls[0][0] }
const responseHandler = instance.interceptors.response.use.mock.calls[0][1]

function unauthorized(url = '/assets/1') {
  return {
    config: { url, headers: {} },
    response: { status: 401, data: { message: '未授权' } }
  }
}

describe('api request interceptor', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.resetAllMocks()
    instance.mockImplementation(() => Promise.resolve({ data: { code: 200 } }))
  })

  it('uses VITE_API_BASE_URL when configured, otherwise /api', () => {
    expect(api).toBe(instance)
    expect(createdConfig.baseURL).toBe(import.meta.env.VITE_API_BASE_URL || '/api')
  })

  it('does not refresh the token for login 401 responses', async () => {
    const error = unauthorized('/login')

    await expect(responseHandler(error)).rejects.toBe(error)

    expect(axiosPost).not.toHaveBeenCalled()
    expect(error.config._retry).toBeUndefined()
  })

  it('does not refresh the token for register 401 responses', async () => {
    const error = unauthorized('/register')

    await expect(responseHandler(error)).rejects.toBe(error)

    expect(axiosPost).not.toHaveBeenCalled()
  })

  it('retries the original request with the refreshed token', async () => {
    localStorage.setItem('refreshToken', 'refresh-1')
    axiosPost.mockResolvedValue({
      data: { code: 200, data: { access_token: 'new-token' } }
    })
    const error = unauthorized()

    await responseHandler(error)

    expect(axiosPost).toHaveBeenCalledWith(
      `${createdConfig.baseURL}/refresh`,
      {},
      { headers: { Authorization: 'Bearer refresh-1' } }
    )
    expect(error.config._retry).toBe(true)
    expect(error.config.headers.Authorization).toBe('Bearer new-token')
    expect(instance).toHaveBeenCalledWith(error.config)
    expect(localStorage.getItem('token')).toBe('new-token')
  })

  it('clears auth state and redirects when refresh fails', async () => {
    localStorage.setItem('refreshToken', 'refresh-1')
    axiosPost.mockRejectedValue(new Error('refresh failed'))
    const error = unauthorized()

    await expect(responseHandler(error)).rejects.toThrow('refresh failed')

    expect(clearAuth).toHaveBeenCalled()
    expect(routerPush).toHaveBeenCalledWith('/login')
  })

  it('clears auth state when no refresh token is stored', async () => {
    const error = unauthorized()

    await expect(responseHandler(error)).rejects.toThrow('no refresh token')

    expect(axiosPost).not.toHaveBeenCalled()
    expect(clearAuth).toHaveBeenCalled()
  })

  it('treats a non-200 refresh body as a refresh failure', async () => {
    localStorage.setItem('refreshToken', 'refresh-1')
    axiosPost.mockResolvedValue({ data: { code: 401, message: 'refresh expired' } })
    const error = unauthorized()

    await expect(responseHandler(error)).rejects.toThrow('refresh expired')

    expect(clearAuth).toHaveBeenCalled()
    expect(routerPush).toHaveBeenCalledWith('/login')
  })

  it('marks queued concurrent requests as retried', async () => {
    localStorage.setItem('refreshToken', 'refresh-1')
    let resolveRefresh
    axiosPost.mockReturnValue(
      new Promise(resolve => {
        resolveRefresh = resolve
      })
    )

    const first = unauthorized('/assets/1')
    const second = unauthorized('/assets/2')

    const firstPromise = responseHandler(first)
    const secondPromise = responseHandler(second)

    // 排队分支在入队时即标记，避免重试再次触发刷新
    expect(second.config._retry).toBe(true)

    resolveRefresh({ data: { code: 200, data: { access_token: 'token-2' } } })

    await Promise.all([firstPromise, secondPromise])

    expect(first.config._retry).toBe(true)
    expect(second.config._retry).toBe(true)
    expect(second.config.headers.Authorization).toBe('Bearer token-2')
    expect(instance).toHaveBeenCalledTimes(2)
  })
})
