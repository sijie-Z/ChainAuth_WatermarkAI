<template>
  <header class="site-header">
    <div class="site-header-inner">
      <router-link to="/home" class="site-brand" aria-label="返回首页">
        <span class="site-mark" aria-hidden="true">园</span>
        <span class="site-brand-text">
          <strong>苏州园林数字资产</strong>
          <small>链上确权与溯源</small>
        </span>
      </router-link>

      <nav class="site-nav" aria-label="站点导航">
        <router-link to="/home" class="site-nav-link" :class="{ active: route.path === '/home' }">首页</router-link>
        <router-link to="/assets" class="site-nav-link" :class="{ active: route.path.startsWith('/assets') }">资产档案</router-link>
        <router-link to="/trace" class="site-nav-link" :class="{ active: route.path === '/trace' }">溯源查询</router-link>
        <router-link v-if="isLoggedIn" to="/license/my" class="site-nav-link" :class="{ active: route.path === '/license/my' }">我的授权</router-link>
        <router-link to="/guide" class="site-nav-link" :class="{ active: route.path === '/guide' }">使用指南</router-link>
      </nav>

      <div class="site-actions">
        <router-link to="/guide" class="guide-link">
          <el-icon><Reading /></el-icon>
          <span>新手指南</span>
        </router-link>

        <template v-if="isLoggedIn">
          <el-dropdown trigger="click" @command="handleCommand">
            <button class="site-user" type="button">
              <span class="site-avatar">{{ username?.charAt(0)?.toUpperCase() }}</span>
              <span class="site-username">{{ username }}</span>
              <el-icon class="site-arrow"><ArrowDown /></el-icon>
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
                <el-dropdown-item command="admin" v-if="isAdmin">
                  <el-icon><DataLine /></el-icon>
                  管理后台
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <router-link to="/login" class="site-login">登录</router-link>
          <router-link to="/register" class="site-register">注册</router-link>
        </template>

        <button
          class="site-menu-toggle"
          type="button"
          :aria-expanded="mobileOpen"
          aria-label="打开导航菜单"
          @click="mobileOpen = !mobileOpen"
        >
          <el-icon><Menu /></el-icon>
        </button>
      </div>
    </div>

    <nav v-if="mobileOpen" class="site-mobile-nav" aria-label="移动端站点导航">
      <router-link to="/home" @click="mobileOpen = false">首页</router-link>
      <router-link to="/assets" @click="mobileOpen = false">资产档案</router-link>
      <router-link to="/trace" @click="mobileOpen = false">溯源查询</router-link>
      <router-link to="/guide" @click="mobileOpen = false">使用指南</router-link>
      <router-link v-if="isLoggedIn" to="/license/my" @click="mobileOpen = false">我的授权</router-link>
      <router-link v-if="isAdmin" to="/admin" @click="mobileOpen = false">管理后台</router-link>
      <router-link v-if="!isLoggedIn" to="/login" @click="mobileOpen = false">登录</router-link>
    </nav>
  </header>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  ArrowDown, DataLine, Menu, Reading, Setting, SwitchButton, User
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const mobileOpen = ref(false)

const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']
const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => ADMIN_ROLES.includes(userStore.userRole))
const username = computed(() => userStore.username)

watch(() => route.fullPath, () => {
  mobileOpen.value = false
})

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/home')
  } else if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'admin') {
    router.push('/admin')
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.site-header {
  position: sticky;
  top: 0;
  z-index: $z-fixed - 1;
  background: rgba(252, 253, 251, 0.98);
  border-bottom: 1px solid $border-light;
}

.site-header-inner {
  max-width: 1440px;
  margin: 0 auto;
  height: 62px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.site-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  color: $text-primary;

  .site-mark {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid $primary-color;
    border-radius: $radius-xs;
    color: $primary-dark;
    font-family: $font-display;
    font-size: 18px;
  }

  .site-brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1.25;

    strong {
      font-family: $font-display;
      font-size: 15px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    small {
      font-size: 10px;
      color: $text-placeholder;
      letter-spacing: 0.16em;
    }
  }
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 100%;
}

.site-nav-link {
  position: relative;
  padding: 8px 12px;
  font-size: 14px;
  color: $text-secondary;
  white-space: nowrap;

  &:hover {
    color: $primary-dark;
  }

  &.active {
    color: $primary-dark;
    font-weight: 500;

    &::after {
      content: '';
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 2px;
      height: 2px;
      background: $accent-color;
    }
  }
}

.site-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 14px;
}

.guide-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  font-size: 13px;
  color: $text-secondary;
  white-space: nowrap;

  &:hover {
    border-color: $primary-color;
    color: $primary-dark;
  }
}

.site-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  background: transparent;
  border: 1px solid $border-color;
  border-radius: $radius-full;
  cursor: pointer;

  &:hover {
    border-color: $border-dark;
  }
}

.site-avatar {
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

.site-username {
  max-width: 9em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: $text-primary;
}

.site-arrow {
  font-size: 11px;
  color: $text-placeholder;
}

.site-login {
  font-size: 14px;
  color: $text-secondary;

  &:hover {
    color: $primary-dark;
  }
}

.site-register {
  padding: 7px 16px;
  background: $primary-color;
  border: 1px solid $primary-dark;
  border-radius: $radius-sm;
  font-size: 14px;
  color: #fcfdfb;

  &:hover {
    background: $primary-dark;
    color: #fcfdfb;
  }
}

.site-menu-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: transparent;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  color: $text-secondary;
  cursor: pointer;
}

.site-mobile-nav {
  display: none;
  padding: 8px 20px 14px;
  border-top: 1px solid $border-light;
  background: $bg-card;

  a {
    display: block;
    padding: 10px 4px;
    font-size: 14px;
    color: $text-secondary;
    border-bottom: 1px solid $border-light;

    &:last-child {
      border-bottom: none;
    }
  }
}

@media (max-width: 900px) {
  .site-header-inner {
    padding: 0 16px;
    gap: 12px;
  }

  .site-nav,
  .guide-link {
    display: none;
  }

  .site-menu-toggle {
    display: inline-flex;
  }

  .site-mobile-nav {
    display: block;
  }

  .site-username {
    display: none;
  }
}

@media (max-width: 480px) {
  .site-brand-text small {
    display: none;
  }

  .site-register {
    padding: 6px 12px;
  }
}
</style>
