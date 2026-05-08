import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// Element Plus样式
import 'element-plus/dist/index.css'

// 自定义样式
import '@/assets/styles/main.scss'

import App from './App.vue'
import router from './router'
import GlobalComponents from '@/components'

const app = createApp(App)

// Pinia
app.use(createPinia())

// 路由
app.use(router)

// Element Plus
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default'
})

// 全局组件
app.use(GlobalComponents)

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('[Vue Error]', err, info)
  // 生产环境可上报到监控服务
}

// 全局属性
app.config.globalProperties.$formatDate = (date) => {
  if (!date) return ''
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
