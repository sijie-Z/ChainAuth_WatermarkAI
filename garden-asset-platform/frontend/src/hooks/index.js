/**
 * 前端Hook集合
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { debounce } from '@/utils'

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