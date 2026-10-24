import { createApp } from 'vue'
import { createPinia } from 'pinia'

// 按需组件由 unplugin 自动导入；这里只保留基础变量与全局服务样式
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-notification.css'
import 'element-plus/theme-chalk/el-loading.css'

// 顶部路由进度条样式（需先于自定义样式加载，便于主题覆盖）
import 'nprogress/nprogress.css'

// 自定义样式
import '@/assets/styles/main.scss'

import App from './App.vue'
import router, { prefetchRoutes, prefetchRoute } from './router'
import GlobalComponents from '@/components'

const app = createApp(App)

// Pinia
app.use(createPinia())

// 路由
app.use(router)

// 全局组件
app.use(GlobalComponents)

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('[Vue Error]', err, info)
  // 生产环境可上报到监控服务
}

// 全局属性
app.config.globalProperties.$formatDate = (date) => {  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

app.config.globalProperties.$formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

app.mount('#app')

// 首屏完成后再预取核心页面；其余页面在用户悬停/聚焦链接时按需加载
router.isReady().then(() => {
  prefetchRoutes()
})

function handleIntentPrefetch(event) {
  const anchor = event.target?.closest?.('a[href]')
  if (!anchor) return
  try {
    const url = new URL(anchor.getAttribute('href'), window.location.origin)
    if (url.origin !== window.location.origin) return
    prefetchRoute(url.pathname)
  } catch {
    // 忽略非法链接
  }
}

document.addEventListener('mouseover', handleIntentPrefetch, { passive: true })
document.addEventListener('focusin', handleIntentPrefetch, { passive: true })
