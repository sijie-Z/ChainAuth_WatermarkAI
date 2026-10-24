<template>
  <div class="admin-tasks">
    <header class="page-head">
      <div>
        <h1 class="page-title">任务队列</h1>
        <p class="page-subtitle">水印与存证后台任务的排队、执行、失败重试与超时回收</p>
      </div>
      <div class="head-actions">
        <el-switch v-model="autoRefresh" active-text="自动刷新" />
        <el-button :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </header>

    <el-alert
      v-if="!loading && !workerEnabled"
      type="warning"
      :closable="false"
      show-icon
      class="worker-alert"
      title="后台 worker 未启用"
      description="任务会留在队列中。请启动 docker compose 的 worker 服务，或运行 flask tasks run。"
    />

    <el-alert
      v-if="health && health.warnings?.length"
      :type="health.status === 'critical' ? 'error' : 'warning'"
      :closable="false"
      show-icon
      class="worker-alert"
      :title="health.status === 'critical' ? '队列健康度：异常' : '队列健康度：需要关注'"
    >
      <ul class="health-warnings">
        <li v-for="warning in health.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </el-alert>

    <section class="health-strip">
      <div class="health-item">
        <span class="health-label">在线 worker</span>
        <strong class="health-value" :class="{ danger: health && !health.online_workers }">
          {{ health?.online_workers ?? '—' }}
        </strong>
      </div>
      <div class="health-item">
        <span class="health-label">最老排队任务</span>
        <strong class="health-value">{{ formatDuration(health?.oldest_queued_seconds) }}</strong>
      </div>
      <div class="health-item">
        <span class="health-label">超时处理中</span>
        <strong class="health-value" :class="{ danger: health?.stale_running }">
          {{ health?.stale_running ?? '—' }}
        </strong>
      </div>
      <div class="health-item health-workers">
        <span class="health-label">worker 心跳</span>
        <span v-if="!health?.workers?.length" class="muted">暂无心跳</span>
        <el-tag
          v-for="worker in (health?.workers || []).slice(0, 3)"
          :key="worker.worker_id"
          size="small"
          :type="worker.online ? 'success' : 'info'"
          effect="plain"
          :title="worker.worker_id"
        >
          {{ worker.online ? '在线' : '离线' }} · {{ worker.kind_label }} ·
          {{ formatDuration(worker.last_seen_seconds) }}前
        </el-tag>
      </div>
    </section>

    <section class="summary-grid">
      <div v-for="item in summaryItems" :key="item.key" class="summary-card">
        <span class="summary-label">{{ item.label }}</span>
        <strong class="summary-value" :class="item.tone">{{ item.value }}</strong>
      </div>
    </section>

    <section class="filter-card">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 160px">
        <el-option label="排队中" value="queued" />
        <el-option label="处理中" value="running" />
        <el-option label="已完成" value="succeeded" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-input
        v-model="assetFilter"
        placeholder="按资产 ID 筛选"
        clearable
        style="width: 300px"
        @keyup.enter="loadTasks"
      />
      <el-button type="primary" @click="loadTasks">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="table-card">
      <el-table v-loading="loading" :data="tasks" stripe row-key="id">
        <el-table-column label="任务" min-width="240">
          <template #default="{ row }">
            <div class="task-type">{{ row.task_type_label }}</div>
            <div class="task-id mono" :title="row.id">{{ row.id.slice(0, 8) }}…{{ row.id.slice(-4) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="资产" min-width="180">
          <template #default="{ row }">
            <router-link
              v-if="row.asset_id && (row.asset_title || row.asset_code)"
              :to="`/assets/${row.asset_id}`"
              class="asset-link"
            >
              {{ row.asset_title || row.asset_code }}
            </router-link>
            <span v-else-if="!row.asset_id" class="muted">全局任务</span>
            <span v-else class="muted">资产已删除</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="row.status === 'failed' ? 'exception' : undefined"
              :stroke-width="6"
            />
          </template>
        </el-table-column>
        <el-table-column label="尝试" width="80">
          <template #default="{ row }">{{ row.attempts }}/{{ row.max_attempts }}</template>
        </el-table-column>
        <el-table-column label="错误" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ 'error-text': row.error_message }">{{ row.error_message || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            <div class="time-line">{{ formatTime(row.created_at) }}</div>
            <div v-if="row.finished_at" class="time-line muted">
              完成 {{ formatTime(row.finished_at) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="['failed', 'cancelled'].includes(row.status)"
              size="small"
              link
              type="primary"
              :loading="busyId === row.id"
              @click="retryTask(row)"
            >
              重试
            </el-button>
            <el-button
              v-if="row.status === 'queued'"
              size="small"
              link
              type="warning"
              :loading="busyId === row.id"
              @click="cancelTask(row)"
            >
              取消
            </el-button>
            <span v-if="!['failed', 'cancelled', 'queued'].includes(row.status)" class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && tasks.length === 0" class="empty-tasks">
        <el-empty description="没有匹配的任务" :image-size="72" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { parseBackendDate } from '@/utils'
import { systemApi, taskApi } from '@/api/modules'

const tasks = ref([])
const loading = ref(false)
const busyId = ref(null)
const workerEnabled = ref(true)
const statusFilter = ref('')
const assetFilter = ref('')
const autoRefresh = ref(true)
const counts = ref({})
const health = ref(null)
let refreshTimer = null

const summaryItems = computed(() => [
  { key: 'queued', label: '排队中', value: counts.value.queued || 0, tone: 'queued' },
  { key: 'running', label: '处理中', value: counts.value.running || 0, tone: 'running' },
  { key: 'failed', label: '失败', value: counts.value.failed || 0, tone: 'failed' },
  { key: 'succeeded', label: '已完成', value: counts.value.succeeded || 0, tone: 'succeeded' }
])

function statusType(status) {
  return {
    queued: 'info',
    running: 'warning',
    succeeded: 'success',
    failed: 'danger',
    cancelled: 'info'
  }[status] || 'info'
}

function formatTime(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : '—'
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时`
  return `${Math.floor(hours / 24)} 天`
}

async function loadTasks() {
  loading.value = true
  try {
    const response = await taskApi.list({
      status: statusFilter.value || undefined,
      asset_id: assetFilter.value.trim() || undefined
    })
    if (response.data?.code === 200) {
      tasks.value = response.data.data?.items || []
      workerEnabled.value = response.data.data?.worker_enabled !== false
    } else {
      ElMessage.error(response.data?.message || '任务加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '任务加载失败')
  } finally {
    loading.value = false
  }
}

async function loadSummary() {
  try {
    const response = await systemApi.getStatus()
    if (response.data?.code === 200) {
      counts.value = response.data.data?.tasks?.counts || {}
      workerEnabled.value = response.data.data?.tasks?.enabled !== false
    }
  } catch {
    // 系统状态读取失败不影响任务列表
  }
}

async function loadHealth() {
  try {
    const response = await taskApi.health()
    if (response.data?.code === 200) {
      health.value = response.data.data || null
    }
  } catch {
    // 健康度读取失败时保留上一次结果，不影响任务列表
  }
}

async function loadAll() {
  await Promise.all([loadTasks(), loadSummary(), loadHealth()])
}

function resetFilters() {
  statusFilter.value = ''
  assetFilter.value = ''
  loadTasks()
}

async function retryTask(task) {
  busyId.value = task.id
  try {
    const response = await taskApi.retry(task.id)
    if (response.data?.code === 200) {
      ElMessage.success('任务已重新排队')
      await loadAll()
    } else {
      ElMessage.error(response.data?.message || '重试失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '重试失败')
  } finally {
    busyId.value = null
  }
}

async function cancelTask(task) {
  try {
    await ElMessageBox.confirm(
      '取消后该任务不再执行，资产会回到未处理状态。',
      '取消任务',
      { type: 'warning', confirmButtonText: '取消任务', cancelButtonText: '返回' }
    )
  } catch {
    return
  }
  busyId.value = task.id
  try {
    const response = await taskApi.cancel(task.id)
    if (response.data?.code === 200) {
      ElMessage.success('任务已取消')
      await loadAll()
    } else {
      ElMessage.error(response.data?.message || '取消失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '取消失败')
  } finally {
    busyId.value = null
  }
}

function scheduleRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (autoRefresh.value) {
    refreshTimer = setInterval(loadAll, 5000)
  }
}

watch(autoRefresh, scheduleRefresh)

onMounted(() => {
  loadAll()
  scheduleRefresh()
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-tasks {
  min-height: 100%;
  padding: 24px 28px 32px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    margin-bottom: 4px;
    font-family: $font-display;
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
  }

  .page-subtitle {
    font-size: 13px;
    color: $text-secondary;
  }
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.worker-alert {
  margin-bottom: $spacing-lg;
}

.health-warnings {
  margin: 4px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.7;
}

.health-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 28px;
  padding: 12px 18px;
  margin-bottom: $spacing-lg;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.health-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.health-label {
  font-size: 12px;
  color: $text-secondary;
}

.health-value {
  font-family: $font-display;
  font-size: 17px;
  font-weight: 600;
  color: $text-primary;

  &.danger { color: $error-color; }
}

.health-workers {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: $spacing-lg;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.summary-label {
  font-size: 12px;
  color: $text-secondary;
}

.summary-value {
  font-family: $font-display;
  font-size: 26px;
  font-weight: 600;
  color: $text-primary;

  &.running { color: $accent-color; }
  &.failed { color: $error-color; }
  &.succeeded { color: $primary-color; }
}

.filter-card {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px;
  margin-bottom: $spacing-lg;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.table-card {
  padding: 8px 16px 16px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.task-type {
  font-weight: 600;
  color: $text-primary;
}

.task-id,
.mono {
  font-family: $font-mono;
  font-size: 11px;
  color: $text-placeholder;
}

.asset-link {
  color: $primary-dark;
  text-decoration: none;

  &:hover { text-decoration: underline; }
}

.muted {
  color: $text-placeholder;
}

.error-text {
  color: $error-color;
}

.time-line {
  font-size: 12px;
  color: $text-secondary;
}

.empty-tasks {
  padding: 24px 0;
}

@media (max-width: $breakpoint-md) {
  .admin-tasks {
    padding: 16px;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
