import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
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

// 响应拦截器
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config

    // Token过期，尝试刷新（带队列防止并发刷新）
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem('refreshToken')
        if (!refreshToken) throw new Error('no refresh token')

        const response = await axios.post('/api/refresh', {}, {
          headers: { Authorization: `Bearer ${refreshToken}` }
        })

        if (response.data.code === 200) {
          const newToken = response.data.data.access_token
          localStorage.setItem('token', newToken)
          processQueue(null, newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        processQueue(refreshError)
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('user')
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // 其他错误（不重复显示刷新失败的错误；静默请求不弹提示）
    if (!error.config?._retry || error.response?.status !== 401) {
      if (!originalRequest?.silent) {
        notifyError(resolveErrorMessage(error))
      }
    }

    return Promise.reject(error)
  }
)

export default api
