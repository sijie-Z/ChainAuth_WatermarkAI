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
        <div class="welcome-actions">
          <el-button type="primary" class="btn-action" @click="$router.push('/admin/assets')">
            <el-icon><Upload /></el-icon>
            管理资产
          </el-button>
          <el-button class="btn-action-secondary" @click="$router.push('/admin/watermark')">
            <el-icon><Stamp /></el-icon>
            水印处理
          </el-button>
        </div>
      </div>
      <div class="welcome-illustration">
        <div class="illustration-bg">
          <svg viewBox="0 0 400 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="200" cy="100" r="80" fill="url(#paint0_linear)" opacity="0.2"/>
            <path d="M160 80 L240 80 L240 140 L160 140 Z" fill="white" opacity="0.3"/>
            <path d="M170 90 L230 90 L230 130 L170 130 Z" fill="white" opacity="0.5"/>
            <defs>
              <linearGradient id="paint0_linear" x1="120" y1="20" x2="280" y2="180">
                <stop stop-color="#10b981"/>
                <stop offset="1" stop-color="#059669"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        class="stat-card"
        v-for="(stat, index) in statCards"
        :key="stat.key"
        :style="{ animationDelay: index * 0.1 + 's' }"
      >
        <div class="stat-card-header">
          <div class="stat-icon-wrapper" :style="{ background: stat.gradient }">
            <el-icon class="stat-icon"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'" v-if="stat.trend">
            <el-icon><component :is="stat.trend > 0 ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
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
        <div class="stat-card-footer">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: stat.progress + '%', background: stat.gradient }"></div>
          </div>
          <span class="progress-text">{{ stat.progress }}% 完成率</span>
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
              <el-radio-button label="week">本周</el-radio-button>
              <el-radio-button label="month">本月</el-radio-button>
            </el-radio-group>
          </div>
          <div class="chart-container" ref="assetChartRef"></div>
        </div>

        <!-- 水印处理趋势 -->
        <div class="chart-card">
          <div class="card-header">
            <h3 class="card-title">水印处理趋势</h3>
            <el-tag size="small" type="success">实时更新</el-tag>
          </div>
          <div class="chart-container" ref="watermarkChartRef"></div>
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

        <!-- 最近活动 -->
        <div class="activity-card">
          <div class="card-header">
            <h3 class="card-title">最近活动</h3>
            <el-button type="primary" link size="small">查看全部</el-button>
          </div>
          <div class="activity-list">
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
          <div class="todo-list">
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
              <el-button type="primary" size="small" round>处理</el-button>
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
          <el-button type="primary" link>查看全部 →</el-button>
        </div>
        <el-table :data="recentAssets" style="width: 100%" class="modern-table">
          <el-table-column label="资产信息" min-width="280">
            <template #default="{ row }">
              <div class="asset-info">
                <div class="asset-thumb">
                  <img :src="row.thumbnail || getDefaultThumb(row.type)" alt="" />
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
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { assetApi, licenseApi, blockchainApi } from '@/api/modules'
import { ElMessage } from 'element-plus'
import {
  Picture, Stamp, Link, Document, Upload, Clock,
  ArrowUp, ArrowDown, User, Setting, Files, Grid,
  CircleCheck, Timer, WarningFilled
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
  { key: 'totalAssets', label: '资产总数', icon: 'Picture', gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', suffix: '个' },
  { key: 'watermarkedAssets', label: '已嵌入水印', icon: 'Stamp', gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', suffix: '个' },
  { key: 'chainedAssets', label: '链上存证', icon: 'Link', gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)', suffix: '个' },
  { key: 'pendingLicenses', label: '待审批授权', icon: 'Document', gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', suffix: '个' }
]

const statCards = ref(
  statCardDefs.map(def => ({ ...def, value: 0, trend: null, progress: 0 }))
)

// 动画数值
const animatedValues = reactive({
  totalAssets: 0,
  watermarkedAssets: 0,
  chainedAssets: 0,
  pendingLicenses: 0
})

// API 数据缓存
let pieData = []
let trendData = []

// 快捷操作
const quickActions = ref([
  { label: '资产管理', icon: 'Picture', path: '/admin/assets', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { label: '水印处理', icon: 'Stamp', path: '/admin/watermark', gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
  { label: '存证管理', icon: 'Link', path: '/admin/blockchain', gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' },
  { label: '用户管理', icon: 'User', path: '/admin/users', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' }
])

// 最近活动
const recentActivities = ref([])

// 待办事项（从待审批授权映射）
const todoList = ref([])

const pendingCount = computed(() => todoList.value.length)

// 最近资产
const recentAssets = ref([])

// 加载仪表盘数据
async function loadDashboardData() {
  loading.value = true
  try {
    const [statsRes, pendingLicensesRes] = await Promise.all([
      assetApi.getDetail('stats'),
      licenseApi.getPending()
    ])

    let stats = null
    if (statsRes.data?.code === 200) {
      stats = statsRes.data.data
    }

    // 统计卡片
    if (stats) {
      const total = stats.total || 0
      const watermarked = stats.watermarked || 0
      const chained = stats.chained || 0
      const pendingLicenses = stats.pending_licenses || 0

      statCards.value = statCardDefs.map(def => {
        let value = 0
        let progress = 0
        if (def.key === 'totalAssets') { value = total; progress = total > 0 ? Math.round((watermarked / total) * 100) : 0 }
        if (def.key === 'watermarkedAssets') { value = watermarked; progress = total > 0 ? Math.round((watermarked / total) * 100) : 0 }
        if (def.key === 'chainedAssets') { value = chained; progress = total > 0 ? Math.round((chained / total) * 100) : 0 }
        if (def.key === 'pendingLicenses') { value = pendingLicenses; progress = pendingLicenses > 0 ? Math.min(pendingLicenses * 20, 100) : 0 }
        return { ...def, value, trend: null, progress }
      })
    }

    // 饼图数据
    if (stats?.by_type) {
      const typeColors = { image: '#10b981', vector: '#3b82f6', model: '#8b5cf6', document: '#f59e0b', video: '#ef4444' }
      const typeNames = { image: '图片', vector: '矢量', model: '模型', document: '文档', video: '视频' }
      pieData = Object.entries(stats.by_type)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ value: v, name: typeNames[k] || k, itemStyle: { color: typeColors[k] || '#6b7280' } }))
    }

    // 趋势数据
    if (stats?.watermark_trends?.length) {
      trendData = stats.watermark_trends
    }

    // 最近活动
    if (stats?.recent_activities?.length) {
      const actionIcons = { upload: 'Picture', embed: 'Stamp', extract: 'Stamp', register: 'Link', approve: 'Document', login: 'User' }
      const actionColors = { upload: '#10b981', embed: '#3b82f6', extract: '#3b82f6', register: '#8b5cf6', approve: '#f59e0b', login: '#6b7280' }
      recentActivities.value = stats.recent_activities.slice(0, 8).map((a, i) => ({
        id: a.id || i,
        icon: actionIcons[a.action] || 'CircleCheck',
        title: a.action || a.module || '操作',
        description: a.description || '',
        time: formatTimeAgo(a.created_at),
        color: actionColors[a.action] || '#6b7280'
      }))
    }

    // 待办事项（来自待审批授权）
    const pendingApps = pendingLicensesRes.data?.code === 200
      ? (pendingLicensesRes.data.data?.items || pendingLicensesRes.data.data || [])
      : []
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
    nextTick(() => initCharts())
  } catch (e) {
    ElMessage.warning('部分数据加载失败，使用默认数据')
  } finally {
    loading.value = false
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

function getDefaultThumb(type) {
  const colors = { image: '#10b981', vector: '#3b82f6', model: '#8b5cf6', document: '#f59e0b', video: '#ef4444' }
  const color = colors[type] || '#6b7280'
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
  const statusMap = { none: '未处理', pending: '处理中', embedded: '已完成' }
  return statusMap[status] || '未知'
}

function getChainStatus(status) {
  const statusMap = { none: '未存证', pending: '处理中', confirmed: '已确认' }
  return statusMap[status] || '未知'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
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

// 数字动画
function animateNumbers() {
  statCards.value.forEach(stat => {
    const target = stat.value
    const duration = 1500
    const steps = 40
    const increment = target / steps
    let current = 0

    const timer = setInterval(() => {
      current += increment
      if (current >= target) {
        animatedValues[stat.key] = target
        clearInterval(timer)
      } else {
        animatedValues[stat.key] = Math.floor(current)
      }
    }, duration / steps)
  })
}

// 初始化图表
function initCharts() {
  // 资产类型分布图
  if (assetChartRef.value) {
    if (assetChart) assetChart.dispose()
    assetChart = echarts.init(assetChartRef.value)
    const defaultPieData = [
      { value: 0, name: '暂无数据', itemStyle: { color: '#e5e7eb' } }
    ]
    const option = {
      tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#eee', borderWidth: 1, textStyle: { color: '#333' } },
      legend: { bottom: '5%', left: 'center', textStyle: { color: '#666' } },
      series: [{
        name: '资产类型',
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
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
    if (trendData.length > 0) {
      dates = trendData.map(d => d.date?.substring(5) || d.date) // MM-DD
      counts = trendData.map(d => d.count)
    }
    // 如果没有趋势数据，显示空图
    if (dates.length === 0) {
      const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      dates = weekdays
      counts = [0, 0, 0, 0, 0, 0, 0]
    }

    const option = {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#eee', borderWidth: 1, textStyle: { color: '#333' } },
      grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { color: '#6b7280' }
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
        axisLabel: { color: '#6b7280' }
      },
      series: [{
        name: '水印嵌入',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#10b981' },
        itemStyle: { color: '#10b981', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.05)' }
          ])
        },
        data: counts
      }]
    }
    watermarkChart.setOption(option)
  }
}

// 窗口大小变化时重绘图表
function handleResize() {
  assetChart?.resize()
  watermarkChart?.resize()
}

onMounted(() => {
  loadDashboardData()
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
  padding: 32px;
}

// 欢迎区域
.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  border-radius: $radius-2xl;
  padding: 40px 48px;
  margin-bottom: 32px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    pointer-events: none;
  }

  .welcome-content {
    position: relative;
    z-index: 1;
  }

  .welcome-title {
    color: white;
    margin-bottom: 8px;

    .greeting {
      font-size: 16px;
      font-weight: $font-weight-normal;
      opacity: 0.9;
    }

    .username {
      display: block;
      font-size: 28px;
      font-weight: $font-weight-bold;
    }
  }

  .welcome-subtitle {
    color: rgba(255, 255, 255, 0.85);
    font-size: 15px;
    margin-bottom: 24px;
  }

  .welcome-actions {
    display: flex;
    gap: 12px;

    .btn-action {
      background: white !important;
      color: $primary-dark !important;
      border: none;
      font-weight: $font-weight-medium;
      padding: 12px 24px;
      border-radius: $radius-lg;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }
    }

    .btn-action-secondary {
      background: rgba(255, 255, 255, 0.2) !important;
      color: white !important;
      border: 1px solid rgba(255, 255, 255, 0.3);
      font-weight: $font-weight-medium;
      padding: 12px 24px;
      border-radius: $radius-lg;

      &:hover {
        background: rgba(255, 255, 255, 0.3) !important;
      }
    }
  }

  .welcome-illustration {
    position: relative;
    z-index: 1;

    .illustration-bg {
      width: 200px;
      height: 200px;
      opacity: 0.6;

      svg {
        width: 100%;
        height: 100%;
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
  background: white;
  border-radius: $radius-xl;
  padding: 24px;
  box-shadow: $shadow-card;
  border: 1px solid rgba(0, 0, 0, 0.02);
  transition: all $transition-base;
  animation: fadeIn 0.6s ease forwards;
  opacity: 0;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-card-hover;
  }

  .stat-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .stat-icon-wrapper {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

    .stat-icon {
      font-size: 24px;
      color: white;
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
      font-size: 32px;
      font-weight: $font-weight-bold;
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
.chart-card, .quick-actions-card, .activity-card, .todo-card, .table-card {
  background: white;
  border-radius: $radius-xl;
  padding: 24px;
  box-shadow: $shadow-card;
  border: 1px solid rgba(0, 0, 0, 0.02);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-title {
  font-size: 16px;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.chart-container {
  height: 280px;
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
  padding: 20px;
  background: $bg-primary;
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: $bg-secondary;
    transform: translateY(-2px);
  }

  .action-icon {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

    .el-icon {
      font-size: 24px;
      color: white;
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
    width: 40px;
    height: 40px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    .el-icon {
      font-size: 18px;
      color: white;
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
  padding: 14px;
  background: $bg-primary;
  border-radius: $radius-lg;
  transition: all $transition-fast;

  &:hover {
    background: $bg-secondary;
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
      &.embedded, &.confirmed { background: $success-color; }
    }
  }
}

// 响应式
@media (max-width: 1400px) {
  .main-content {
    grid-template-columns: 1fr 350px;
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
