<template>
  <div class="license-usage">
    <header class="page-head">
      <div>
        <h1 class="page-title">授权使用报表</h1>
        <p class="page-subtitle">授权状态、配额消耗、超范围拒绝与版本过期趋势</p>
      </div>
      <div class="head-actions">
        <el-button :loading="loading" @click="loadReport">刷新</el-button>
        <el-button plain :disabled="rows.length === 0" @click="exportCsv">导出当前页</el-button>
      </div>
    </header>

    <section class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">有效授权</span>
        <strong class="summary-value">{{ summary.active ?? '—' }}</strong>
        <span class="summary-note">共 {{ summary.total ?? '—' }} 条授权</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">30 天内到期</span>
        <strong class="summary-value warning">{{ summary.expiring_30d ?? '—' }}</strong>
        <span class="summary-note">含 {{ summary.expired ?? 0 }} 条已过期</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">版本待重审</span>
        <strong class="summary-value danger">{{ summary.version_outdated ?? '—' }}</strong>
        <span class="summary-note">授权绑定的不是当前文件版本</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">超范围拒绝</span>
        <strong class="summary-value danger">{{ summary.denied ?? '—' }}</strong>
        <span class="summary-note">近 {{ summary.days || days }} 天</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">配额使用</span>
        <strong class="summary-value">
          {{ summary.quota_used ?? 0 }}<small>/{{ summary.quota_total ?? 0 }}</small>
        </strong>
        <span class="summary-note">{{ summary.quota_licenses ?? 0 }} 条授权设了上限</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">近 {{ summary.days || days }} 天下载</span>
        <strong class="summary-value">{{ summary.downloads ?? '—' }}</strong>
        <span class="summary-note">今日 {{ summary.downloads_today ?? 0 }} 次</span>
      </div>
    </section>

    <section class="filter-card">
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 130px">
        <el-option label="生效中" value="active" />
        <el-option label="已过期" value="expired" />
        <el-option label="已撤销" value="revoked" />
        <el-option label="待生效" value="pending" />
      </el-select>
      <el-select v-model="filters.version_outdated" style="width: 150px">
        <el-option label="全部版本" value="" />
        <el-option label="仅历史版本授权" value="1" />
        <el-option label="仅当前版本授权" value="0" />
      </el-select>
      <el-select v-model="filters.days" style="width: 120px">
        <el-option label="近 7 天" :value="7" />
        <el-option label="近 30 天" :value="30" />
        <el-option label="近 90 天" :value="90" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="授权编号、资产或被授权方"
        clearable
        style="width: 260px"
        @keyup.enter="applyFilters"
      />
      <el-button type="primary" @click="applyFilters">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <div class="charts-grid">
      <section class="chart-card">
        <header class="card-head">
          <h3>下载与拒绝趋势</h3>
          <span>近 {{ summary.days || days }} 天</span>
        </header>
        <div v-if="loading" class="chart-placeholder">加载中…</div>
        <div v-else ref="trendChartRef" class="chart-canvas"></div>
      </section>
      <section class="reasons-card">
        <header class="card-head">
          <h3>超范围原因</h3>
          <span>近 {{ summary.days || days }} 天</span>
        </header>
        <div v-if="denialCategories.length === 0" class="empty-mini">暂无拒绝记录</div>
        <ul v-else class="reason-list">
          <li v-for="item in denialCategories" :key="item.key">
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
          </li>
        </ul>
      </section>
    </div>

    <section class="table-card">
      <header class="card-head">
        <h3>授权明细</h3>
        <span>按授权创建时间倒序</span>
      </header>
      <el-table v-loading="loading" :data="rows" stripe row-key="id">
        <el-table-column label="授权 / 资产" min-width="240">
          <template #default="{ row }">
            <div class="license-code mono">{{ row.license_code }}</div>
            <router-link
              v-if="row.asset_id"
              :to="`/assets/${row.asset_id}`"
              class="asset-link"
            >
              {{ row.asset_title || row.asset_code || '查看资产' }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="被授权方" width="130">
          <template #default="{ row }">{{ row.licensee_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="版本" width="150">
          <template #default="{ row }">
            <div class="version-line">
              授权 v{{ row.version_no || '—' }}
              <span class="muted">/ 当前 v{{ row.current_version_no || '—' }}</span>
            </div>
            <el-tag v-if="row.version_outdated" size="small" type="danger" effect="plain">
              需重新申请
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="配额" width="170">
          <template #default="{ row }">
            <template v-if="row.max_downloads">
              <el-progress
                :percentage="quotaPercent(row)"
                :stroke-width="6"
                :status="quotaPercent(row) >= 100 ? 'exception' : undefined"
              />
              <span class="quota-text">
                {{ row.download_count || 0 }} / {{ row.max_downloads }}
              </span>
            </template>
            <span v-else class="muted">不限次数</span>
          </template>
        </el-table-column>
        <el-table-column label="下载 / 拒绝" width="110">
          <template #default="{ row }">
            {{ row.download_count || 0 }} / <span class="danger-text">{{ row.denied_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最近下载" width="170">
          <template #default="{ row }">{{ formatTime(row.last_download_at) }}</template>
        </el-table-column>
        <el-table-column label="到期时间" width="120">
          <template #default="{ row }">
            {{ row.end_time ? formatDate(row.end_time) : '长期' }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && rows.length === 0" class="empty-table">
        <el-empty description="没有匹配的授权" :image-size="72" />
      </div>

      <el-pagination
        v-if="rowTotal > 0"
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="rowTotal"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="loadReport"
        @current-change="loadReport"
      />
    </section>

    <section class="table-card top-assets">
      <header class="card-head">
        <h3>资产使用排行</h3>
        <span>按下载 + 拒绝次数排序</span>
      </header>
      <el-table :data="topAssets" size="small">
        <el-table-column label="资产" min-width="240">
          <template #default="{ row }">
            <router-link v-if="row.asset_id" :to="`/assets/${row.asset_id}`" class="asset-link">
              {{ row.asset_title || row.asset_code }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="license_count" label="授权数" width="90" />
        <el-table-column prop="downloads" label="下载" width="90" />
        <el-table-column label="拒绝" width="90">
          <template #default="{ row }">
            <span class="danger-text">{{ row.denied }}</span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import echarts from '@/utils/echarts'
import { parseBackendDate } from '@/utils'
import { licenseApi } from '@/api/modules'

const loading = ref(false)
const summary = ref({})
const rows = ref([])
const rowTotal = ref(0)
const page = ref(1)
const perPage = ref(20)
const topAssets = ref([])
const denialCategories = ref([])
const trend = ref([])
const trendChartRef = ref(null)
const filters = reactive({
  status: '',
  version_outdated: '',
  days: 30,
  keyword: ''
})
const applied = reactive({
  status: '',
  version_outdated: '',
  days: 30,
  keyword: ''
})
const days = computed(() => applied.days)
let trendChart = null

const STATUS_LABELS = {
  active: '生效中',
  expired: '已过期',
  revoked: '已撤销',
  pending: '待生效'
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status || '未知'
}

function statusType(status) {
  return {
    active: 'success',
    expired: 'warning',
    revoked: 'danger',
    pending: 'info'
  }[status] || 'info'
}

function quotaPercent(row) {
  if (!row.max_downloads) return 0
  return Math.min(100, Math.round(((row.download_count || 0) / row.max_downloads) * 100))
}

function formatDate(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleDateString('zh-CN') : '—'
}

function formatTime(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : '—'
}

function applyFilters() {
  applied.status = filters.status || ''
  applied.version_outdated = filters.version_outdated || ''
  applied.days = filters.days || 30
  applied.keyword = filters.keyword.trim()
  page.value = 1
  loadReport()
}

function resetFilters() {
  filters.status = ''
  filters.version_outdated = ''
  filters.days = 30
  filters.keyword = ''
  applyFilters()
}

function renderChart() {
  if (!trendChartRef.value || trend.value.length === 0) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const dates = trend.value.map(item => item.date.slice(5))
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['下载', '拒绝'], top: 0, right: 0 },
    grid: { left: 40, right: 20, top: 36, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { interval: Math.max(0, Math.floor(dates.length / 8)) }
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '下载',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: { opacity: 0.12 },
        itemStyle: { color: '#2f6b5a' },
        data: trend.value.map(item => item.success)
      },
      {
        name: '拒绝',
        type: 'line',
        smooth: true,
        symbol: 'none',
        itemStyle: { color: '#a6402f' },
        data: trend.value.map(item => item.denied)
      }
    ]
  }, true)
}

async function loadReport() {
  loading.value = true
  let loaded = false
  try {
    const response = await licenseApi.usageReport({
      page: page.value,
      per_page: perPage.value,
      days: applied.days,
      status: applied.status || undefined,
      version_outdated: applied.version_outdated || undefined,
      keyword: applied.keyword || undefined
    })
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      summary.value = data.summary || {}
      rows.value = data.rows?.items || []
      rowTotal.value = data.rows?.total || 0
      trend.value = data.trend || []
      denialCategories.value = data.denial_categories || []
      topAssets.value = data.top_assets || []
      loaded = true
    } else {
      ElMessage.error(response.data?.message || '报表加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '报表加载失败')
  } finally {
    loading.value = false
  }
  if (loaded) {
    await nextTick()
    renderChart()
  }
}

function exportCsv() {
  const headers = [
    '授权编号', '资产编码', '资产标题', '被授权方', '状态',
    '授权版本', '当前版本', '下载次数', '拒绝次数', '配额上限',
    '最近下载', '到期时间'
  ]
  const lines = rows.value.map(row => [
    row.license_code,
    row.asset_code || '',
    row.asset_title || '',
    row.licensee_name || '',
    statusLabel(row.status),
    row.version_no || '',
    row.current_version_no || '',
    row.download_count || 0,
    row.denied_count || 0,
    row.max_downloads || '',
    row.last_download_at || '',
    row.end_time || ''
  ])
  const csv = [headers, ...lines].map(line =>
    line.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')
  ).join('\n')
  const blob = new Blob([String.fromCharCode(0xFEFF) + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `license-usage-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function handleResize() {
  trendChart?.resize()
}

onMounted(() => {
  loadReport()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  trendChart = null
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-usage {
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
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: $spacing-lg;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
  font-size: 25px;
  font-weight: 600;
  color: $text-primary;

  small {
    font-size: 13px;
    color: $text-placeholder;
  }

  &.warning { color: $accent-color; }
  &.danger { color: $error-color; }
}

.summary-note {
  font-size: 11px;
  color: $text-placeholder;
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

.charts-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(220px, 1fr);
  gap: 16px;
  margin-bottom: $spacing-lg;
}

.chart-card,
.reasons-card,
.table-card {
  padding: 16px 18px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;

  h3 {
    margin: 0;
    font-family: $font-display;
    font-size: 15px;
    color: $text-primary;
  }

  span {
    font-size: 12px;
    color: $text-placeholder;
  }
}

.chart-canvas {
  width: 100%;
  height: 260px;
}

.chart-placeholder {
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: $text-placeholder;
}

.reason-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;

  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px dashed $border-light;
    font-size: 13px;
    color: $text-secondary;

    strong {
      color: $error-color;
      font-family: $font-mono;
    }
  }
}

.empty-mini {
  padding: 24px 0;
  text-align: center;
  font-size: 12px;
  color: $text-placeholder;
}

.table-card {
  margin-bottom: $spacing-lg;
}

.license-code {
  font-size: 12px;
  color: $text-primary;
}

.mono {
  font-family: $font-mono;
}

.asset-link {
  font-size: 12px;
  color: $primary-dark;
  text-decoration: none;

  &:hover { text-decoration: underline; }
}

.version-line {
  font-size: 12px;
  color: $text-secondary;
}

.muted {
  color: $text-placeholder;
}

.danger-text {
  color: $error-color;
}

.quota-text {
  font-size: 11px;
  color: $text-placeholder;
}

.empty-table {
  padding: 16px 0;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}

@media (max-width: $breakpoint-lg) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: $breakpoint-md) {
  .license-usage {
    padding: 16px;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
