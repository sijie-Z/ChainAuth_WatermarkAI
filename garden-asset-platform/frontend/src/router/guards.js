/**
 * 前端路由守卫工具
 */
import { useUserStore } from '@/stores/user'

/**
 * 权限守卫
 */
export function permissionGuard(router) {
  router.beforeEach((to, from, next) => {
    const userStore = useUserStore()

    // 公开路由
    const publicRoutes = ['/home', '/login', '/register', '/trace', '/gardens']

    if (publicRoutes.includes(to.path) || to.meta.public) {
      return next()
    }

    // 需要认证的路由
    if (to.meta.requiresAuth && !userStore.isLoggedIn) {
      return next('/login')
    }

    // 角色权限检查
    if (to.meta.roles && to.meta.roles.length > 0) {
      const userRole = userStore.user?.role
      if (!to.meta.roles.includes(userRole)) {
        return next('/403')
      }
    }

    next()
  })
}

/**
 * 进度条守卫
 */
export function progressGuard(router) {
  router.beforeEach(() => {
    // NProgress.start()
  })

  router.afterEach(() => {
    // NProgress.done()
  })
}

/**
 * 标题守卫
 */
export function titleGuard(router) {
  router.afterEach((to) => {
    const title = to.meta.title || '苏州园林数字资产平台'
    document.title = `${title} - 苏州园林数字资产平台`
  })
}

/**
 * 初始化所有守卫
 */
export function setupGuards(router) {
  permissionGuard(router)
  progressGuard(router)
  titleGuard(router)
}