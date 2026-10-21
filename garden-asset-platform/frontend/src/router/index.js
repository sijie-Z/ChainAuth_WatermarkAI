import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import { useUserStore } from '@/stores/user'

// 管理员角色集合，与后端角色枚举保持一致（无 adm3 / super_admin）
const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']

// 登记所有页面加载器：首屏渲染完成后在浏览器空闲时逐块预取，
// 让后续点击不再等待路由分包下载，也不会阻塞首屏。
const prefetchable = []
const page = (loader, prefetch = true) => {
  if (prefetch) {
    prefetchable.push(loader)
  }
  return loader
}

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
        meta: { title: '资产管理' }
      },
      {
        path: 'watermark',
        name: 'AdminWatermark',
        component: page(() => import('@/views/admin/watermark.vue'), false),
        meta: { title: '水印管理' }
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
        meta: { title: '已审批' }
      },
      {
        path: 'blockchain',
        name: 'AdminBlockchain',
        component: page(() => import('@/views/admin/blockchain.vue'), false),
        meta: { title: '存证管理' }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: page(() => import('@/views/admin/users.vue'), false),
        meta: { title: '用户管理' }
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
    return savedPosition || { top: 0 }
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

    // 角色权限检查：遍历 matched 路由收集所有允许的角色
    const allowedRoles = to.matched
      .flatMap(record => record.meta.roles || [])
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

/**
 * 首屏渲染后逐块预取路由组件。
 * 每个页面加载完后才预约下一个空闲时段，避免一次性抢占带宽。
 */
export function prefetchRoutes() {
  if (prefetchStarted || typeof window === 'undefined') return
  prefetchStarted = true

  const schedule = (cb) => window.setTimeout(cb, 350)

  let index = 0
  const loadNext = () => {
    if (index >= prefetchable.length) return
    const loader = prefetchable[index++]
    Promise.resolve()
      .then(loader)
      .catch(() => {})
      .finally(() => schedule(loadNext))
  }

  window.setTimeout(() => schedule(loadNext), 1200)
}

export default router
