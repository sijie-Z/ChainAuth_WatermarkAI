<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <!-- Logo区域 -->
      <div class="sidebar-header">
        <div class="logo-container">
          <div class="logo-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 2L4 10v12l12 8 12-8V10L16 2z" fill="url(#logoGradient)"/>
              <path d="M16 8L8 13v6l8 5 8-5v-6l-8-5z" fill="white" fill-opacity="0.3"/>
              <defs>
                <linearGradient id="logoGradient" x1="4" y1="2" x2="28" y2="30">
                  <stop stop-color="#10b981"/>
                  <stop offset="1" stop-color="#059669"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <transition name="fade">
            <span v-if="!isCollapsed" class="logo-text">园林资产平台</span>
          </transition>
        </div>
        <button class="collapse-btn" @click="toggleCollapse">
          <el-icon :class="{ rotated: isCollapsed }"><Expand /></el-icon>
        </button>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-section">
          <transition name="fade">
            <span v-if="!isCollapsed" class="nav-section-title">主菜单</span>
          </transition>
          <ul class="nav-list">
            <li v-for="item in menuItems" :key="item.path">
              <router-link
                :to="item.path"
                class="nav-item"
                :class="{ active: isActive(item.path) }"
                v-if="!item.children"
              >
                <div class="nav-icon-wrapper">
                  <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
                </div>
                <transition name="fade">
                  <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
                </transition>
                <transition name="fade">
                  <span v-if="!isCollapsed && item.badge" class="nav-badge">{{ item.badge }}</span>
                </transition>
              </router-link>

              <!-- 有子菜单 -->
              <template v-else>
                <div class="nav-item has-children" @click="toggleSubMenu(item.path)" :class="{ expanded: expandedMenus.includes(item.path) }">
                  <div class="nav-icon-wrapper">
                    <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
                  </div>
                  <transition name="fade">
                    <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
                  </transition>
                  <transition name="fade">
                    <el-icon v-if="!isCollapsed" class="nav-arrow"><ArrowDown /></el-icon>
                  </transition>
                </div>
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
                        <span v-if="child.badge" class="nav-badge">{{ child.badge }}</span>
                      </router-link>
                    </li>
                  </ul>
                </transition>
              </template>
            </li>
          </ul>
        </div>
      </nav>

      <!-- 用户信息 -->
      <div class="sidebar-footer">
        <div class="user-card" :class="{ compact: isCollapsed }">
          <el-avatar :size="isCollapsed ? 36 : 40" class="user-avatar">
            {{ username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <transition name="fade">
            <div v-if="!isCollapsed" class="user-info">
              <div class="user-name">{{ username }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
          </transition>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-area">
      <!-- 顶栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="mobile-menu-btn" @click="toggleMobileMenu">
            <el-icon><Menu /></el-icon>
          </button>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/admin' }">
              <el-icon><HomeFilled /></el-icon>
            </el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="topbar-right">
          <!-- 搜索 -->
          <div class="search-box">
            <el-input
              v-model="searchQuery"
              placeholder="搜索..."
              prefix-icon="Search"
              size="default"
              clearable
            />
          </div>

          <!-- 通知 -->
          <el-badge :value="notificationCount" :hidden="notificationCount === 0" class="notification-badge">
            <el-button :icon="Bell" circle class="icon-btn" />
          </el-badge>

          <!-- 全屏 -->
          <el-button :icon="isFullscreen ? Close : FullScreen" circle class="icon-btn" @click="toggleFullscreen" />

          <!-- 用户下拉 -->
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-dropdown">
              <el-avatar :size="32" class="user-avatar-small">
                {{ username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <span class="user-name-small">{{ username }}</span>
              <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
            </div>
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

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  DataLine, Picture, Stamp, Document, Link, User, Setting,
  Bell, Menu, HomeFilled, ArrowDown, Expand, SwitchButton,
  FullScreen, Close, Search
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 状态
const isCollapsed = ref(false)
const isFullscreen = ref(false)
const searchQuery = ref('')
const notificationCount = ref(3)
const expandedMenus = ref(['license'])

// 用户信息
const username = computed(() => userStore.username)
const userRole = computed(() => userStore.userRole)
const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    adm1: '资产管理员',
    adm2: '授权管理员',
    adm3: '审核员',
    user: '普通用户'
  }
  return labels[userRole.value] || '用户'
})

// 菜单配置
const menuItems = ref([
  { path: '/admin', label: '仪表盘', icon: 'DataLine' },
  { path: '/admin/assets', label: '资产管理', icon: 'Picture', badge: '156' },
  { path: '/admin/watermark', label: '水印管理', icon: 'Stamp' },
  {
    path: 'license',
    label: '授权审批',
    icon: 'Document',
    children: [
      { path: '/admin/license/pending', label: '待审批', badge: '5' },
      { path: '/admin/license/approved', label: '已审批' }
    ]
  },
  { path: '/admin/blockchain', label: '存证管理', icon: 'Link' },
  { path: '/admin/users', label: '用户管理', icon: 'User' }
])

// 面包屑
const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title
  }))
})

// 方法
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function toggleMobileMenu() {
  // 移动端菜单切换
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
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
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

// 监听全屏变化
function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
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
  width: 260px;
  background: linear-gradient(180deg, #065f46 0%, #047857 50%, #059669 100%);
  display: flex;
  flex-direction: column;
  transition: width $transition-base;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;

  &.collapsed {
    width: 80px;

    .nav-item {
      justify-content: center;
      padding: 0 16px;

      .nav-icon-wrapper {
        margin-right: 0;
      }
    }

    .sidebar-header {
      padding: 20px 16px;
    }

    .sidebar-footer {
      padding: 16px;
    }
  }
}

.sidebar-header {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;

  .logo-icon {
    width: 36px;
    height: 36px;
    flex-shrink: 0;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .logo-text {
    font-size: 16px;
    font-weight: $font-weight-semibold;
    color: white;
    white-space: nowrap;
  }
}

.collapse-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: $radius-md;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .el-icon {
    transition: transform $transition-base;

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

// 导航
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-section-title {
  font-size: 11px;
  font-weight: $font-weight-semibold;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 12px;
  margin-bottom: 8px;
  display: block;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 4px;
  border-radius: $radius-lg;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  cursor: pointer;
  transition: all $transition-fast;
  position: relative;

  .nav-icon-wrapper {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border-radius: $radius-md;
    margin-right: 12px;
    transition: all $transition-fast;
  }

  .nav-icon {
    font-size: 18px;
  }

  .nav-label {
    flex: 1;
    font-size: 14px;
    font-weight: $font-weight-medium;
  }

  .nav-badge {
    padding: 2px 8px;
    font-size: 11px;
    font-weight: $font-weight-semibold;
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border-radius: $radius-full;
  }

  .nav-arrow {
    font-size: 12px;
    transition: transform $transition-fast;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;

    .nav-icon-wrapper {
      background: rgba(255, 255, 255, 0.2);
    }
  }

  &.active {
    background: rgba(255, 255, 255, 0.2);
    color: white;

    .nav-icon-wrapper {
      background: white;

      .nav-icon {
        color: $primary-dark;
      }
    }
  }

  &.has-children.expanded {
    .nav-arrow {
      transform: rotate(180deg);
    }
  }
}

.sub-nav-list {
  list-style: none;
  padding: 4px 0 4px 44px;
  margin: 0;
}

.sub-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: $radius-md;
  font-size: 14px;
  transition: all $transition-fast;

  .sub-nav-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transition: all $transition-fast;
  }

  &:hover {
    color: white;

    .sub-nav-dot {
      background: white;
    }
  }

  &.active {
    color: white;

    .sub-nav-dot {
      background: white;
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
    }
  }

  .nav-badge {
    padding: 2px 8px;
    font-size: 11px;
    font-weight: $font-weight-semibold;
    background: $error-color;
    color: white;
    border-radius: $radius-full;
  }
}

// 用户卡片
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: $radius-lg;
  transition: all $transition-fast;

  &.compact {
    justify-content: center;
    padding: 8px;
  }

  .user-avatar {
    background: linear-gradient(135deg, $accent-light, $accent-dark);
    border: 2px solid rgba(255, 255, 255, 0.3);
    flex-shrink: 0;
  }

  .user-info {
    min-width: 0;
  }

  .user-name {
    font-size: 14px;
    font-weight: $font-weight-semibold;
    color: white;
    margin-bottom: 2px;
  }

  .user-role {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.7);
  }
}

// ========== 主内容区 ==========
.main-area {
  flex: 1;
  margin-left: 260px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left $transition-base;
}

.sidebar.collapsed ~ .main-area {
  margin-left: 80px;
}

// 顶栏
.topbar {
  height: 64px;
  background: white;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 50;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.mobile-menu-btn {
  display: none;
  width: 40px;
  height: 40px;
  border: none;
  background: $bg-secondary;
  border-radius: $radius-md;
  cursor: pointer;
  font-size: 20px;
  color: $text-secondary;
}

.breadcrumb {
  :deep(.el-breadcrumb__item) {
    .el-breadcrumb__inner {
      display: flex;
      align-items: center;
      gap: 4px;
      color: $text-secondary;
      font-weight: $font-weight-medium;

      &.is-link:hover {
        color: $primary-color;
      }
    }

    &:last-child .el-breadcrumb__inner {
      color: $text-primary;
    }
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-box {
  width: 240px;

  :deep(.el-input__wrapper) {
    background: $bg-primary;
    border-radius: $radius-full;
    box-shadow: none;
    border: 1px solid transparent;
    padding: 0 16px;

    &:hover, &:focus-within {
      border-color: $primary-color;
    }
  }
}

.icon-btn {
  background: $bg-primary !important;
  border: none !important;
  color: $text-secondary !important;

  &:hover {
    color: $primary-color !important;
  }
}

.notification-badge {
  :deep(.el-badge__content) {
    background: $error-color;
  }
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  border-radius: $radius-full;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: $bg-primary;
  }

  .user-avatar-small {
    background: $primary-gradient;
  }

  .user-name-small {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .dropdown-arrow {
    font-size: 12px;
    color: $text-secondary;
  }
}

// 页面内容
.page-content {
  flex: 1;
  overflow-y: auto;
}

// ========== 动画 ==========
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: all 0.3s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

// ========== 响应式 ==========
@media (max-width: 1200px) {
  .search-box {
    width: 200px;
  }
}

@media (max-width: 992px) {
  .sidebar {
    transform: translateX(-100%);

    &:not(.collapsed) {
      transform: translateX(0);
    }
  }

  .main-area {
    margin-left: 0 !important;
  }

  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

@media (max-width: 576px) {
  .topbar {
    padding: 0 16px;
  }

  .search-box {
    display: none;
  }

  .user-name-small {
    display: none;
  }
}
</style>
