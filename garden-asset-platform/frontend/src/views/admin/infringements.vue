<template>
  <div class="admin-infringements">
    <header class="page-head">
      <div>
        <h1 class="page-title">侵权线索</h1>
        <p class="page-subtitle">核实公开提交的疑似盗用文件与来源，确认或驳回后通知相关方</p>
      </div>
      <div class="head-actions">
        <el-button type="primary" plain @click="openPatrol">批量巡检</el-button>
        <el-button :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </header>

    <section class="summary-grid">
      <div v-for="item in summaryItems" :key="item.key" class="summary-card">
        <span class="summary-label">{{ item.label }}</span>
        <strong class="summary-value" :class="item.tone">{{ item.value }}</strong>
      </div>
    </section>

    <section class="filter-card">
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px">
        <el-option label="待处理" value="pending" />
        <el-option label="处理中" value="reviewing" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="线索编号、资产、来源链接或说明"
        clearable
        style="width: 300px"
        @keyup.enter="applyFilters"
      />
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px"
      />
      <el-button type="primary" @click="applyFilters">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="table-card">
      <el-table v-loading="loading" :data="reports" stripe row-key="id">
        <el-table-column label="线索" width="200">
          <template #default="{ row }">
            <div class="report-code mono">{{ row.report_code }}</div>
            <div class="time-line">{{ formatTime(row.created_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="匹配资产" min-width="180">
          <template #default="{ row }">
            <router-link v-if="row.asset_id" :to="`/assets/${row.asset_id}`" class="asset-link">
              {{ row.asset_title || row.asset_code || '查看资产' }}
            </router-link>
            <span v-else class="muted">未匹配到平台资产</span>
          </template>
        </el-table-column>
        <el-table-column label="来源/说明" min-width="240">
          <template #default="{ row }">
            <a
              v-if="row.source_url"
              :href="row.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="source-link"
            >
              {{ row.source_url }}
            </a>
            <div class="description">{{ row.description || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="举报人" width="150">
          <template #default="{ row }">
            <div>{{ row.reporter_name || row.reporter_username || '匿名' }}</div>
            <div class="time-line">{{ row.contact || '未留联系方式' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="水印匹配" width="110">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.trace_verified ? 'success' : 'info'"
              effect="plain"
            >
              {{ row.trace_verified ? '已匹配' : '未匹配' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openDetail(row)">
              查看/处理
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && reports.length === 0" class="empty-reports">
        <el-empty description="暂无侵权线索" :image-size="72" />
      </div>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="loadReports"
        @current-change="loadReports"
      />
    </section>

    <el-dialog
      v-model="detailVisible"
      title="线索详情与处理"
      width="min(720px, 94vw)"
      @closed="clearPreview"
    >
      <el-skeleton v-if="detailLoading" animated :rows="5" />
      <template v-else-if="detail.id">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="线索编号">{{ detail.report_code }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusType(detail.status)" effect="plain">
              {{ statusLabel(detail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="匹配资产">
            <router-link v-if="detail.asset_id" :to="`/assets/${detail.asset_id}`">
              {{ detail.asset_title || detail.asset_code }}
            </router-link>
            <span v-else class="muted">未匹配</span>
          </el-descriptions-item>
          <el-descriptions-item label="水印编号">
            {{ detail.watermark_id || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="举报人">
            {{ detail.reporter_name || detail.reporter_username || '匿名' }}
          </el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ detail.contact || '—' }}</el-descriptions-item>
          <el-descriptions-item label="来源链接" :span="2">
            <a
              v-if="detail.source_url"
              :href="detail.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="source-link"
            >
              {{ detail.source_url }}
            </a>
            <span v-else class="muted">未提供</span>
          </el-descriptions-item>
          <el-descriptions-item label="情况说明" :span="2">
            {{ detail.description || '—' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.suspect_file_hash" label="文件指纹" :span="2">
            <span class="mono hash">{{ detail.suspect_file_hash }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.has_file" class="preview-block">
          <div class="preview-head">
            <span>举报文件</span>
            <el-button size="small" link type="primary" @click="downloadFile">下载原文件</el-button>
          </div>
          <img v-if="previewUrl" :src="previewUrl" alt="举报文件预览" class="preview-image" />
          <div v-else class="preview-placeholder">
            {{ previewNotImage ? '该文件不是图片，请下载查看' : '正在加载预览…' }}
          </div>
        </div>

        <div v-if="detail.review_comment" class="review-result">
          <strong>处理意见：</strong>{{ detail.review_comment }}
          <span v-if="detail.reviewer_name" class="muted"> · {{ detail.reviewer_name }}</span>
        </div>

        <div v-if="detail.can_review && !['confirmed', 'rejected'].includes(detail.status)" class="review-block">
          <el-input
            v-model="reviewComment"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            placeholder="处理意见（驳回时建议说明原因）"
          />
          <div class="review-actions">
            <el-button
              v-if="detail.status === 'pending'"
              :loading="reviewing"
              @click="review('start')"
            >
              开始处理
            </el-button>
            <el-button type="danger" plain :loading="reviewing" @click="review('reject')">
              驳回线索
            </el-button>
            <el-button type="primary" :loading="reviewing" @click="review('confirm')">
              确认侵权
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="patrolVisible"
      title="批量侵权巡检"
      width="min(680px, 94vw)"
      :close-on-click-modal="false"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="patrol-alert"
        title="上传疑似副本，系统批量提取水印"
        description="最多 20 个图片或 ZIP，每个不超过 20MB。匹配到已发布资产会自动生成待处理线索；未匹配文件不会被保留。"
      />
      <el-upload
        ref="patrolUploadRef"
        multiple
        :auto-upload="false"
        :limit="20"
        :on-change="handlePatrolChange"
        :on-remove="handlePatrolChange"
        accept="image/*,.zip"
      >
        <el-button plain>选择巡检文件</el-button>
        <template #tip>
          <span class="patrol-tip">支持 JPG、PNG、BMP、TIFF、WebP、ZIP</span>
        </template>
      </el-upload>
      <el-input
        v-model="patrolSourceUrl"
        placeholder="来源链接（可选，应用到本批全部文件）"
        class="patrol-source"
        maxlength="500"
      />

      <div v-if="patrolRunning" class="patrol-progress">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在提取水印并匹配资产，请稍候…</span>
      </div>

      <template v-if="patrolResult">
        <div class="patrol-summary">
          共 {{ patrolResult.total }} 个文件，匹配 {{ patrolResult.matched }} 个，
          异常 {{ patrolResult.errors || 0 }} 个
        </div>
        <el-table :data="patrolResult.items" size="small" class="patrol-table">
          <el-table-column prop="file" label="文件" min-width="160" show-overflow-tooltip />
          <el-table-column label="结果" min-width="200">
            <template #default="{ row }">
              <router-link v-if="row.matched" :to="`/assets/${row.asset_id}`" class="asset-link">
                {{ row.asset_title || row.asset_code }}
              </router-link>
              <span v-else class="muted">{{ row.message || '未匹配' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="线索编号" width="190">
            <template #default="{ row }">
              <span v-if="row.report_code" class="mono">{{ row.report_code }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <template #footer>
        <el-button @click="patrolVisible = false">
          {{ patrolResult ? '关闭' : '取消' }}
        </el-button>
        <el-button
          v-if="!patrolResult"
          type="primary"
          :loading="patrolRunning"
          :disabled="patrolFiles.length === 0 || patrolQueued"
          @click="startPatrol"
        >
          {{ patrolQueued ? '已提交' : '开始巡检' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { parseBackendDate } from '@/utils'
import { infringementApi, taskApi } from '@/api/modules'

const reports = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const counts = ref({})
const filters = reactive({ status: '', keyword: '', dateRange: [] })
const applied = reactive({ status: '', keyword: '', start_date: '', end_date: '' })

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref({})
const reviewComment = ref('')
const reviewing = ref(false)
const previewUrl = ref('')
const previewNotImage = ref(false)

const patrolVisible = ref(false)
const patrolRunning = ref(false)
const patrolFiles = ref([])
const patrolUploadRef = ref()
const patrolSourceUrl = ref('')
const patrolResult = ref(null)
const patrolQueued = ref(false)

const summaryItems = computed(() => [
  { key: 'pending', label: '待处理', value: counts.value.pending || 0, tone: 'pending' },
  { key: 'reviewing', label: '处理中', value: counts.value.reviewing || 0, tone: 'reviewing' },
  { key: 'confirmed', label: '已确认', value: counts.value.confirmed || 0, tone: 'confirmed' },
  { key: 'rejected', label: '已驳回', value: counts.value.rejected || 0, tone: 'rejected' }
])

const STATUS_LABELS = {
  pending: '待处理',
  reviewing: '处理中',
  confirmed: '已确认',
  rejected: '已驳回'
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

function statusType(status) {
  return {
    pending: 'warning',
    reviewing: 'info',
    confirmed: 'success',
    rejected: 'danger'
  }[status] || 'info'
}

function formatTime(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : '—'
}

function applyFilters() {
  applied.status = filters.status || ''
  applied.keyword = filters.keyword.trim()
  applied.start_date = filters.dateRange?.[0] || ''
  applied.end_date = filters.dateRange?.[1] || ''
  page.value = 1
  loadReports()
}

function resetFilters() {
  filters.status = ''
  filters.keyword = ''
  filters.dateRange = []
  applyFilters()
}

async function loadReports() {
  loading.value = true
  try {
    const response = await infringementApi.list({
      page: page.value,
      per_page: perPage.value,
      status: applied.status || undefined,
      keyword: applied.keyword || undefined,
      start_date: applied.start_date || undefined,
      end_date: applied.end_date || undefined
    })
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      reports.value = data.items || []
      total.value = data.total || 0
      counts.value = data.counts || {}
    } else {
      ElMessage.error(response.data?.message || '线索加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '线索加载失败')
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  await loadReports()
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = {}
  reviewComment.value = ''
  previewNotImage.value = false
  clearPreview()
  try {
    const response = await infringementApi.get(row.id)
    if (response.data?.code === 200) {
      detail.value = response.data.data || {}
      if (detail.value.has_file) loadPreview(detail.value.id)
    } else {
      ElMessage.error(response.data?.message || '线索详情加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '线索详情加载失败')
  } finally {
    detailLoading.value = false
  }
}

async function loadPreview(reportId) {
  try {
    const response = await infringementApi.getFile(reportId)
    const type = response.headers?.['content-type'] || 'application/octet-stream'
    if (!type.startsWith('image/')) {
      previewNotImage.value = true
      return
    }
    clearPreview()
    previewUrl.value = URL.createObjectURL(response.data)
  } catch {
    previewNotImage.value = true
  }
}

function clearPreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

async function downloadFile() {
  try {
    const response = await infringementApi.getFile(detail.value.id)
    const link = document.createElement('a')
    const url = URL.createObjectURL(response.data)
    link.href = url
    link.download = `${detail.value.report_code}-suspect`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '文件下载失败')
  }
}

async function review(action) {
  if (action !== 'start') {
    try {
      await ElMessageBox.confirm(
        action === 'confirm'
          ? '确认侵权后会通知举报人与资产权利人，此操作不可撤回。'
          : '驳回后会通知举报人与资产权利人，此操作不可撤回。',
        action === 'confirm' ? '确认侵权' : '驳回线索',
        { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }
  reviewing.value = true
  try {
    const response = await infringementApi.review(detail.value.id, {
      action,
      comment: reviewComment.value.trim()
    })
    if (response.data?.code === 200) {
      ElMessage.success('线索状态已更新')
      detail.value = response.data.data || detail.value
      await loadReports()
    } else {
      ElMessage.error(response.data?.message || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '处理失败')
  } finally {
    reviewing.value = false
  }
}

function openPatrol() {
  patrolVisible.value = true
  patrolFiles.value = []
  patrolSourceUrl.value = ''
  patrolResult.value = null
  patrolQueued.value = false
  patrolUploadRef.value?.clearFiles()
}

function handlePatrolChange(file, fileList) {
  const allowed = /\.(jpe?g|png|bmp|tiff?|webp|zip)$/i
  const valid = fileList.filter(item => item.raw && allowed.test(item.name))
  if (valid.length !== fileList.length) {
    ElMessage.warning('仅支持图片或 ZIP，其他文件不会提交巡检')
  }
  if (valid.length > 20) {
    ElMessage.warning('单次最多巡检 20 个文件')
  }
  patrolFiles.value = valid.slice(0, 20)
}

async function waitPatrolTask(taskId) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, 2000))
    try {
      const response = await taskApi.get(taskId)
      const task = response.data?.data
      if (!task) continue
      if (task.status === 'succeeded') return task
      if (['failed', 'cancelled'].includes(task.status)) {
        throw new Error(task.error_message || '巡检任务失败')
      }
    } catch (error) {
      if (error.message && !error.response) throw error
    }
  }
  throw new Error('巡检任务超时，请稍后在任务队列查看')
}

async function startPatrol() {
  if (patrolFiles.value.length === 0 || patrolRunning.value) return
  patrolRunning.value = true
  patrolResult.value = null
  try {
    const form = new FormData()
    patrolFiles.value.forEach(item => {
      if (item.raw) form.append('files', item.raw)
    })
    form.append('source_url', patrolSourceUrl.value.trim())
    const response = await infringementApi.patrol(form)
    if (response.data?.code !== 202) {
      ElMessage.error(response.data?.message || '巡检提交失败')
      return
    }
    const data = response.data.data || {}
    patrolQueued.value = true
    if (!data.worker_enabled) {
      ElMessage.warning('巡检任务已排队，但后台 worker 未启用')
      patrolRunning.value = false
      return
    }
    const task = await waitPatrolTask(data.task_id)
    patrolResult.value = task.result || { total: 0, matched: 0, items: [] }
    ElMessage.success(
      `巡检完成：匹配 ${patrolResult.value.matched || 0} 个文件`
    )
    await loadReports()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.message || '巡检失败')
  } finally {
    patrolRunning.value = false
  }
}

onMounted(loadAll)
onBeforeUnmount(clearPreview)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-infringements {
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

.patrol-alert {
  margin-bottom: 14px;
}

.patrol-tip {
  font-size: 12px;
  color: $text-placeholder;
}

.patrol-source {
  margin-top: 12px;
}

.patrol-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  font-size: 13px;
  color: $primary-dark;
}

.patrol-summary {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: $radius-sm;
  background: $bg-secondary;
  font-size: 13px;
  color: $text-secondary;
}

.patrol-table {
  margin-top: 10px;
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

  &.pending { color: $accent-color; }
  &.confirmed { color: $primary-color; }
  &.rejected { color: $error-color; }
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

.mono {
  font-family: $font-mono;
}

.report-code {
  font-size: 12px;
  color: $text-primary;
}

.time-line {
  font-size: 11px;
  color: $text-placeholder;
}

.asset-link,
.source-link {
  color: $primary-dark;
  text-decoration: none;
  word-break: break-all;

  &:hover { text-decoration: underline; }
}

.source-link {
  display: block;
  font-size: 12px;
}

.description {
  margin-top: 4px;
  font-size: 12px;
  color: $text-secondary;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.muted { color: $text-placeholder; }

.hash { font-size: 11px; word-break: break-all; }

.preview-block {
  margin-top: 16px;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.preview-image {
  display: block;
  max-width: 100%;
  max-height: 320px;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  object-fit: contain;
}

.preview-placeholder {
  padding: 24px;
  font-size: 12px;
  color: $text-placeholder;
  background: $bg-secondary;
  border-radius: $radius-sm;
}

.review-result {
  margin-top: 16px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
  color: $text-secondary;
  background: $bg-secondary;
  border-radius: $radius-sm;
}

.review-block {
  margin-top: 16px;
}

.review-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.empty-reports {
  padding: 24px 0;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

@media (max-width: $breakpoint-md) {
  .admin-infringements {
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
