import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

import api from '@/api'
import { useUserStore } from '@/stores/user'

describe('user store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('stores tokens and profile after a successful login', async () => {
    api.post.mockResolvedValue({
      data: {
        code: 200,
        data: {
          access_token: 'access-1',
          refresh_token: 'refresh-1',
          user: { id: 1, username: 'alice', role: 'user' }
        }
      }
    })

    const store = useUserStore()
    const result = await store.login({ username: 'alice', password: 'secret' })

    expect(result).toEqual({ success: true })
    expect(store.isLoggedIn).toBe(true)
    expect(store.username).toBe('alice')
    expect(store.userRole).toBe('user')
    expect(localStorage.getItem('token')).toBe('access-1')
    expect(localStorage.getItem('refreshToken')).toBe('refresh-1')
    expect(JSON.parse(localStorage.getItem('user'))).toMatchObject({ username: 'alice' })
  })

  it('returns the server message when login is rejected', async () => {
    api.post.mockResolvedValue({ data: { code: 401, message: '用户名或密码错误' } })

    const store = useUserStore()
    const result = await store.login({ username: 'alice', password: 'wrong' })

    expect(result).toEqual({ success: false, message: '用户名或密码错误' })
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('returns a friendly message on network failure', async () => {
    api.post.mockRejectedValue(new Error('Network Error'))

    const store = useUserStore()
    const result = await store.login({ username: 'alice', password: 'secret' })

    expect(result).toEqual({ success: false, message: '登录失败' })
  })

  it('logout clears state and storage', async () => {
    api.post.mockResolvedValue({
      data: {
        code: 200,
        data: {
          access_token: 'a',
          refresh_token: 'r',
          user: { id: 1, username: 'alice', role: 'admin' }
        }
      }
    })

    const store = useUserStore()
    await store.login({ username: 'alice', password: 'secret' })
    store.logout()

    // 注销请求必须携带显式 Authorization，且失败时不触发 token 刷新提示
    expect(api.post).toHaveBeenCalledWith(
      '/logout',
      { refresh_token: 'r' },
      expect.objectContaining({
        skipAuthRefresh: true,
        headers: { Authorization: 'Bearer a' }
      })
    )
    expect(store.isLoggedIn).toBe(false)
    expect(store.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('refreshToken')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('clearAuth resets token, refresh token and user together', async () => {
    api.post.mockResolvedValue({
      data: {
        code: 200,
        data: {
          access_token: 'access-2',
          refresh_token: 'refresh-2',
          user: { id: 3, username: 'carol', role: 'asset_admin' }
        }
      }
    })

    const store = useUserStore()
    await store.login({ username: 'carol', password: 'secret' })

    store.clearAuth()

    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('refreshToken')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('initStore restores a saved session', () => {
    localStorage.setItem('token', 'saved-token')
    localStorage.setItem('refreshToken', 'saved-refresh')
    localStorage.setItem('user', JSON.stringify({ id: 2, username: 'bob', role: 'adm1' }))

    const store = useUserStore()
    store.initStore()

    expect(store.isLoggedIn).toBe(true)
    expect(store.username).toBe('bob')
    expect(store.userRole).toBe('adm1')
    expect(store.refreshToken).toBe('saved-refresh')
  })

  it('register reports success and failure without logging in', async () => {
    const store = useUserStore()

    api.post.mockResolvedValueOnce({ data: { code: 200 } })
    await expect(store.register({ username: 'new' })).resolves.toEqual({
      success: true,
      message: '注册成功'
    })
    expect(store.isLoggedIn).toBe(false)

    api.post.mockResolvedValueOnce({ data: { code: 400, message: '用户名已存在' } })
    await expect(store.register({ username: 'new' })).resolves.toEqual({
      success: false,
      message: '用户名已存在'
    })
  })
})
