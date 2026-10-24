import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

// 生产环境为 /api；开发环境可通过 VITE_API_BASE_URL 覆盖（默认走 vite proxy）
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

// 登录、注册、刷新接口自身返回 401 时不应触发 token 刷新
const AUTH_ENDPOINTS = ['/login', '/register', '/refresh']

const api = axios.create({
  baseURL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

function isAuthEndpoint(config) {
  const url = (config?.url || '').split('?')[0]
  return AUTH_ENDPOINTS.some(endpoint => url === endpoint || url.endsWith(endpoint))
}

// 请求拦截器
api.interceptors.request.use(
  config => {
    // FormData 必须让浏览器自行设置 multipart 边界；沿用实例默认的
    // application/json 会让后端完全收不到文件字段。
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      if (typeof config.headers?.delete === 'function') {
        config.headers.delete('Content-Type')
      } else if (config.headers) {
        delete config.headers['Content-Type']
      }
    }

    const token = localStorage.getItem('token')
    if (token && !config.skipAuth) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// 是否正在刷新token
let isRefreshing = false
let failedQueue = []

// 相同错误 3 秒内只提示一次，避免并发请求刷屏
let lastToast = { message: '', time: 0 }
function notifyError(message) {
  const now = Date.now()
  if (message === lastToast.message && now - lastToast.time < 3000) return
  lastToast = { message, time: now }
  ElMessage.error(message)
}

function resolveErrorMessage(error) {
  const status = error.response?.status
  if (status >= 500) return '服务暂时不可用，请稍后重试'
  if (!error.response) {
    return error.code === 'ECONNABORTED'
      ? '请求超时，请稍后重试'
      : '无法连接服务器，请检查网络'
  }
  return error.response?.data?.message || error.message || '请求失败'
}

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token)
  })
  failedQueue = []
}

// 刷新失败时同步清空 Pinia 与 localStorage，避免路由守卫仍认为已登录
function clearAuthState() {
  try {
    useUserStore().clearAuth()
  } catch {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }
}

// 响应拦截器
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config || {}

    // Token过期，尝试刷新（带队列防止并发刷新）。
    // 公开分享接口的 401 表示“需要/错误访问码”，不能触发登录刷新。
    if (
      error.response?.status === 401
      && !originalRequest._retry
      && !originalRequest.skipAuth
      && !isAuthEndpoint(originalRequest)
    ) {
      if (isRefreshing) {
        // 排队请求同样标记为已重试，避免重试再次 401 时无限刷新
        originalRequest._retry = true
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem('refreshToken')
        if (!refreshToken) throw new Error('no refresh token')

        const response = await axios.post(`${baseURL}/refresh`, {}, {
          headers: { Authorization: `Bearer ${refreshToken}` }
        })

        if (response.data.code !== 200) {
          throw new Error(response.data.message || 'refresh failed')
        }

        const newToken = response.data.data.access_token
        localStorage.setItem('token', newToken)
        processQueue(null, newToken)
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        clearAuthState()
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 其他错误（不重复显示刷新失败的错误；静默请求不弹提示）
    if (!originalRequest._retry || error.response?.status !== 401) {
      if (!originalRequest.silent) {
        notifyError(resolveErrorMessage(error))
      }
    }

    return Promise.reject(error)
  }
)

export default api
