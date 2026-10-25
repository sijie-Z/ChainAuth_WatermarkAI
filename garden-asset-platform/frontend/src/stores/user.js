import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const refreshToken = ref(localStorage.getItem('refreshToken') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const userRole = computed(() => user.value?.role || '')
  const username = computed(() => user.value?.username || '')

  // 方法
  function setToken(accessToken, refresh) {
    token.value = accessToken
    refreshToken.value = refresh
    localStorage.setItem('token', accessToken)
    localStorage.setItem('refreshToken', refresh)
  }

  function setUser(userData) {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  // 清除本地登录态：供退出登录、token 刷新失败、路由守卫复用
  function clearAuth() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  function logout() {
    // 先捕获 token：clearAuth() 后 localStorage 为空，
    // axios 拦截器无法再补 Authorization，导致注销请求 401 并误报“登录已过期”。
    const accessToken = token.value
    const refresh = refreshToken.value
    if (accessToken) {
      api.post('/logout', { refresh_token: refresh || undefined }, {
        silent: true,
        skipAuthRefresh: true,
        headers: { Authorization: `Bearer ${accessToken}` }
      }).catch(() => {})
    }
    clearAuth()
  }

  async function login(credentials) {
    try {
      const response = await api.post('/login', credentials)
      if (response.data.code === 200) {
        const { access_token, refresh_token, user } = response.data.data
        setToken(access_token, refresh_token)
        setUser(user)
        return { success: true }
      }
      return { success: false, message: response.data.message }
    } catch (error) {
      return { success: false, message: error.response?.data?.message || '登录失败' }
    }
  }

  async function register(data) {
    try {
      const response = await api.post('/register', data)
      if (response.data.code === 200) {
        return { success: true, message: '注册成功' }
      }
      return { success: false, message: response.data.message }
    } catch (error) {
      return { success: false, message: error.response?.data?.message || '注册失败' }
    }
  }

  function initStore() {
    const savedToken = localStorage.getItem('token')
    const savedRefreshToken = localStorage.getItem('refreshToken')
    const savedUser = localStorage.getItem('user')
    if (savedToken && savedUser) {
      token.value = savedToken
      refreshToken.value = savedRefreshToken || ''
      user.value = JSON.parse(savedUser)
    }
  }

  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    userRole,
    username,
    setToken,
    setUser,
    clearAuth,
    logout,
    login,
    register,
    initStore
  }
})