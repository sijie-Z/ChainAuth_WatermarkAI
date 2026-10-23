<template>
  <div class="dashboard-page">
    <!-- 欢迎区域 -->
    <div class="welcome-section">
      <div class="welcome-content">
        <div class="welcome-text">
          <h1 class="welcome-title">
            <span class="greeting">{{ getGreeting() }}，</span>
            <span class="username">{{ username || '管理员' }}</span>
          </h1>
          <p class="welcome-subtitle">欢迎回到苏州园林数字资产平台管理后台</p>
        </div>
        <div v-if="canManageAssets" class="welcome-actions">
          <el-button type="primary" class="btn-action" @click="$router.push('/admin/assets')">
            <el-icon><Upload /></el-icon>
            管理资产
          </el-button>
          <el-button
            v-if="canProcessAssets"
            class="btn-action-secondary"
            @click="$router.push('/admin/watermark')"
          >
            <el-icon><Stamp /></el-icon>
            水印处理
          </el-button>
          <el-button class="btn-action-secondary" @click="$router.push('/guide')">
            <el-icon><Reading /></el-icon>
            使用指南
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-skeleton v-if="loading" animated :rows="1" style="margin-bottom: 32px">
      <template #template>
        <div class="stats-grid">
          <el-skeleton-item v-for="i in 4" :key="i" variant="rect" style="height: 160px; border-radius: 16px" />
        </div>
      </template>
    </el-skeleton>
    <div v-else class="stats-grid">
      <div
        class="stat-card"
        v-for="stat in statCards"
        :key="stat.key"
      >
        <div class="stat-card-header">
          <div class="stat-icon-wrapper" :style="{ background: stat.gradient }">
            <el-icon class="stat-icon"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'" v-if="stat.trend">
            <el-icon><component :is="stat.trend > 0 ? ArrowUp : ArrowDown" /></el-icon>
            <span>{{ Math.abs(stat.trend) }}%</span>
          </div>
        </div>
        <div class="stat-card-body">
          <div class="stat-value">
            <span class="value-number">{{ animatedValues[stat.key] }}</span>
            <span class="value-suffix" v-if="stat.suffix">{{ stat.suffix }}</span>
          </div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-card-footer" v-if="stat.showProgress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: stat.progress + '%', background: stat.gradient }"></div>
          </div>
          <span class="progress-text">{{ stat.progress }}% {{ stat.progressLabel }}</span>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧：图表 -->
      <div class="content-left">
        <!-- 资产类型分布 -->
        <div class="chart-card">
          <div class="card-header">
            <h3 class="card-title">资产类型分布</h3>
            <el-radio-group v-model="chartType" size="small">
              <el-radio-button value="week">本周</el-radio-button>
              <el-radio-button value="month">本月</el-radio-button>
            </el-radio-group>
          </div>
          <el-skeleton v-if="loading" animated :rows="1" style="padding: 20px">
            <template #template>
              <el-skeleton-item variant="rect" style="height: 300px; border-radius: 12px" />
            </template>
          </el-skeleton>
          <div v-else class="chart-container" ref="assetChartRef"></div>
        </div>

        <!-- 水印处理趋势 -->
        <div class="chart-card">
          <div class="card-header">
            <h3 class="card-title">水印处理趋势</h3>
            <el-tag size="small" type="success">最近 7 天</el-tag>
          </div>
          <el-skeleton v-if="loading" animated :rows="1" style="padding: 20px">
            <template #template>
              <el-skeleton-item variant="rect" style="height: 300px; border-radius: 12px" />
            </template>
          </el-skeleton>
          <div v-else class="chart-container" ref="watermarkChartRef"></div>
        </div>
      </div>

      <!-- 右侧：列表 -->
      <div class="content-right">
        <!-- 快捷入口 -->
        <div class="quick-actions-card">
          <h3 class="card-title">快捷入口</h3>
          <div class="quick-actions-grid">
            <div class="quick-action-item" v-for="action in quickActions" :key="action.path" @click="$router.push(action.path)">
              <div class="action-icon" :style="{ background: action.gradient }">
                <el-icon><component :is="action.icon" /></el-icon>
              </div>
              <span class="action-label">{{ action.label }}</span>
            </div>
          </div>
        </div>

        <!-- 系统能力状态 -->
        <div class="system-card">
          <div class="card-header">
            <h3 class="card-title">系统能力</h3>
            <el-button link type="primary" size="small" @click="loadSystemStatus">刷新</el-button>
          </div>
          <el-skeleton v-if="systemLoading" animated :rows="3" style="padding: 12px 16px" />
          <div v-else class="system-list">
            <div v-for="item in systemItems" :key="item.key" class="system-row">
              <div class="system-text">
                <strong>{{ item.name }}</strong>
                <span>{{ item.description }}</span>
              </div>
              <el-tag size="small" :type="item.type" effect="plain">{{ item.label }}</el-tag>
            </div>
            <p class="system-note">演示环境不会把未启用能力伪装成可用状态。</p>
          </div>
        </div>

        <!-- 最近活动 -->
        <div class="activity-card">
          <div class="card-header">
            <h3 class="card-title">最近活动</h3>
          </div>
          <el-skeleton v-if="loading" animated :rows="4" style="padding: 16px" />
          <div v-else class="activity-list">
            <div v-if="recentActivities.length === 0" class="empty-mini">
              <el-icon><Timer /></el-icon>
              <span>暂无活动</span>
            </div>
            <div class="activity-item" v-for="activity in recentActivities" :key="activity.id">
              <div class="activity-avatar" :style="{ background: activity.color }">
                <el-icon><component :is="activity.icon" /></el-icon>
              </div>
              <div class="activity-content">
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-desc">{{ activity.description }}</div>
              </div>
              <div class="activity-time">{{ activity.time }}</div>
            </div>
          </div>
        </div>

        <!-- 待办事项 -->
        <div class="todo-card">
          <div class="card-header">
            <h3 class="card-title">待办事项</h3>
            <el-badge :value="pendingCount" type="danger" />
          </div>
          <el-skeleton v-if="loading" animated :rows="2" style="padding: 16px" />
          <div v-else class="todo-list">
            <div v-if="todoList.length === 0" class="empty-mini">
              <el-icon><CircleCheck /></el-icon>
              <span>暂无待办</span>
            </div>
            <div class="todo-item" v-for="todo in todoList" :key="todo.id">
              <div class="todo-priority" :class="todo.priority"></div>
              <div class="todo-content">
                <div class="todo-title">{{ todo.title }}</div>
                <div class="todo-meta">
                  <span class="todo-deadline">
                    <el-icon><Clock /></el-icon>
                    {{ todo.deadline }}
                  </span>
                </div>
              </div>
              <el-button type="primary" size="small" round @click="goToPendingLicenses">处理</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部表格 -->
    <div class="bottom-section">
      <div class="table-card">
        <div class="card-header">
          <h3 class="card-title">最近上传资产</h3>
          <el-button type="primary" link @click="$router.push('/admin/assets')">查看全部 →</el-button>
        </div>
        <el-skeleton v-if="loading" animated :rows="4" style="padding: 16px" />
        <el-table v-else :data="recentAssets" style="width: 100%" class="modern-table">
          <el-table-column label="资产信息" min-width="280">
            <template #default="{ row }">
              <div class="asset-info">
                <div class="asset-thumb">
                  <img :src="getThumbnail(row)" alt="" loading="lazy" @error="onThumbnailError($event, row)" />
                </div>
                <div class="asset-meta">
                  <div class="asset-code">{{ row.asset_code }}</div>
                  <div class="asset-title">{{ row.title }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getTypeTag(row.type)" size="small" effect="light">
                {{ getTypeName(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="水印状态" width="120">
            <template #default="{ row }">
              <div class="status-cell">
                <span class="status-dot" :class="row.watermark_status"></span>
                <span>{{ getWatermarkStatus(row.watermark_status) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="存证状态" width="120">
            <template #default="{ row }">
              <div class="status-cell">
                <span class="status-dot" :class="row.chain_status"></span>
                <span>{{ getChainStatus(row.chain_status) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" width="160" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="viewAsset(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick, shallowRef } from 'vue'
import { parseBackendDate } from '@/utils'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { assetApi, licenseApi, systemApi } from '@/api/modules'
import {
  Picture, Stamp, Link, Document, Upload, Clock, DataLine,
  ArrowUp, ArrowDown, User, Reading,
  CircleCheck, Timer, Download, Place, Warning, Bell
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const userStore = useUserStore()
const router = useRouter()

const username = computed(() => userStore.username)
const loading = ref(false)

// 图表引用
const assetChartRef = ref(null)
const watermarkChartRef = ref(null)
let assetChart = null
let watermarkChart = null

// 图表类型
const chartType = ref('week')

// 统计卡片配置（label/icon/gradient/suffix 为静态，value 从 API 填充）
const statCardDefs = [
  { key: 'totalAssets', label: '资产总数', icon: Picture, gradient: 'linear-gradient(135deg, #2f6b5a 0%, #1c5145 100%)', suffix: '个' },
  { key: 'watermarkedAssets', label: '已嵌入水印', icon: Stamp, gradient: 'linear-gradient(135deg, #4c6e8a 0%, #34506a 100%)', suffix: '个' },
  { key: 'chainedAssets', label: '链上存证', icon: Link, gradient: 'linear-gradient(135deg, #6d5b7a 0%, #584765 100%)', suffix: '个' },
  { key: 'pendingLicenses', label: '待审批授权', icon: Document, gradient: 'linear-gradient(135deg, #b07a2a 0%, #8f6322 100%)', suffix: '个' }
]

const statCards = shallowRef(
  statCardDefs.map(def => ({ ...def, value: 0, trend: null, progress: 0 }))
)

// 动画数值
const animatedValues = reactive({
  totalAssets: 0,
  watermarkedAssets: 0,
  chainedAssets: 0,
  pendingLicenses: 0
})

// API 数据缓存（用于图表切换时重新绘制）
let rawStats = null

// 管理后台角色集合（与后端角色枚举一致）
const ASSET_ROLES = ['admin', 'asset_admin', 'adm1', 'adm2']
// 后端审批角色：adm1/asset_admin 参与一级审批，adm2/license_admin 参与二级审批
const LICENSE_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']

const currentRole = computed(() => userStore.userRole)
const canManageAssets = computed(() => ASSET_ROLES.includes(currentRole.value))
const canProcessAssets = computed(() => ['admin', 'asset_admin'].includes(currentRole.value))

// 快捷操作（按角色过滤）
const quickActionDefs = [
  { label: '资产管理', icon: Picture, path: '/admin/assets', gradient: 'linear-gradient(135deg, #2f6b5a, #1c5145)', roles: ASSET_ROLES },
  { label: '水印处理', icon: Stamp, path: '/admin/watermark', gradient: 'linear-gradient(135deg, #4c6e8a, #34506a)', roles: ['admin', 'asset_admin'] },
  { label: '存证管理', icon: Link, path: '/admin/blockchain', gradient: 'linear-gradient(135deg, #6d5b7a, #584765)', roles: ['admin', 'asset_admin'] },
  { label: '授权审批', icon: Document, path: '/admin/license/pending', gradient: 'linear-gradient(135deg, #b07a2a, #8f6322)', roles: LICENSE_ROLES },
  { label: '使用报表', icon: DataLine, path: '/admin/license/usage', gradient: 'linear-gradient(135deg, #2f6b5a, #1c5145)', roles: LICENSE_ROLES },
  { label: '侵权线索', icon: Warning, path: '/admin/infringements', gradient: 'linear-gradient(135deg, #a6402f, #7c2d21)', roles: LICENSE_ROLES },
  { label: '园林档案', icon: Place, path: '/admin/gardens', gradient: 'linear-gradient(135deg, #4a7c59, #365c42)', roles: ['admin', 'asset_admin'] },
  { label: '下载台账', icon: Download, path: '/admin/downloads', gradient: 'linear-gradient(135deg, #5b7f8a, #45616a)', roles: LICENSE_ROLES },
  { label: '用户管理', icon: User, path: '/admin/users', gradient: 'linear-gradient(135deg, #5b675f, #414b43)', roles: ['admin'] },
  { label: '通知渠道', icon: Bell, path: '/admin/notifications', gradient: 'linear-gradient(135deg, #4c6e8a, #34506a)', roles: ['admin'] }
]

const quickActions = computed(() => {
  return quickActionDefs.filter(action => action.roles.includes(currentRole.value))
})

// 最近活动
const recentActivities = shallowRef([])

// 待办事项（从待审批授权映射）
const todoList = ref([])

const pendingCount = computed(() => todoList.value.length)

const systemStatus = ref(null)
const systemLoading = ref(false)
const systemItems = computed(() => {
  const data = systemStatus.value
  if (!data) return []
  return [
    {
      key: 'blockchain',
      name: '区块链存证',
      label: data.blockchain?.label || '未知',
      description: data.blockchain?.description || '',
      type: data.blockchain?.enabled ? 'success' : 'warning'
    },
    {
      key: 'ai',
      name: 'AI 辅助',
      label: data.ai?.label || '未知',
      description: data.ai?.description || '',
      type: data.ai?.enabled ? 'success' : 'info'
    },
    {
      key: 'redis',
      name: '缓存与限流',
      label: data.redis?.label || '未知',
      description: data.redis?.description || '',
      type: data.redis?.enabled ? 'success' : 'warning'
    },
    {
      key: 'scheduler',
      name: '定时任务',
      label: data.scheduler?.label || '未知',
      description: data.scheduler?.description || '',
      type: data.scheduler?.enabled ? 'success' : 'info'
    },
    {
      key: 'tasks',
      name: '异步任务',
      label: data.tasks?.label || '未知',
      description: data.tasks
        ? `排队 ${data.tasks.counts?.queued || 0} · 处理中 ${data.tasks.counts?.running || 0} · 失败 ${data.tasks.counts?.failed || 0}`
        : '',
      type: (data.tasks?.counts?.failed || 0) > 0
        ? 'danger'
        : (data.tasks?.enabled ? 'success' : 'warning')
    },
    {
      key: 'notifications',
      name: '通知渠道',
      label: data.notifications?.mail_configured
        ? '邮件 + 站内实时'
        : (data.notifications?.sse_enabled ? '仅站内实时' : '通知未启用'),
      description: data.notifications
        ? `邮件待发 ${data.notifications.deliveries?.pending || 0} · 已发 ${data.notifications.deliveries?.sent || 0} · 失败 ${data.notifications.deliveries?.failed || 0}`
        : '',
      type: (data.notifications?.deliveries?.failed || 0) > 0
        ? 'danger'
        : (data.notifications?.mail_configured ? 'success' : 'info')
    }
  ]
})

async function loadSystemStatus() {
  systemLoading.value = true
  try {
    const response = await systemApi.getStatus()
    if (response.data?.code === 200) {
      systemStatus.value = response.data.data
    }
  } catch {
    // 状态读取失败不影响仪表盘其他区块
  } finally {
    systemLoading.value = false
  }
}

// 最近资产
const recentAssets = ref([])

// 加载仪表盘数据
async function loadDashboardData() {
  loading.value = true
  try {
    // 使用 allSettled：单个接口失败（如权限不足返回 403）不影响其余模块渲染
    const [statsSettled, pendingLicensesSettled] = await Promise.allSettled([
      assetApi.getDetail('stats'),
      licenseApi.getPending()
    ])

    let stats = null
    if (statsSettled.status === 'fulfilled' && statsSettled.value.data?.code === 200) {
      stats = statsSettled.value.data.data
    } else if (statsSettled.status === 'rejected') {
      console.error('加载统计数据失败:', statsSettled.reason)
    }
    rawStats = stats

    // 统计卡片
    if (stats) {
      const total = stats.total || 0
      const watermarked = stats.watermarked || 0
      const chained = stats.chained || 0
      const pendingLicenses = stats.pending_licenses || 0

      statCards.value = statCardDefs.map(def => {
        let value = 0
        let progress = 0
        let showProgress = true
        let progressLabel = '水印覆盖率'
        if (def.key === 'totalAssets') {
          value = total
          progress = total > 0 ? Math.round((watermarked / total) * 100) : 0
        }
        if (def.key === 'watermarkedAssets') {
          value = watermarked
          progress = total > 0 ? Math.round((watermarked / total) * 100) : 0
        }
        if (def.key === 'chainedAssets') {
          value = chained
          progress = total > 0 ? Math.round((chained / total) * 100) : 0
          progressLabel = '上链覆盖率'
        }
        if (def.key === 'pendingLicenses') {
          value = pendingLicenses
          showProgress = false
        }
        return { ...def, value, trend: null, progress, showProgress, progressLabel }
      })
    }

    // 最近活动
    if (stats?.recent_activities?.length) {
      const actionIcons = { upload: Picture, embed: Stamp, extract: Stamp, register: Link, approve: Document, login: User }
      const actionColors = { upload: '#2f6b5a', embed: '#4c6e8a', extract: '#4c6e8a', register: '#6d5b7a', approve: '#b07a2a', login: '#5b675f' }
      const actionNames = {
        upload: '上传资产',
        embed: '嵌入水印',
        watermark_embed: '嵌入水印',
        extract: '提取水印',
        register: '上链存证',
        approve: '审批授权',
        reject: '驳回申请',
        license_apply: '提交授权申请',
        update: '更新资产',
        delete: '删除资产',
        login: '登录'
      }
      recentActivities.value = stats.recent_activities.slice(0, 8).map((a, i) => ({
        id: a.id || i,
        icon: actionIcons[a.action] || CircleCheck,
        title: actionNames[a.action] || a.module || '操作',
        description: a.description || '',
        time: formatTimeAgo(a.created_at),
        color: actionColors[a.action] || '#5b675f'
      }))
    }

    // 待办事项（来自待审批授权）
    let pendingApps = []
    if (pendingLicensesSettled.status === 'fulfilled' && pendingLicensesSettled.value.data?.code === 200) {
      const data = pendingLicensesSettled.value.data.data
      pendingApps = data?.items || data || []
    } else if (pendingLicensesSettled.status === 'rejected') {
      console.error('加载待审批授权失败:', pendingLicensesSettled.reason)
    }
    if (Array.isArray(pendingApps) && pendingApps.length > 0) {
      todoList.value = pendingApps.slice(0, 5).map(app => ({
        id: app.id,
        title: `审批授权申请 #${app.application_code || app.id}`,
        deadline: formatDate(app.created_at),
        priority: 'high'
      }))
    } else {
      todoList.value = []
    }

    // 最近资产
    if (stats?.recent?.length) {
      recentAssets.value = stats.recent.slice(0, 5).map(a => ({
        ...a,
        type: a.asset_type || a.type
      }))
    }

    // 运行动画和图表
    animateNumbers()
  } catch (e) {
    console.error('加载仪表盘数据失败:', e)
  } finally {
    loading.value = false
    // 图表容器在 loading 结束后才渲染，必须等 DOM 更新后再初始化
    nextTick(() => initCharts())
  }
}

// 工具函数
function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 17) return '下午好'
  if (hour < 19) return '傍晚好'
  return '晚上好'
}

function getThumbnail(row) {
  return row.id ? `/api/assets/${row.id}/thumbnail?size=card&v=2` : getDefaultThumb(row.type)
}

function onThumbnailError(event, row) {
  const img = event?.target
  if (!img || img.dataset.fallbackApplied) return
  img.dataset.fallbackApplied = '1'
  img.src = getDefaultThumb(row.type)
}

function getDefaultThumb(type) {
  const colors = { image: '#2f6b5a', vector: '#4c6e8a', model: '#6d5b7a', document: '#b07a2a', video: '#a6402f' }
  const color = colors[type] || '#5b675f'
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="60" height="60"%3E%3Crect fill="%23${color.replace('#', '')}" width="60" height="60" rx="8"/%3E%3Ctext x="30" y="36" text-anchor="middle" fill="white" font-size="14"%3E${(type || 'FILE').substring(0, 3).toUpperCase()}%3C/text%3E%3C/svg%3E`
}

function getTypeName(type) {
  const names = { image: '图片', vector: '矢量', model: '模型', document: '文档', video: '视频' }
  return names[type] || type
}

function getTypeTag(type) {
  const tags = { image: 'success', vector: 'primary', model: 'warning', document: 'info', video: 'danger' }
  return tags[type] || ''
}

function getWatermarkStatus(status) {
  const statusMap = { none: '未嵌入', pending: '处理中', embedded: '已嵌入', verified: '已验证', failed: '失败' }
  return statusMap[status] || '未知'
}

function getChainStatus(status) {
  const statusMap = { none: '未存证', pending: '处理中', confirmed: '已存证', failed: '存证失败' }
  return statusMap[status] || '未知'
}

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return formatDate(dateStr)
}

// 数字直接呈现，避免动画期间显示与实际不一致的中间值
function animateNumbers() {
  statCards.value.forEach(stat => {
    animatedValues[stat.key] = stat.value
  })
}

// 按本周/本月构建资产类型分布数据
function buildPieData() {
  const byType = (chartType.value === 'month'
    ? (rawStats?.by_type_month || rawStats?.by_type)
    : (rawStats?.by_type_week || rawStats?.by_type))
  if (!byType) return []

  const typeColors = { image: '#2f6b5a', vector: '#7397ab', model: '#c1925b', document: '#789262', video: '#a6402f' }
  const typeNames = { image: '图片', vector: '矢量', model: '模型', document: '文档', video: '视频' }
  return Object.entries(byType)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ value: v, name: typeNames[k] || k, itemStyle: { color: typeColors[k] || '#5b675f' } }))
}

// 本周取最近 7 条趋势，本月取最近 30 条
function buildTrendData() {
  const trends = rawStats?.watermark_trends || []
  if (!Array.isArray(trends) || trends.length === 0) return []
  return trends.slice(chartType.value === 'week' ? -7 : -30)
}

// 初始化图表
function initCharts() {
  // 资产类型分布图
  if (assetChartRef.value) {
    if (assetChart) assetChart.dispose()
    assetChart = echarts.init(assetChartRef.value)
    const pieData = buildPieData()
    const pieTotal = pieData.reduce((sum, item) => sum + (item.value || 0), 0)
    const defaultPieData = [
      { value: 0, name: '暂无数据', itemStyle: { color: '#d8e1da' } }
    ]
    const option = {
      graphic: pieTotal > 0
        ? [
            {
              type: 'text',
              left: 'center',
              top: '39%',
              silent: true,
              style: {
                text: String(pieTotal),
                fill: '#17201c',
                fontSize: 26,
                fontWeight: 600,
                textAlign: 'center'
              }
            },
            {
              type: 'text',
              left: 'center',
              top: '49%',
              silent: true,
              style: {
                text: '件资产',
                fill: '#5b675f',
                fontSize: 12,
                textAlign: 'center'
              }
            }
          ]
        : [],
      tooltip: {
        trigger: 'item',
        backgroundColor: '#fcfdfb',
        borderColor: '#d8e1da',
        borderWidth: 1,
        textStyle: { color: '#17201c', fontSize: 13 },
        extraCssText: 'box-shadow:0 4px 12px rgba(18,28,23,.08);border-radius:6px;'
      },
      legend: {
        bottom: 0,
        left: 'center',
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#5b675f', fontSize: 12 }
      },
      series: [{
        name: '资产类型',
        type: 'pie',
        radius: ['48%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 2, borderColor: '#fcfdfb', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 600, color: '#17201c' } },
        labelLine: { show: false },
        data: pieData.length > 0 ? pieData : defaultPieData
      }]
    }
    assetChart.setOption(option)
  }

  // 水印处理趋势图
  if (watermarkChartRef.value) {
    if (watermarkChart) watermarkChart.dispose()
    watermarkChart = echarts.init(watermarkChartRef.value)

    let dates = []
    let counts = []
    const trendData = buildTrendData()
    if (trendData.length > 0) {
      dates = trendData.map(d => d.date?.substring(5) || d.date) // MM-DD
      counts = trendData.map(d => d.count)
    }
    // 没有趋势数据时明确显示空态，不伪造一周的 0 值
    if (dates.length === 0) {
      dates = ['暂无趋势数据']
      counts = [0]
    }

    const option = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#fcfdfb',
        borderColor: '#d8e1da',
        borderWidth: 1,
        padding: [8, 10],
        textStyle: { color: '#17201c', fontSize: 13 },
        axisPointer: { type: 'line', lineStyle: { color: '#d8e1da' } },
        extraCssText: 'box-shadow:0 4px 12px rgba(18,28,23,.08);border-radius:6px;'
      },
      grid: { left: 0, right: 8, bottom: 0, top: 18, containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#5b675f', fontSize: 12, margin: 12 }
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#e8ede9', type: 'solid', width: 1 } },
        axisLabel: { color: '#5b675f', fontSize: 12 }
      },
      series: [{
        name: '水印嵌入',
        type: 'line',
        smooth: 0.3,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#2f6b5a' },
        itemStyle: { color: '#2f6b5a', borderWidth: 2, borderColor: '#fcfdfb' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(47, 107, 90, 0.2)' },
            { offset: 1, color: 'rgba(47, 107, 90, 0.02)' }
          ])
        },
        data: counts
      }]
    }
    watermarkChart.setOption(option)
  }
}

// 本周/本月切换时真正重绘图表
watch(chartType, () => {
  nextTick(() => initCharts())
})

// 窗口大小变化时重绘图表
function handleResize() {
  assetChart?.resize()
  watermarkChart?.resize()
}

function viewAsset(row) {
  if (!row?.id) return
  router.push(`/assets/${row.id}`)
}

function goToPendingLicenses() {
  router.push('/admin/license/pending')
}

onMounted(() => {
  loadDashboardData()
  loadSystemStatus()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  assetChart?.dispose()
  watermarkChart?.dispose()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.dashboard-page {
  min-height: 100%;
  background: $bg-primary;
}

// 欢迎区域
.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: $primary-dark;
  border-radius: $radius-lg;
  padding: 30px 36px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg width='48' height='48' viewBox='0 0 48 48' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23fcfdfb' stroke-opacity='0.07' stroke-width='1'%3E%3Cpath d='M24 0v48M0 24h48'/%3E%3Crect x='10' y='10' width='28' height='28' transform='rotate(45 24 24)'/%3E%3C/g%3E%3C/svg%3E");
    pointer-events: none;
  }

  .welcome-content {
    position: relative;
    z-index: 1;
  }

  .welcome-title {
    color: #fcfdfb;
    margin-bottom: 8px;

    .greeting {
      font-size: 14px;
      font-weight: $font-weight-normal;
      opacity: 0.7;
    }

    .username {
      display: block;
      font-family: $font-display;
      font-size: 26px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }
  }

  .welcome-subtitle {
    color: rgba(252, 253, 251, 0.66);
    font-size: 14px;
    margin-bottom: 20px;
  }

  .welcome-actions {
    display: flex;
    gap: 10px;

    .btn-action {
      background: #fcfdfb !important;
      color: $primary-dark !important;
      border: 1px solid #fcfdfb !important;
      font-weight: $font-weight-medium;
      padding: 10px 20px;
      border-radius: $radius-sm;

      &:hover {
        background: $bg-secondary !important;
        color: $primary-dark !important;
      }
    }

    .btn-action-secondary {
      background: transparent !important;
      color: #fcfdfb !important;
      border: 1px solid rgba(252, 253, 251, 0.3) !important;
      font-weight: $font-weight-medium;
      padding: 10px 20px;
      border-radius: $radius-sm;

      &:hover {
        background: rgba(252, 253, 251, 0.08) !important;
        border-color: rgba(252, 253, 251, 0.5) !important;
      }
    }
  }
}

// 统计卡片
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  background: $bg-card;
  border-radius: $radius-lg;
  padding: 20px;
  box-shadow: $shadow-sm;
  border: 1px solid $border-color;
  transition: border-color $transition-fast, box-shadow $transition-fast;
  animation: fadeIn 0.5s ease forwards;
  opacity: 0;

  &:hover {
    border-color: $border-dark;
    box-shadow: $shadow-md;
  }

  .stat-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .stat-icon-wrapper {
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    background: $bg-secondary !important;
    border: 1px solid $border-color;
    box-shadow: none;

    .stat-icon {
      font-size: 20px;
      color: $primary-dark;
    }
  }

  .stat-trend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: $font-weight-medium;
    padding: 4px 8px;
    border-radius: $radius-full;

    &.up {
      background: rgba(34, 197, 94, 0.1);
      color: $success-color;
    }

    &.down {
      background: rgba(239, 68, 68, 0.1);
      color: $error-color;
    }
  }

  .stat-card-body {
    margin-bottom: 16px;
  }

  .stat-value {
    margin-bottom: 4px;

    .value-number {
      font-family: $font-display;
      font-size: 30px;
      font-weight: 600;
      color: $text-primary;
      font-variant-numeric: tabular-nums;
    }

    .value-suffix {
      font-size: 16px;
      color: $text-secondary;
      margin-left: 4px;
    }
  }

  .stat-label {
    font-size: 14px;
    color: $text-secondary;
  }

  .stat-card-footer {
    .progress-bar {
      height: 6px;
      background: $bg-secondary;
      border-radius: $radius-full;
      overflow: hidden;
      margin-bottom: 8px;

      .progress-fill {
        height: 100%;
        border-radius: $radius-full;
        transition: width 1s ease;
      }
    }

    .progress-text {
      font-size: 12px;
      color: $text-placeholder;
    }
  }
}

// 主内容区域
.main-content {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;
  margin-bottom: 32px;
}

.content-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.content-right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// 卡片通用样式
.chart-card, .quick-actions-card, .activity-card, .todo-card, .table-card, .system-card {
  background: $bg-card;
  border-radius: $radius-lg;
  padding: 20px;
  box-shadow: $shadow-sm;
  border: 1px solid $border-color;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-title {
  font-family: $font-display;
  font-size: 17px;
  font-weight: 600;
  color: $text-primary;
}

.system-card {
  .card-header {
    margin-bottom: 12px;
  }
}

.system-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.system-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.system-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 12px;
    color: $text-primary;
  }

  span {
    margin-top: 2px;
    font-size: 11px;
    line-height: 1.5;
    color: $text-placeholder;
  }
}

.system-note {
  margin: 12px 0 0;
  font-size: 11px;
  line-height: 1.6;
  color: $text-placeholder;
}

.chart-container {
  height: 320px;
}

// 快捷入口
.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.quick-action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  cursor: pointer;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $primary-color;
  }

  .action-icon {
    width: 40px;
    height: 40px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
    background: $bg-secondary !important;
    border: 1px solid $border-color;
    box-shadow: none;

    .el-icon {
      font-size: 20px;
      color: $primary-dark;
    }
  }

  .action-label {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }
}

// 活动列表
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: $radius-lg;
  transition: background $transition-fast;

  &:hover {
    background: $bg-primary;
  }

  .activity-avatar {
    width: 34px;
    height: 34px;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    background: $bg-secondary !important;
    border: 1px solid $border-color;

    .el-icon {
      font-size: 16px;
      color: $primary-dark;
    }
  }

  .activity-content {
    flex: 1;
    min-width: 0;
  }

  .activity-title {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .activity-desc {
    font-size: 13px;
    color: $text-secondary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .activity-time {
    font-size: 12px;
    color: $text-placeholder;
    flex-shrink: 0;
  }
}

// 待办事项
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $border-dark;
  }

  .todo-priority {
    width: 4px;
    height: 40px;
    border-radius: 2px;
    flex-shrink: 0;

    &.high { background: $error-color; }
    &.medium { background: $warning-color; }
    &.low { background: $info-color; }
  }

  .todo-content {
    flex: 1;
    min-width: 0;
  }

  .todo-title {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .todo-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .todo-deadline {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: $text-secondary;
  }
}

// 底部表格
.bottom-section {
  .table-card {
    overflow: hidden;
  }

  .asset-info {
    display: flex;
    align-items: center;
    gap: 12px;

    .asset-thumb {
      width: 48px;
      height: 48px;
      border-radius: $radius-md;
      overflow: hidden;
      flex-shrink: 0;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    .asset-meta {
      min-width: 0;
    }

    .asset-code {
      font-size: 12px;
      color: $text-secondary;
      font-family: $font-mono;
    }

    .asset-title {
      font-size: 14px;
      font-weight: $font-weight-medium;
      color: $text-primary;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .status-cell {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;

      &.none { background: $text-placeholder; }
      &.pending { background: $warning-color; }
      &.embedded, &.confirmed, &.verified { background: $success-color; }
      &.failed { background: $error-color; }
    }
  }
}

// 响应式
@media (max-width: 1400px) {
  .main-content {
    grid-template-columns: 1fr 350px;
  }
}

.empty-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: $text-placeholder;
  font-size: $font-size-sm;

  .el-icon {
    font-size: 28px;
  }
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .main-content {
    grid-template-columns: 1fr;
  }

  .content-right {
    flex-direction: row;
    flex-wrap: wrap;

    > * {
      flex: 1;
      min-width: 300px;
    }
  }
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }

  .welcome-section {
    padding: 24px;
    flex-direction: column;
    text-align: center;

    .welcome-illustration {
      display: none;
    }

    .welcome-actions {
      flex-direction: column;
      width: 100%;

      button {
        width: 100%;
      }
    }
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}

// 动画
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
