<template>
  <div class="profile-page">
    <header class="page-bar">
      <router-link to="/home" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回首页
      </router-link>
      <h1 class="page-title">个人中心</h1>
    </header>

    <div class="profile-container">
      <!-- 左侧：用户信息卡片 -->
      <div class="profile-sidebar">
        <div class="user-card">
          <div class="user-card-header">
            <div class="avatar-section">
              <el-avatar :size="80" class="profile-avatar">
                {{ username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <div class="avatar-badge">
                <el-icon><Check /></el-icon>
              </div>
            </div>
            <h2 class="user-display-name">{{ username || '用户' }}</h2>
            <span class="user-role-badge">{{ roleLabel }}</span>
          </div>

          <div class="user-card-body">
            <div class="info-item">
              <el-icon class="info-icon"><User /></el-icon>
              <div class="info-content">
                <span class="info-label">用户名</span>
                <span class="info-value">{{ username || '-' }}</span>
              </div>
            </div>
            <div class="info-item">
              <el-icon class="info-icon"><Stamp /></el-icon>
              <div class="info-content">
                <span class="info-label">角色</span>
                <span class="info-value">{{ roleLabel }}</span>
              </div>
            </div>
            <div class="info-item">
              <el-icon class="info-icon"><Calendar /></el-icon>
              <div class="info-content">
                <span class="info-label">注册时间</span>
                <span class="info-value">{{ formatDate(user?.created_at) || '-' }}</span>
              </div>
            </div>
            <div class="info-item">
              <el-icon class="info-icon"><Clock /></el-icon>
              <div class="info-content">
                <span class="info-label">最近活跃</span>
                <span class="info-value">{{ formatDate(user?.last_login_at) || '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：内容区 -->
      <div class="profile-main">
        <!-- 统计卡片（仅展示有真实接口的统计） -->
        <div class="stats-grid">
          <div class="stat-card" role="button" tabindex="0" @click="$router.push('/my-assets')" @keydown.enter="$router.push('/my-assets')">
            <div class="stat-icon">
              <el-icon><Picture /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.assets ?? '-' }}</span>
              <span class="stat-label">我的资产</span>
            </div>
          </div>
          <div class="stat-card" role="button" tabindex="0" @click="$router.push('/license/my')" @keydown.enter="$router.push('/license/my')">
            <div class="stat-icon accent">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.licenses ?? '-' }}</span>
              <span class="stat-label">我的授权</span>
            </div>
          </div>
        </div>

        <!-- 最近活动 -->
        <el-card class="activity-card">
          <template #header>
            <div class="card-header">
              <span>最近活动</span>
              <el-button text type="primary" @click="loadActivities">刷新</el-button>
            </div>
          </template>

          <div v-if="activities.length === 0 && !loading" class="empty-state">
            <el-empty description="暂无活动记录" :image-size="120" />
          </div>

          <div v-else v-loading="loading" class="activity-list">
            <div v-for="item in activities" :key="item.id" class="activity-item">
              <div class="activity-dot" :style="{ background: getActivityColor(item.type) }"></div>
              <div class="activity-content">
                <p class="activity-desc">{{ item.description }}</p>
                <span class="activity-time">{{ formatDate(item.created_at) }}</span>
              </div>
              <el-tag size="small" :type="getActivityTagType(item.type)">
                {{ getActivityTypeLabel(item.type) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { licenseApi } from '@/api/modules'
import {
  User, Stamp, Calendar, Clock, Picture, Document, Check, ArrowLeft
} from '@element-plus/icons-vue'

const userStore = useUserStore()
const user = computed(() => userStore.user)
const username = computed(() => userStore.username)
const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    asset_admin: '资产管理员',
    license_admin: '授权管理员',
    adm1: '一级审批员',
    adm2: '二级审批员',
    user: '普通用户'
  }
  return labels[userStore.userRole] || '用户'
})

const loading = ref(false)
const activities = ref([])
const stats = ref({
  assets: null,
  licenses: null
})

async function loadStats() {
  const [assetsResult, licensesResult] = await Promise.allSettled([
    api.get('/assets/my', { params: { page: 1, per_page: 1 } }),
    licenseApi.getMyLicenses({ page: 1, per_page: 1 })
  ])

  if (assetsResult.status === 'fulfilled' && assetsResult.value.data?.code === 200) {
    stats.value.assets = assetsResult.value.data.data?.total ?? 0
  } else if (assetsResult.status === 'rejected') {
    console.error('加载资产统计失败:', assetsResult.reason)
  }

  if (licensesResult.status === 'fulfilled' && licensesResult.value.data?.code === 200) {
    stats.value.licenses = licensesResult.value.data.data?.total ?? 0
  } else if (licensesResult.status === 'rejected') {
    console.error('加载授权统计失败:', licensesResult.reason)
  }
}

async function loadActivities() {
  loading.value = true
  try {
    const response = await licenseApi.getMyLicenses({ page: 1, per_page: 5 })
    if (response.data.code === 200) {
      const items = response.data.data?.items || []
      activities.value = items.map(item => ({
        id: item.id,
        type: 'license',
        description: `授权申请: ${item.asset_title || '未知资产'}`,
        created_at: item.created_at
      }))
    }
  } catch {
    // 加载失败保持空状态
  } finally {
    loading.value = false
  }
}

function getActivityColor(type) {
  const map = { license: '#4c6e8a', asset: '#2f6b5a', watermark: '#b07a2a', blockchain: '#6d5b7a' }
  return map[type] || '#5b675f'
}

function getActivityTagType(type) {
  const map = { license: 'primary', asset: 'success', watermark: 'warning', blockchain: '' }
  return map[type] || 'info'
}

function getActivityTypeLabel(type) {
  const map = { license: '授权', asset: '资产', watermark: '水印', blockchain: '存证' }
  return map[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadStats()
  loadActivities()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.profile-page {
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
  background: $bg-primary;
  padding: $spacing-2xl $spacing-3xl;
}

// ========== 页眉 ==========
.page-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-xl;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  letter-spacing: 0.02em;
  color: $text-primary;
}

.profile-container {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: $spacing-2xl;
}

.profile-sidebar {
  position: sticky;
  top: 88px;
  align-self: start;
}

.user-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.user-card-header {
  background: $bg-card;
  padding: $spacing-3xl $spacing-xl $spacing-xl;
  text-align: center;
  border-bottom: 1px solid $border-light;
}

.avatar-section {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;

  .profile-avatar {
    background: $primary-color;
    border: 1px solid $primary-dark;
    color: $bg-card;
    font-family: $font-display;
    font-size: $font-size-3xl;
    font-weight: $font-weight-semibold;
  }

  .avatar-badge {
    position: absolute;
    bottom: 2px;
    right: 2px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: $primary-dark;
    border: 2px solid $bg-card;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $bg-card;
    font-size: 12px;
  }
}

.user-display-name {
  margin: 0 0 $spacing-sm;
  font-family: $font-display;
  font-size: $font-size-xl;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.user-role-badge {
  display: inline-block;
  padding: 2px 10px;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  color: $text-secondary;
  font-size: $font-size-xs;
  letter-spacing: 0.08em;
}

.user-card-body {
  padding: $spacing-lg $spacing-xl;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }

  .info-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $bg-secondary;
    border-radius: $radius-md;
    color: $text-secondary;
    font-size: 18px;
    flex-shrink: 0;
  }

  .info-content {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .info-label {
      font-size: $font-size-xs;
      color: $text-placeholder;
    }

    .info-value {
      font-size: $font-size-sm;
      color: $text-primary;
      font-weight: $font-weight-medium;
    }
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-lg;
  margin-bottom: $spacing-2xl;
}

.stat-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-xl;
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  box-shadow: $shadow-sm;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &:hover {
    border-color: $border-color;
    box-shadow: $shadow-sm;
  }

  .stat-icon {
    width: 44px;
    height: 44px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    margin-bottom: 0;
    background: $bg-secondary;
    color: $primary-color;

    &.accent {
      color: $accent-color;
    }
  }

  .stat-info {
    display: flex;
    flex-direction: column;

    .stat-value {
      font-family: $font-display;
      font-size: $font-size-3xl;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      line-height: 1.1;
      margin-bottom: 0;
      font-variant-numeric: tabular-nums;
    }

    .stat-label {
      font-size: $font-size-xs;
      color: $text-secondary;
      margin-top: $spacing-xs;
      letter-spacing: 0.06em;
    }
  }
}

.activity-card {
  :deep(.el-card__header) {
    padding: $spacing-lg $spacing-xl;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-card__body) {
    padding: $spacing-xl;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: $font-display;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.empty-state {
  padding: 40px 0;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }
}

.activity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  min-width: 0;

  .activity-desc {
    margin: 0;
    font-size: $font-size-sm;
    color: $text-primary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .activity-time {
    font-size: $font-size-xs;
    color: $text-placeholder;
  }
}

@media (max-width: $breakpoint-lg) {
  .profile-container {
    grid-template-columns: 1fr;
  }

  .profile-sidebar {
    position: static;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: $breakpoint-md) {
  .profile-page {
    padding: $spacing-lg;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .activity-item {
    flex-wrap: wrap;
  }
}
</style>
