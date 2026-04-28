<template>
  <div class="profile-page">
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
                <span class="info-value">{{ formatDate(user?.last_login) || '刚刚' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：内容区 -->
      <div class="profile-main">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon" style="background: rgba(16, 185, 129, 0.1); color: #10b981;">
              <el-icon><Picture /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.assets }}</span>
              <span class="stat-label">拥有资产</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="background: rgba(59, 130, 246, 0.1); color: #3b82f6;">
              <el-icon><Stamp /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.watermarks }}</span>
              <span class="stat-label">水印记录</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b;">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.licenses }}</span>
              <span class="stat-label">授权申请</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon" style="background: rgba(139, 92, 246, 0.1); color: #8b5cf6;">
              <el-icon><Link /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ stats.blockchain }}</span>
              <span class="stat-label">链上存证</span>
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
import { licenseApi } from '@/api/modules'
import { ElMessage } from 'element-plus'
import {
  User, Stamp, Calendar, Clock, Picture, Document, Link, Check
} from '@element-plus/icons-vue'

const userStore = useUserStore()
const user = computed(() => userStore.user)
const username = computed(() => userStore.username)
const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    adm1: '资产管理员',
    adm2: '授权管理员',
    adm3: '审核员',
    user: '普通用户'
  }
  return labels[userStore.userRole] || '用户'
})

const loading = ref(false)
const activities = ref([])
const stats = ref({
  assets: 0,
  watermarks: 0,
  licenses: 0,
  blockchain: 0
})

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
  const map = { license: '#3b82f6', asset: '#10b981', watermark: '#f59e0b', blockchain: '#8b5cf6' }
  return map[type] || '#6b7280'
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
  loadActivities()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.profile-page {
  min-height: 100vh;
  background: $bg-primary;
  padding: 32px;
}

.profile-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 24px;
}

.profile-sidebar {
  position: sticky;
  top: 88px;
  align-self: start;
}

.user-card {
  background: white;
  border-radius: $radius-xl;
  box-shadow: $shadow-card;
  overflow: hidden;
}

.user-card-header {
  background: $primary-gradient;
  padding: 32px 24px;
  text-align: center;
  color: white;
}

.avatar-section {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;

  .profile-avatar {
    background: rgba(255, 255, 255, 0.2);
    border: 3px solid rgba(255, 255, 255, 0.4);
    font-size: 32px;
    font-weight: $font-weight-bold;
  }

  .avatar-badge {
    position: absolute;
    bottom: 2px;
    right: 2px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: $success-color;
    border: 2px solid white;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
  }
}

.user-display-name {
  margin: 0 0 8px;
  font-size: $font-size-xl;
  font-weight: $font-weight-semibold;
}

.user-role-badge {
  display: inline-block;
  padding: 4px 14px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: $radius-full;
  font-size: $font-size-xs;
}

.user-card-body {
  padding: 20px 24px;
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
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: $radius-lg;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: $shadow-card;
  transition: all $transition-base;

  &:hover {
    box-shadow: $shadow-card-hover;
    transform: translateY(-2px);
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
  }

  .stat-info {
    display: flex;
    flex-direction: column;

    .stat-value {
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      line-height: 1;
    }

    .stat-label {
      font-size: $font-size-xs;
      color: $text-secondary;
      margin-top: 4px;
    }
  }
}

.activity-card {
  border-radius: $radius-xl;
  box-shadow: $shadow-card;

  :deep(.el-card__header) {
    padding: 20px 24px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
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

@media (max-width: $breakpoint-sm) {
  .profile-page {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
