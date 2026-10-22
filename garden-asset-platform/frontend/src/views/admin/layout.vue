<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar lattice-light" :class="{ collapsed: isCollapsed, 'mobile-open': mobileOpen }">
      <div class="sidebar-header">
        <router-link to="/admin" class="logo-container" title="返回仪表盘">
          <span class="logo-mark">园</span>
          <transition name="fade">
            <span v-if="!isCollapsed" class="logo-text">
              <span class="logo-name">园林资产台账</span>
              <span class="logo-sub">数字档案后台</span>
            </span>
          </transition>
        </router-link>
        <button
          class="collapse-btn"
          type="button"
          :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          :title="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          @click.stop="toggleCollapse"
        >
          <el-icon :class="{ rotated: isCollapsed }"><Expand /></el-icon>
        </button>
      </div>

      <nav class="sidebar-nav" aria-label="后台导航">
        <span v-if="!isCollapsed" class="nav-section-title">档案目录</span>
        <ul class="nav-list">
          <li v-for="item in visibleMenuItems" :key="item.path">
            <router-link
              v-if="!item.children"
              :to="item.path"
              class="nav-item"
              :class="{ active: isActive(item.path) }"
              :title="isCollapsed ? item.label : undefined"
            >
              <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
              <transition name="fade">
                <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
              </transition>
            </router-link>

            <template v-else>
              <button
                type="button"
                class="nav-item has-children"
                :class="{ expanded: expandedMenus.includes(item.path) }"
                :title="isCollapsed ? item.label : undefined"
                @click="toggleSubMenu(item.path)"
              >
                <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
                <transition name="fade">
                  <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
                </transition>
                <transition name="fade">
                  <el-icon v-if="!isCollapsed" class="nav-arrow"><ArrowDown /></el-icon>
                </transition>
              </button>
              <transition name="slide">
                <ul v-if="expandedMenus.includes(item.path) && !isCollapsed" class="sub-nav-list">
                  <li v-for="child in item.children" :key="child.path">
                    <router-link
                      :to="child.path"
                      class="sub-nav-item"
                      :class="{ active: isActive(child.path) }"
                    >
                      <span class="sub-nav-dot"></span>
                      <span>{{ child.label }}</span>
                    </router-link>
                  </li>
                </ul>
              </transition>
            </template>
          </li>
        </ul>
      </nav>

      <div class="sidebar-footer">
        <router-link to="/guide" class="sidebar-aux-link" title="使用指南">
          <el-icon><Reading /></el-icon>
          <span v-if="!isCollapsed">使用指南</span>
        </router-link>
        <router-link to="/home" class="sidebar-aux-link" title="返回前台">
          <el-icon><HomeFilled /></el-icon>
          <span v-if="!isCollapsed">返回前台</span>
        </router-link>
        <div class="user-card" :class="{ compact: isCollapsed }">
          <span class="user-avatar">{{ username?.charAt(0)?.toUpperCase() }}</span>
          <transition name="fade">
            <div v-if="!isCollapsed" class="user-info">
              <span class="user-name">{{ username }}</span>
              <span class="user-role">{{ roleLabel }}</span>
            </div>
          </transition>
        </div>
      </div>
    </aside>

    <div v-if="mobileOpen" class="sidebar-backdrop" @click="mobileOpen = false"></div>

    <!-- 主内容区 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <button class="mobile-menu-btn" type="button" aria-label="打开导航" @click="toggleMobileMenu">
            <el-icon><Menu /></el-icon>
          </button>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item>
              <router-link to="/admin" class="breadcrumb-home" aria-label="后台首页" title="后台首页">
                <el-icon aria-hidden="true"><HomeFilled /></el-icon>
              </router-link>
            </el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="topbar-right">
          <router-link to="/home" class="topbar-link">返回前台</router-link>

          <el-popover
            v-model:visible="pendingVisible"
            placement="bottom-end"
            :width="340"
            trigger="click"
            popper-class="admin-notification-popover"
          >
            <template #reference>
              <button class="topbar-bell" type="button" :aria-label="`待办提醒，${pendingNotifications} 条未读`">
                <el-badge :value="pendingNotifications" :hidden="pendingNotifications === 0" :max="99">
                  <el-icon><Bell /></el-icon>
                </el-badge>
              </button>
            </template>
            <div class="admin-pending-panel">
              <header class="pending-head">
                <strong>待办提醒</strong>
                <div class="pending-head-actions">
                  <span>{{ pendingNotifications }} 条未读</span>
                  <button
                    v-if="pendingNotifications > 0"
                    type="button"
                    class="pending-mark-all"
                    @click="markAllPendingRead"
                  >
                    全部已读
                  </button>
                </div>
              </header>
              <el-empty
                v-if="pendingItems.length === 0"
                description="暂无待办"
                :image-size="52"
              />
              <ul v-else class="pending-list">
                <li v-for="item in pendingItems" :key="item.id" :class="{ unread: !item.read }">
                  <router-link :to="item.link" @click="markPendingRead(item)">
                    <span class="pending-title">{{ item.title }}</span>
                    <span class="pending-desc">{{ item.description }}</span>
                  </router-link>
                </li>
              </ul>
            </div>
          </el-popover>

          <el-button
            :icon="isFullscreen ? Close : FullScreen"
            circle
            class="icon-btn"
            :aria-label="isFullscreen ? '退出全屏' : '进入全屏'"
            :title="isFullscreen ? '退出全屏' : '进入全屏'"
            @click="toggleFullscreen"
          />

          <el-dropdown trigger="click" @command="handleCommand">
            <button class="user-dropdown" type="button">
              <span class="user-avatar-small">{{ username?.charAt(0)?.toUpperCase() }}</span>
              <span class="user-name-small">{{ username }}</span>
              <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  账号设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="admin-main">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useNotificationStream } from '@/hooks'
import {
  DataLine, Picture, Stamp, Document, Link, User, Setting,
  Menu, HomeFilled, ArrowDown, Expand, SwitchButton,
  FullScreen, Close, Reading, Bell, Download, Place, Timer
} from '@element-plus/icons-vue'
import { notificationApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapsed = ref(false)
const mobileOpen = ref(false)
const isFullscreen = ref(false)
const expandedMenus = ref(['license'])
const pendingNotifications = ref(0)
const pendingItems = ref([])
const pendingVisible = ref(false)

const username = computed(() => userStore.username)
const userRole = computed(() => userStore.userRole)
const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    asset_admin: '资产管理员',
    license_admin: '授权管理员',
    adm1: '一级审批员',
    adm2: '二级审批员',
    user: '普通用户'
  }
  return labels[userRole.value] || '用户'
})

// 与后端角色枚举一致：user/asset_admin/license_admin/adm1/adm2/admin
const ASSET_ROLES = ['admin', 'asset_admin', 'adm1', 'adm2']
// 水印/上链只允许资产管理员与超级管理员（与后端一致）
const WATERMARK_ROLES = ['admin', 'asset_admin']
// 后端审批角色：adm1/asset_admin 参与一级审批，adm2/license_admin 参与二级审批
const LICENSE_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']
const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']

const menuItems = shallowRef([
  { path: '/admin', label: '仪表盘', icon: DataLine, roles: ADMIN_ROLES },
  { path: '/admin/assets', label: '资产管理', icon: Picture, roles: ASSET_ROLES },
  { path: '/admin/watermark', label: '水印管理', icon: Stamp, roles: WATERMARK_ROLES },
  { path: '/admin/blockchain', label: '存证管理', icon: Link, roles: WATERMARK_ROLES },
  { path: '/admin/tasks', label: '任务队列', icon: Timer, roles: WATERMARK_ROLES },
  {
    path: 'license',
    label: '授权审批',
    icon: Document,
    roles: LICENSE_ROLES,
    children: [
      { path: '/admin/license/pending', label: '待审批' },
      { path: '/admin/license/approved', label: '已审批' }
    ]
  },
  { path: '/admin/gardens', label: '园林档案', icon: Place, roles: WATERMARK_ROLES },
  { path: '/admin/downloads', label: '下载台账', icon: Download, roles: ADMIN_ROLES },
  { path: '/admin/users', label: '用户管理', icon: User, roles: ['admin'] },
  { path: '/admin/logs', label: '操作日志', icon: Document, roles: ADMIN_ROLES }
])

// 菜单按当前角色过滤；移动端抽屉行为保持不变
const visibleMenuItems = computed(() => {
  return menuItems.value.filter(item => !item.roles || item.roles.includes(userRole.value))
})

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title
  }))
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

// 切换后台子页面时收起移动端抽屉，避免遮住新页面
watch(() => route.path, () => {
  mobileOpen.value = false
  loadPendingNotifications()
})

function toggleMobileMenu() {
  mobileOpen.value = !mobileOpen.value
}

async function loadPendingNotifications() {
  try {
    const response = await notificationApi.get()
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      pendingItems.value = data.items || []
      pendingNotifications.value = data.unread_count ?? data.count ?? 0
    }
  } catch {
    // 待办数量失败不影响后台使用
  }
}

async function markPendingRead(item) {
  pendingVisible.value = false
  if (item.read || !item.key) return
  item.read = true
  pendingNotifications.value = Math.max(
    0, pendingNotifications.value - (item.count || 1)
  )
  try {
    const response = await notificationApi.markRead({ keys: [item.key] })
    if (typeof response.data?.data?.unread_count === 'number') {
      pendingNotifications.value = response.data.data.unread_count
    }
  } catch {
    item.read = false
    loadPendingNotifications()
  }
}

async function markAllPendingRead() {
  if (pendingNotifications.value === 0) return
  pendingItems.value.forEach(item => { item.read = true })
  pendingNotifications.value = 0
  try {
    await notificationApi.markRead({ all: true })
  } catch {
    loadPendingNotifications()
  }
}

function toggleSubMenu(path) {
  const index = expandedMenus.value.indexOf(path)
  if (index > -1) {
    expandedMenus.value.splice(index, 1)
  } else {
    expandedMenus.value.push(path)
  }
}

function isActive(path) {
  return route.path === path
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'settings') {
    router.push('/settings')
  }
}

function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function handleKeydown(event) {
  if (event.key === 'Escape' && mobileOpen.value) {
    mobileOpen.value = false
  }
}

watch(mobileOpen, open => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('keydown', handleKeydown)
  loadPendingNotifications()
})

useNotificationStream((event) => {
  loadPendingNotifications()
  ElNotification({
    title: event.title || '新通知',
    message: event.description || '你有一条新的站内通知',
    type: /rejected|revoked|failed/.test(event.event_type || '') ? 'warning' : 'info',
    duration: 6000,
    onClick: () => {
      if (event.link) router.push(event.link)
    }
  })
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-layout {
  display: flex;
  min-height: 100vh;
  background: $bg-primary;
}

// ========== 侧边栏 ==========
.sidebar {
  width: $sidebar-width;
  background: $primary-dark;
  display: flex;
  flex-direction: column;
  transition: width $transition-base;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: $z-fixed;
  border-right: 1px solid rgba(252, 253, 251, 0.08);

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      flex-direction: column;
      gap: 8px;
      padding: 14px 8px;
      justify-content: center;
    }

    // 折叠后仍保留展开入口，否则桌面端没有恢复方式
    .collapse-btn {
      display: inline-flex;
    }

    .nav-item {
      justify-content: center;
      padding: 12px;
    }

    .sidebar-footer { padding: 12px; }
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 18px 16px;
  border-bottom: 1px solid rgba(252, 253, 251, 0.08);
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;

  .logo-mark {
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(252, 253, 251, 0.38);
    border-radius: $radius-xs;
    color: #fcfdfb;
    font-family: $font-display;
    font-size: 18px;
  }

  .logo-text {
    display: flex;
    flex-direction: column;
    line-height: 1.3;
    white-space: nowrap;
  }

  .logo-name {
    font-family: $font-display;
    font-size: 15px;
    color: #fcfdfb;
    letter-spacing: 0.04em;
  }

  .logo-sub {
    font-size: 10px;
    letter-spacing: 0.14em;
    color: rgba(252, 253, 251, 0.45);
  }
}

.collapse-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(252, 253, 251, 0.16);
  border-radius: $radius-xs;
  color: rgba(252, 253, 251, 0.65);
  cursor: pointer;

  &:hover {
    color: #fcfdfb;
    border-color: rgba(252, 253, 251, 0.36);
  }

  .el-icon {
    transition: transform $transition-base;

    &.rotated { transform: rotate(180deg); }
  }
}

// 导航
.sidebar-nav {
  flex: 1;
  padding: 18px 10px;
  overflow-y: auto;
}

.nav-section-title {
  display: block;
  padding: 0 12px;
  margin-bottom: 8px;
  font-size: 10px;
  letter-spacing: 0.2em;
  color: rgba(252, 253, 251, 0.35);
}

.nav-list {
  list-style: none;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 2px;
  background: transparent;
  border: none;
  border-radius: $radius-sm;
  color: rgba(252, 253, 251, 0.68);
  font-size: 14px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  transition: color $transition-fast, background $transition-fast;

  .nav-icon {
    font-size: 17px;
    flex-shrink: 0;
  }

  .nav-label {
    flex: 1;
    white-space: nowrap;
  }

  .nav-arrow {
    font-size: 11px;
    color: rgba(252, 253, 251, 0.4);
    transition: transform $transition-fast;
  }

  &:hover {
    color: #fcfdfb;
    background: rgba(252, 253, 251, 0.06);
  }

  &.active {
    color: #fcfdfb;
    background: rgba(252, 253, 251, 0.08);

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 8px;
      bottom: 8px;
      width: 2px;
      background: $accent-light;
      border-radius: 1px;
    }
  }

  &.has-children.expanded .nav-arrow {
    transform: rotate(180deg);
  }
}

.sub-nav-list {
  list-style: none;
  padding: 2px 0 6px 38px;
}

.sub-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: $radius-xs;
  color: rgba(252, 253, 251, 0.6);
  font-size: 13px;

  .sub-nav-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: rgba(252, 253, 251, 0.3);
  }

  &:hover {
    color: #fcfdfb;
    background: rgba(252, 253, 251, 0.05);
  }

  &.active {
    color: #fcfdfb;

    .sub-nav-dot { background: $accent-light; }
  }
}

.sidebar-footer {
  padding: 12px 14px;
  border-top: 1px solid rgba(252, 253, 251, 0.08);
}

.sidebar-aux-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  margin-bottom: 2px;
  border-radius: $radius-xs;
  font-size: 12.5px;
  color: rgba(252, 253, 251, 0.62);

  &:hover {
    background: rgba(252, 253, 251, 0.06);
    color: #fcfdfb;
  }

  .el-icon {
    font-size: 14px;
  }
}

.sidebar.collapsed .sidebar-aux-link {
  justify-content: center;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid rgba(252, 253, 251, 0.1);
  border-radius: $radius-sm;

  &.compact {
    justify-content: center;
    border-color: transparent;
  }

  .user-avatar {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: $radius-xs;
    background: rgba(252, 253, 251, 0.12);
    color: #fcfdfb;
    font-family: $font-display;
    font-size: 14px;
  }

  .user-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    line-height: 1.35;
  }

  .user-name {
    font-size: 13px;
    color: #fcfdfb;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .user-role {
    font-size: 11px;
    color: rgba(252, 253, 251, 0.45);
  }
}

// ========== 主内容区 ==========
.main-area {
  flex: 1;
  min-width: 0;
  margin-left: $sidebar-width;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left $transition-base;
}

.sidebar.collapsed ~ .main-area {
  margin-left: $sidebar-collapsed-width;
}

.topbar {
  height: $header-height;
  background: rgba(252, 253, 251, 0.98);
  border-bottom: 1px solid $border-light;  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: $z-sticky;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.mobile-menu-btn {
  display: none;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  color: $text-secondary;
  cursor: pointer;
}

.breadcrumb {
  :deep(.el-breadcrumb__inner) {
    display: flex;
    align-items: center;
    gap: 4px;
    color: $text-secondary;
    font-weight: 400;

    &.is-link:hover { color: $primary-color; }
  }

  .breadcrumb-home {
    display: inline-flex;
    align-items: center;
    color: $text-secondary;

    &:hover { color: $primary-color; }
  }

  :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
    color: $text-primary;
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-bell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  background: transparent;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  color: $text-secondary;
  cursor: pointer;

  &:hover {
    border-color: $primary-color;
    color: $primary-dark;
  }

  :deep(.el-badge__content) {
    border: none;
    background: $accent-color;
    font-size: 10px;
  }
}

.admin-pending-panel {
  .pending-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding-bottom: 8px;
    margin-bottom: 4px;
    border-bottom: 1px solid $border-light;

    strong {
      font-size: 14px;
      color: $text-primary;
    }
  }
}

.pending-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: $text-placeholder;
}

.pending-mark-all {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 11px;
  color: $primary-color;
  cursor: pointer;

  &:hover { text-decoration: underline; }
}

.pending-list {
  list-style: none;
  max-height: 320px;
  overflow-y: auto;

  li + li {
    border-top: 1px solid $border-light;
  }

  li.unread a {
    background: rgba(47, 107, 90, 0.04);
  }

  a {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 9px 6px;
    border-radius: $radius-xs;
    color: $text-primary;

    &:hover {
      background: $bg-hover;
      color: $text-primary;
    }
  }
}

.pending-title {
  font-size: 13px;
  font-weight: 500;
}

.pending-desc {
  font-size: 12px;
  line-height: 1.6;
  color: $text-secondary;
}

.topbar-link {
  font-size: 13px;
  color: $text-secondary;
  padding: 6px 10px;
  border-radius: $radius-xs;

  &:hover {
    color: $primary-dark;
    background: $bg-secondary;
  }
}

.icon-btn {
  background: $bg-card !important;
  border: 1px solid $border-color !important;
  color: $text-secondary !important;

  &:hover {
    color: $primary-color !important;
    border-color: $primary-color !important;
  }
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 5px;
  background: transparent;
  border: 1px solid $border-color;
  border-radius: $radius-full;
  cursor: pointer;

  &:hover { border-color: $border-dark; }

  .user-avatar-small {
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: $accent-color;
    color: #fcfdfb;
    font-family: $font-display;
    font-size: 13px;
  }

  .user-name-small {
    font-size: 13px;
    color: $text-primary;
  }

  .dropdown-arrow {
    font-size: 11px;
    color: $text-placeholder;
  }
}

.admin-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

@media (max-width: 768px) {
  .admin-main {
    padding: 0;
  }
}

// ========== 移动端遮罩 ==========
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1029;
  background: rgba(14, 59, 51, 0.35);
}

// ========== 动画 ==========
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

.slide-enter-active,
.slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from,
.slide-leave-to { opacity: 0; transform: translateY(-6px); }

.page-fade-enter-active,
.page-fade-leave-active { transition: opacity 0.2s ease; }
.page-fade-enter-from,
.page-fade-leave-to { opacity: 0; }

// ========== 响应式 ==========
@media (max-width: 992px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform $transition-base;

    &.mobile-open {
      width: $sidebar-width;
      transform: translateX(0);
    }
  }

  .main-area {
    margin-left: 0 !important;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }
}

@media (max-width: 576px) {
  .topbar { padding: 0 14px; }
  .topbar-link { display: none; }
  .user-name-small { display: none; }
}
</style>
