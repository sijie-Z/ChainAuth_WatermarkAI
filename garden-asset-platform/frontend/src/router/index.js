import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useUserStore } from '@/stores/user'

// 管理员角色集合，与后端角色枚举保持一致（无 adm3 / super_admin）
const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']

// 页面加载器：保留统一入口，路由组件仍按需分包
const page = (loader) => loader

// 记录已触发过的加载器，悬停/聚焦与空闲预取不会重复请求
const prefetchedLoaders = new WeakSet()

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: page(() => import('@/views/home/index.vue')),
    meta: { title: '首页' }
  },
  {
    path: '/login',
    name: 'Login',
    component: page(() => import('@/views/home/login.vue')),
    meta: { title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: page(() => import('@/views/home/register.vue')),
    meta: { title: '注册' }
  },
  {
    path: '/assets',
    name: 'Assets',
    component: page(() => import('@/views/asset/list.vue')),
    meta: { title: '资产中心', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/assets/:id',
    name: 'AssetDetail',
    component: page(() => import('@/views/asset/detail.vue')),
    meta: { title: '资产详情', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/assets/upload',
    name: 'AssetUpload',
    component: page(() => import('@/views/asset/upload.vue')),
    meta: { title: '上传资产', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: page(() => import('@/views/asset/favorites.vue')),
    meta: { title: '我的收藏', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/downloads',
    name: 'MyDownloads',
    component: page(() => import('@/views/download/index.vue')),
    meta: { title: '下载记录', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/collections',
    name: 'Collections',
    component: page(() => import('@/views/collections/index.vue')),
    meta: { title: '我的合集', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/collections/:id',
    name: 'CollectionDetail',
    component: page(() => import('@/views/collections/detail.vue')),
    meta: { title: '合集详情', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/my-assets',
    name: 'MyAssets',
    component: page(() => import('@/views/asset/my-assets.vue')),
    meta: { title: '我的资产', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/trace',
    name: 'Trace',
    component: page(() => import('@/views/trace/index.vue')),
    meta: { title: '溯源查询', siteHeader: true }
  },
  {
    path: '/watermark-lab',
    name: 'WatermarkLab',
    component: page(() => import('@/views/watermark/lab.vue')),
    meta: { title: '水印实验室', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/verify-package',
    name: 'VerifyEvidencePackage',
    component: page(() => import('@/views/evidence/verify.vue')),
    meta: { title: '证据包核验', siteHeader: true }
  },
  {
    path: '/guide',
    name: 'Guide',
    component: page(() => import('@/views/guide/index.vue')),
    meta: { title: '使用指南', siteHeader: true }
  },
  {
    path: '/license/apply',
    name: 'LicenseApply',
    component: page(() => import('@/views/license/apply.vue')),
    meta: { title: '申请授权', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/license/my',
    name: 'MyLicenses',
    component: page(() => import('@/views/license/my.vue')),
    meta: { title: '我的授权', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/certificate/:id',
    name: 'Certificate',
    component: page(() => import('@/views/certificate/index.vue')),
    meta: { title: '存证证书', siteHeader: true }
  },
  {
    path: '/share/:token',
    name: 'SharedAsset',
    component: page(() => import('@/views/share/index.vue'), false),
    meta: { title: '资产分享' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: page(() => import('@/views/profile/index.vue')),
    meta: { title: '个人中心', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: page(() => import('@/views/settings/index.vue')),
    meta: { title: '账号设置', requiresAuth: true, siteHeader: true }
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: page(() => import('@/views/error/403.vue')),
    meta: { title: '权限不足' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: page(() => import('@/views/error/404.vue')),
    meta: { title: '页面未找到' }
  },
  // 管理后台
  {
    path: '/admin',
    name: 'AdminLayout',
    component: page(() => import('@/views/admin/layout.vue'), false),
    meta: { requiresAuth: true, roles: ADMIN_ROLES },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: page(() => import('@/views/admin/dashboard.vue'), false),
        meta: { title: '仪表盘' }
      },
      {
        path: 'assets',
        name: 'AdminAssets',
        component: page(() => import('@/views/admin/assets.vue'), false),
        meta: { title: '资产管理', roles: ['admin', 'asset_admin', 'adm1', 'adm2'] }
      },
      {
        path: 'watermark',
        name: 'AdminWatermark',
        component: page(() => import('@/views/admin/watermark.vue'), false),
        meta: { title: '水印管理', roles: ['admin', 'asset_admin'] }
      },
      {
        path: 'license/pending',
        name: 'AdminLicensePending',
        component: page(() => import('@/views/admin/license-pending.vue'), false),
        meta: { title: '待审批', roles: ADMIN_ROLES }
      },
      {
        path: 'license/approved',
        name: 'AdminLicenseApproved',
        component: page(() => import('@/views/admin/license-approved.vue'), false),
        meta: { title: '已审批', roles: ADMIN_ROLES }
      },
      {
        path: 'license/usage',
        name: 'AdminLicenseUsage',
        component: page(() => import('@/views/admin/license-usage.vue'), false),
        meta: { title: '使用报表', roles: ADMIN_ROLES }
      },
      {
        path: 'blockchain',
        name: 'AdminBlockchain',
        component: page(() => import('@/views/admin/blockchain.vue'), false),
        meta: { title: '存证管理', roles: ['admin', 'asset_admin'] }
      },
      {
        path: 'tasks',
        name: 'AdminTasks',
        component: page(() => import('@/views/admin/tasks.vue'), false),
        meta: { title: '任务队列', roles: ['admin', 'asset_admin'] }
      },
      {
        path: 'infringements',
        name: 'AdminInfringements',
        component: page(() => import('@/views/admin/infringements.vue'), false),
        meta: { title: '侵权线索', roles: ADMIN_ROLES }
      },
      {
        path: 'gardens',
        name: 'AdminGardens',
        component: page(() => import('@/views/admin/gardens.vue'), false),
        meta: { title: '园林档案', roles: ['admin', 'asset_admin'] }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: page(() => import('@/views/admin/users.vue'), false),
        meta: { title: '用户管理', roles: ['admin'] }
      },
      {
        path: 'notifications',
        name: 'AdminNotifications',
        component: page(() => import('@/views/admin/notifications.vue'), false),
        meta: { title: '通知渠道', roles: ['admin'] }
      },
      {
        path: 'downloads',
        name: 'AdminDownloads',
        component: page(() => import('@/views/download/index.vue'), false),
        meta: { title: '下载台账', roles: ADMIN_ROLES }
      },
      {
        path: 'logs',
        name: 'AdminLogs',
        component: page(() => import('@/views/admin/logs.vue'), false),
        meta: { title: '操作日志' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      return { el: to.hash, top: 88, behavior: 'smooth' }
    }
    return { top: 0 }
  }
})

NProgress.configure({
  showSpinner: false,
  minimum: 0.15,
  trickleSpeed: 120,
  speed: 260
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 同一路径重复点击不显示进度条，避免残留
  if (to.fullPath !== from.fullPath) {
    NProgress.start()
  }

  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 苏州园林数字资产平台` : '苏州园林数字资产平台'

  const userStore = useUserStore()

  // 已登录用户访问登录/注册页时按角色重定向
  if (userStore.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    return next(ADMIN_ROLES.includes(userStore.userRole) ? '/admin' : '/assets')
  }

  // 需要认证的路由
  if (to.meta.requiresAuth) {
    if (!userStore.isLoggedIn) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }

    // 角色权限检查：以最深层（最具体）路由的 roles 为准，
    // 避免父级后台路由的角色集合放宽子页面权限。
    const roleRecords = to.matched.filter(record => record.meta.roles?.length)
    const allowedRoles = roleRecords.length
      ? roleRecords[roleRecords.length - 1].meta.roles
      : []
    if (allowedRoles.length > 0) {
      const userRole = userStore.user?.role
      if (!allowedRoles.includes(userRole)) {
        return next('/403')
      }
    }
  }

  next()
})

router.afterEach(() => {
  NProgress.done()
})

router.onError(() => {
  NProgress.done()
})

let prefetchStarted = false

// 只预取最常用的几个页面；其余页面在用户悬停/聚焦链接时按需预取。
const CORE_PREFETCH_PATHS = ['/assets', '/trace', '/guide']

/**
 * 预取某个路径对应的路由分包。
 * 会沿匹配链找到最后一个异步组件，避免漏掉后台子路由。
 */
export function prefetchRoute(path) {
  if (!path || typeof window === 'undefined') return null
  try {
    const resolved = router.resolve(path)
    const record = [...resolved.matched].reverse().find(item => {
      const component = item.components?.default || item.component
      return typeof component === 'function'
    })
    const loader = record?.components?.default || record?.component
    if (typeof loader !== 'function' || prefetchedLoaders.has(loader)) {
      return loader || null
    }
    prefetchedLoaders.add(loader)
    Promise.resolve().then(loader).catch(() => {})
    return loader
  } catch {
    return null
  }
}

/**
 * 首屏稳定后只预取核心页面。
 * 弱网/省流模式直接跳过；其余页面在用户表现出意图（悬停/焦点）时再取。
 */
export function prefetchRoutes() {
  if (prefetchStarted || typeof window === 'undefined') return
  prefetchStarted = true

  const connection = navigator.connection
  if (connection?.saveData) return
  if (['slow-2g', '2g'].includes(connection?.effectiveType)) return

  const schedule = (cb) => {
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(cb, { timeout: 2500 })
    } else {
      window.setTimeout(cb, 350)
    }
  }

  let index = 0
  const loadNext = () => {
    if (index >= CORE_PREFETCH_PATHS.length) return
    prefetchRoute(CORE_PREFETCH_PATHS[index++])
    schedule(loadNext)
  }

  window.setTimeout(() => schedule(loadNext), 1200)
}

export default router
