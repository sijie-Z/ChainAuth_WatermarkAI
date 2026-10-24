/**
 * 前端Hook集合
 */
import { ref, onMounted, onBeforeUnmount, onUnmounted, computed, watch } from 'vue'
import { debounce } from '@/utils'
import { notificationApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

/**
 * 窗口大小Hook
 */
export function useWindowSize() {
  const width = ref(window.innerWidth)
  const height = ref(window.innerHeight)

  const update = () => {
    width.value = window.innerWidth
    height.value = window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', update)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', update)
  })

  return { width, height }
}

/**
 * 加载状态Hook
 */
export function useLoading(initialState = false) {
  const loading = ref(initialState)

  const startLoading = () => {
    loading.value = true
  }

  const stopLoading = () => {
    loading.value = false
  }

  const withLoading = async (fn) => {
    startLoading()
    try {
      await fn()
    } finally {
      stopLoading()
    }
  }

  return { loading, startLoading, stopLoading, withLoading }
}

/**
 * 分页Hook
 */
export function usePagination(defaultPerPage = 20) {
  const page = ref(1)
  const perPage = ref(defaultPerPage)
  const total = ref(0)

  const pages = computed(() => {
    return Math.ceil(total.value / perPage.value)
  })

  const setPage = (p) => {
    page.value = p
  }

  const setPerPage = (pp) => {
    perPage.value = pp
  }

  const setTotal = (t) => {
    total.value = t
  }

  const reset = () => {
    page.value = 1
    total.value = 0
  }

  return { page, perPage, total, pages, setPage, setPerPage, setTotal, reset }
}

/**
 * 搜索Hook
 */
export function useSearch(fetchFn, delay = 300) {
  const keyword = ref('')
  const results = ref([])
  const loading = ref(false)

  const doSearch = debounce(async () => {
    if (!keyword.value) {
      results.value = []
      return
    }

    loading.value = true
    try {
      const res = await fetchFn(keyword.value)
      results.value = res
    } finally {
      loading.value = false
    }
  }, delay)

  const clear = () => {
    keyword.value = ''
    results.value = []
  }

  return { keyword, results, loading, doSearch, clear }
}

/**
 * 表单验证Hook
 */
export function useFormValidation(rules) {
  const errors = ref({})
  const isValid = computed(() => {
    return Object.keys(errors.value).length === 0
  })

  const validate = (field, value) => {
    const rule = rules[field]
    if (!rule) return true

    const result = rule(value)
    if (result !== true) {
      errors.value[field] = result
      return false
    } else {
      delete errors.value[field]
      return true
    }
  }

  const validateAll = (formData) => {
    errors.value = {}
    let allValid = true

    for (const [field, rule] of Object.entries(rules)) {
      const result = rule(formData[field])
      if (result !== true) {
        errors.value[field] = result
        allValid = false
      }
    }

    return allValid
  }

  const clearErrors = () => {
    errors.value = {}
  }

  return { errors, isValid, validate, validateAll, clearErrors }
}

/**
 * 文件上传Hook
 */
export function useFileUpload(options = {}) {
  const file = ref(null)
  const uploading = ref(false)
  const progress = ref(0)

  const setFile = (f) => {
    file.value = f
  }

  const upload = async (uploadFn) => {
    if (!file.value) return

    uploading.value = true
    progress.value = 0

    try {
      const result = await uploadFn(file.value, (p) => {
        progress.value = p
      })
      return result
    } finally {
      uploading.value = false
    }
  }

  const clear = () => {
    file.value = null
    progress.value = 0
  }

  return { file, uploading, progress, setFile, upload, clear }
}

/**
 * 倒计时Hook
 */
export function useCountdown(seconds) {
  const count = ref(seconds)
  const running = ref(false)

  let timer = null

  const start = () => {
    running.value = true
    timer = setInterval(() => {
      count.value--
      if (count.value <= 0) {
        stop()
      }
    }, 1000)
  }

  const stop = () => {
    running.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  const reset = () => {
    stop()
    count.value = seconds
  }

  onUnmounted(() => {
    stop()
  })

  return { count, running, start, stop, reset }
}

/**
 * 站内通知 SSE 流
 *
 * 使用 fetch + ReadableStream 而不是 EventSource，以便携带 Authorization 头。
 * 断线按 5s 起指数退避重连；用 localStorage 记录最后事件 ID，重连后补发。
 */
export function useNotificationStream(onEvent) {
  const userStore = useUserStore()
  const connected = ref(false)
  const LAST_ID_KEY = 'notification-last-event-id'
  let controller = null
  let retryTimer = null
  let stopped = false
  let retryDelay = 5000

  function lastEventId() {
    const value = Number(localStorage.getItem(LAST_ID_KEY) || 0)
    return Number.isFinite(value) && value > 0 ? value : null
  }

  function rememberEventId(id) {
    if (Number.isFinite(Number(id)) && Number(id) > 0) {
      localStorage.setItem(LAST_ID_KEY, String(id))
    }
  }

  function dispatchChunk(chunk) {
    let eventId = null
    let eventName = 'message'
    const dataLines = []
    for (const line of chunk.split('\n')) {
      if (line.startsWith('id:')) {
        eventId = Number(line.slice(3).trim())
      } else if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
    if (!dataLines.length || eventName === 'close') return
    let payload = null
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      return
    }
    if (!payload || Object.keys(payload).length === 0) return
    if (eventId) rememberEventId(eventId)
    if (typeof onEvent === 'function') onEvent(payload)
  }

  async function connect() {
    if (stopped || !userStore.isLoggedIn) return
    const token = localStorage.getItem('token')
    if (!token) return

    controller = new AbortController()
    try {
      const response = await fetch(notificationApi.streamUrl(lastEventId()), {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal
      })
      if (response.status === 401) {
        // 交给 axios 拦截器刷新 access token，下一轮重连使用新 token
        await notificationApi.get().catch(() => {})
        throw new Error('unauthorized')
      }
      if (!response.ok || !response.body) {
        throw new Error(`stream failed: ${response.status}`)
      }

      connected.value = true
      retryDelay = 5000
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (!stopped) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary >= 0) {
          const chunk = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          dispatchChunk(chunk)
          boundary = buffer.indexOf('\n\n')
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        // 断线或鉴权失败，进入退避重连
      }
    } finally {
      connected.value = false
      controller = null
      if (!stopped && userStore.isLoggedIn) {
        retryTimer = setTimeout(connect, retryDelay)
        retryDelay = Math.min(retryDelay * 2, 30000)
      }
    }
  }

  function start() {
    if (stopped) stopped = false
    if (!controller) connect()
  }

  function stop() {
    stopped = true
    connected.value = false
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
    if (controller) {
      controller.abort()
      controller = null
    }
  }

  watch(() => userStore.isLoggedIn, loggedIn => {
    if (loggedIn) start()
    else stop()
  })

  onMounted(start)
  onBeforeUnmount(stop)

  return { connected, start, stop }
}