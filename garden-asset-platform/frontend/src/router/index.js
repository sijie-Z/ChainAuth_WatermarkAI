import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/home/login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/home/register.vue'),
    meta: { title: '注册' }
  },
  {
    path: '/assets',
    name: 'Assets',
    component: () => import('@/views/asset/list.vue'),
    meta: { title: '资产中心', requiresAuth: true }
  },
  {
    path: '/assets/:id',
    name: 'AssetDetail',
    component: () => import('@/views/asset/detail.vue'),
    meta: { title: '资产详情', requiresAuth: true }
  },
  {
    path: '/assets/upload',
    name: 'AssetUpload',
    component: () => import('@/views/asset/upload.vue'),
    meta: { title: '上传资产', requiresAuth: true }
  },
  {
    path: '/trace',
    name: 'Trace',
    component: () => import('@/views/trace/index.vue'),
    meta: { title: '溯源查询' }
  },
  {
    path: '/license/apply',
    name: 'LicenseApply',
    component: () => import('@/views/license/apply.vue'),
    meta: { title: '申请授权', requiresAuth: true }
  },
  {
    path: '/license/my',
    name: 'MyLicenses',
    component: () => import('@/views/license/my.vue'),
    meta: { title: '我的授权', requiresAuth: true }
  },
  {
    path: '/certificate/:id',
    name: 'Certificate',
    component: () => import('@/views/certificate/index.vue'),
    meta: { title: '存证证书' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/profile/index.vue'),
    meta: { title: '个人中心', requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/index.vue'),
    meta: { title: '账号设置', requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面未找到' }
  },
  // 管理后台
  {
    path: '/admin',
    name: 'AdminLayout',
    component: () => import('@/views/admin/layout.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'adm1', 'adm2', 'adm3'] },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/dashboard.vue'),
        meta: { title: '仪表盘' }
      },
      {
        path: 'assets',
        name: 'AdminAssets',
        component: () => import('@/views/admin/assets.vue'),
        meta: { title: '资产管理' }
      },
      {
        path: 'watermark',
        name: 'AdminWatermark',
        component: () => import('@/views/admin/watermark.vue'),
        meta: { title: '水印管理' }
      },
      {
        path: 'license/pending',
        name: 'AdminLicensePending',
        component: () => import('@/views/admin/license-pending.vue'),
        meta: { title: '待审批', roles: ['admin', 'adm1', 'adm2'] }
      },
      {
        path: 'license/approved',
        name: 'AdminLicenseApproved',
        component: () => import('@/views/admin/license-approved.vue'),
        meta: { title: '已审批' }
      },
      {
        path: 'blockchain',
        name: 'AdminBlockchain',
        component: () => import('@/views/admin/blockchain.vue'),
        meta: { title: '存证管理' }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/users.vue'),
        meta: { title: '用户管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 苏州园林数字资产平台` : '苏州园林数字资产平台'

  const userStore = useUserStore()

  // 已登录用户访问登录/注册页时重定向
  if (userStore.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    return next('/assets')
  }

  // 需要认证的路由
  if (to.meta.requiresAuth) {
    if (!userStore.isLoggedIn) {
      return next('/login')
    }

    // 角色权限检查：遍历 matched 路由收集所有允许的角色
    const allowedRoles = to.matched
      .flatMap(record => record.meta.roles || [])
    if (allowedRoles.length > 0) {
      const userRole = userStore.user?.role
      if (!allowedRoles.includes(userRole)) {
        ElMessage.warning('无权限访问该页面')
        return next('/home')
      }
    }
  }

  next()
})

export default router