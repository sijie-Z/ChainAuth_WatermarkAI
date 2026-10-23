<template>
  <div class="license-my">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">我的授权</h1>
    </header>

    <el-card class="license-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ isApplicationView ? '我的申请' : '授权记录' }}</span>
          <div class="header-filters">
            <el-radio-group v-model="viewMode" @change="handleViewChange">
              <el-radio-button value="licenses">授权记录</el-radio-button>
              <el-radio-button value="applications">申请记录</el-radio-button>
            </el-radio-group>
            <el-radio-group v-model="filterStatus" @change="handleFilterChange">
              <el-radio-button
                v-for="option in statusOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>

      <el-skeleton :loading="loading" animated :rows="6">
        <template #template>
          <div v-for="i in 6" :key="i" class="skeleton-row">
            <div style="display: flex; gap: 24px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--el-border-color-lighter)">
              <el-skeleton-item variant="text" style="width: 160px" />
              <el-skeleton-item variant="text" style="flex: 1" />
              <el-skeleton-item variant="text" style="width: 80px" />
              <el-skeleton-item variant="text" style="width: 60px" />
              <el-skeleton-item variant="text" style="width: 120px" />
              <el-skeleton-item variant="text" style="width: 120px" />
            </div>
          </div>
        </template>
        <template #default>
          <el-alert
            v-if="loadError"
            type="error"
            :closable="false"
            show-icon
            title="授权记录加载失败"
            class="load-error"
          >
            <el-button size="small" @click="loadLicenses">重试</el-button>
          </el-alert>
          <el-table v-else class="license-table" :data="licenses" stripe row-key="id" style="cursor: pointer" @row-click="viewDetail">
            <el-table-column label="编码" width="170">
              <template #default="{ row }">
                <span class="mono">{{ row.license_code || row.application_code || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="资产标题" min-width="170" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.asset_title || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="资产编码" width="160">
              <template #default="{ row }">
                <span class="mono">{{ row.asset_code || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="license_type" label="类型" width="85">
              <template #default="{ row }">
                <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusMeta(row.status).type" size="small">
                  {{ getStatusMeta(row.status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="end_time" :label="isApplicationView ? '申请时长' : '有效期'" width="110">
              <template #default="{ row }">
                <span v-if="isApplicationView">
                  {{ row.duration_months ? `${row.duration_months} 个月` : '-' }}
                </span>
                <span v-else>{{ row.end_time ? formatDate(row.end_time) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="isApplicationView ? '提交时间' : '生效时间'" width="110">
              <template #default="{ row }">
                {{ formatDate(isApplicationView ? row.created_at : (row.start_time || row.created_at)) || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="190">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click.stop="viewDetail(row)">详情</el-button>
                <el-button
                  v-if="!isApplicationView"
                  size="small"
                  link
                  type="primary"
                  :loading="downloadingId === row.id"
                  @click.stop="downloadAsset(row)"                  :disabled="row.status !== 'active' || !row.asset_id"
                  :title="row.status !== 'active' ? '授权未生效或已过期，无法下载' : '下载资产'"
                >
                  下载
                </el-button>
                <el-button
                  v-if="isApplicationView && ['pending', 'adm1_approved'].includes(row.status)"
                  size="small"
                  link
                  type="danger"
                  @click="cancelApplication(row)"
                >
                  撤回
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 移动端卡片列表：避免横向拖动表格找操作按钮 -->
          <div class="license-mobile-list">
            <article
              v-for="row in licenses"
              :key="`mobile-${row.id}`"
              class="license-mobile-card"
              @click="viewDetail(row)"
            >
              <header class="mobile-card-head">
                <span class="mono">{{ row.license_code || row.application_code || '-' }}</span>
                <el-tag :type="getStatusMeta(row.status).type" size="small">
                  {{ getStatusMeta(row.status).label }}
                </el-tag>
              </header>
              <h3>{{ row.asset_title || '未知资产' }}</h3>
              <p class="mono mobile-asset-code">{{ row.asset_code || '-' }}</p>
              <div class="mobile-card-meta">
                <span>{{ getLicenseType(row.license_type) }}</span>
                <span v-if="isApplicationView">{{ row.duration_months ? `${row.duration_months} 个月` : '未指定时长' }}</span>
                <span v-else>{{ row.end_time ? formatDate(row.end_time) : '未设置有效期' }}</span>
              </div>
              <div class="mobile-card-actions">
                <el-button link type="primary" size="small" @click.stop="viewDetail(row)">详情</el-button>
                <el-button
                  v-if="!isApplicationView"
                  link
                  type="primary"
                  size="small"
                  :loading="downloadingId === row.id"
                  :disabled="row.status !== 'active' || !row.asset_id"
                  @click.stop="downloadAsset(row)"
                >
                  下载
                </el-button>
                <el-button
                  v-if="isApplicationView && ['pending', 'adm1_approved'].includes(row.status)"
                  link
                  type="danger"
                  size="small"
                  @click.stop="cancelApplication(row)"
                >
                  撤回
                </el-button>
              </div>
            </article>
          </div>

          <EmptyState
            v-if="!loading && !loadError && licenses.length === 0"
            :description="emptyDescription"
            :show-action="true"
            action-text="去资产档案"
            @action="$router.push('/assets')"
          />
        </template>
      </el-skeleton>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLicenses"
        @current-change="loadLicenses"
        class="license-pagination"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" :title="isApplicationView ? '申请详情' : '授权详情'" width="min(620px, 92vw)">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="编码">{{ detail.license_code || detail.application_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusMeta(detail.status).type" size="small">
            {{ getStatusMeta(detail.status).label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产标题" :span="2">{{ detail.asset_title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产编码">{{ detail.asset_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="授权类型">{{ getLicenseType(detail.license_type) }}</el-descriptions-item>
        <el-descriptions-item v-if="!isApplicationView" label="授权版本">
          {{ detail.version_no ? `v${detail.version_no}` : '历史授权（不限版本）' }}
        </el-descriptions-item>
        <el-descriptions-item label="使用期限">
          {{ detail.end_time ? formatDate(detail.end_time) : (detail.duration_months ? `${detail.duration_months} 个月` : '-') }}
        </el-descriptions-item>
        <el-descriptions-item label="使用范围">{{ formatScope(detail) }}</el-descriptions-item>
        <el-descriptions-item label="使用目的" :span="2">{{ detail.purpose || detail.usage_purpose || detail.usage_scope || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.scope_summary" label="执行范围" :span="2">
          {{ detail.scope_summary }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.max_downloads" label="下载用量">
          {{ detail.download_count || 0 }} / {{ detail.max_downloads }}
        </el-descriptions-item>
        <el-descriptions-item v-if="isApplicationView" label="一级审批">
          {{ getStatusMeta(detail.adm1_status).label }}
        </el-descriptions-item>
        <el-descriptions-item v-if="isApplicationView" label="二级审批">
          {{ getStatusMeta(detail.adm2_status).label }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.tx_hash" label="区块链存证" :span="2">
          <span class="mono">{{ detail.tx_hash }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">
          {{ detail.adm2_review_comment || detail.adm1_review_comment || detail.approve_comment || '-' }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button
          v-if="!isApplicationView && detail.license_code && ['active', 'expired', 'revoked'].includes(detail.status)"
          type="primary"
          :loading="contractLoading"
          @click="openContract(detail)"
        >
          查看授权合同
        </el-button>
        <el-button
          v-if="isApplicationView && ['pending', 'adm1_approved'].includes(detail.status)"
          type="danger"
          plain
          @click="cancelApplication(detail)"
        >
          撤回申请
        </el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 合同对话框 -->
    <el-dialog v-model="contractVisible" title="数字资产使用授权合同" width="min(720px, 92vw)">
      <pre class="contract-content">{{ contractContent }}</pre>
      <template #footer>
        <el-button type="primary" @click="copyContract">复制全文</el-button>
        <el-button @click="contractVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { parseBackendDate } from '@/utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { licenseApi, assetApi } from '@/api/modules'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(false)
const loadError = ref(false)
const downloadingId = ref(null)
const licenses = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const filterStatus = ref('')
const viewMode = ref('licenses')

const detailVisible = ref(false)
const detail = ref({})
const contractVisible = ref(false)
const contractContent = ref('')
const contractLoading = ref(false)

const LICENSE_STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'active', label: '已生效' },
  { value: 'expired', label: '已过期' },
  { value: 'revoked', label: '已撤销' }
]
const APPLICATION_STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'pending', label: '审批中' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' },
  { value: 'cancelled', label: '已撤回' }
]
const isApplicationView = computed(() => viewMode.value === 'applications')
const statusOptions = computed(() => isApplicationView.value ? APPLICATION_STATUS_OPTIONS : LICENSE_STATUS_OPTIONS)
const emptyDescription = computed(() => isApplicationView.value ? '暂无申请记录' : '暂无授权记录')

const STATUS_META = {
  pending: { label: '审批中', type: 'warning' },
  adm1_approved: { label: '一级已通过', type: 'warning' },
  adm2_approved: { label: '二级已通过', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  active: { label: '生效中', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' },
  expired: { label: '已过期', type: 'info' },
  revoked: { label: '已撤销', type: 'danger' }
}

function getStatusMeta(status) {
  return STATUS_META[status] || { label: status || '未知', type: 'info' }
}

function handleViewChange() {
  filterStatus.value = ''
  page.value = 1
  loadLicenses()
}

function handleFilterChange() {
  page.value = 1
  loadLicenses()
}

async function loadLicenses() {
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: page.value,
      per_page: perPage.value
    }
    if (filterStatus.value) {
      // “审批中”同时包含待一级审批与一级已通过、待二级审批
      params.status = (isApplicationView.value && filterStatus.value === 'pending')
        ? 'in_progress'
        : filterStatus.value
    }

    const response = isApplicationView.value
      ? await licenseApi.myApplications(params)
      : await licenseApi.getMyLicenses(params)

    if (response.data?.code === 200) {
      const data = response.data.data
      const items = Array.isArray(data) ? data : (data?.items || [])
      licenses.value = items
      total.value = Array.isArray(data) ? items.length : (data?.total || 0)
    } else {
      loadError.value = true
    }
  } catch (error) {
    console.error('加载授权记录失败:', error)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function cancelApplication(row) {
  if (!row?.id || row.status === 'cancelled') return
  try {
    await ElMessageBox.confirm(
      '撤回后该申请将不再进入审批，需要时可重新提交。确定撤回吗？',
      '撤回授权申请',
      { type: 'warning', confirmButtonText: '撤回申请', cancelButtonText: '继续等待' }
    )
  } catch {
    return
  }

  try {
    const response = await licenseApi.cancelApplication(row.id)
    if (response.data?.code === 200) {
      ElMessage.success('申请已撤回')
      detailVisible.value = false
      loadLicenses()
    } else {
      ElMessage.error(response.data?.message || '撤回失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '撤回失败')
  }
}

async function openContract(row) {
  if (!row?.id || contractLoading.value) return
  contractLoading.value = true
  try {
    const response = await licenseApi.getContract(row.id)
    if (response.data?.code === 200) {
      contractContent.value = response.data.data?.contract_content || '合同内容暂不可用'
      contractVisible.value = true
    } else {
      ElMessage.error(response.data?.message || '合同加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '合同加载失败')
  } finally {
    contractLoading.value = false
  }
}

async function copyContract() {
  try {
    await navigator.clipboard.writeText(contractContent.value)
    ElMessage.success('合同全文已复制')
  } catch {
    ElMessage.warning('浏览器未允许复制，请手动选择文本')
  }
}

function viewDetail(row) {
  detail.value = row
  detailVisible.value = true
}

async function downloadAsset(row) {
  if (!row.asset_id) {
    ElMessage.warning('资产信息缺失')
    return
  }
  if (downloadingId.value) return
  downloadingId.value = row.id
  try {
    const params = {}
    if (row.usage_purpose_code) params.purpose = row.usage_purpose_code
    if (['中国大陆', '中国港澳台', '全球', '海外'].includes(row.territory)) {
      params.territory = row.territory
    }
    const response = await assetApi.download(row.asset_id, params)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${row.asset_code}.${(row.file_format || 'bin').toLowerCase()}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    const fingerprint = response.headers?.['x-download-fingerprint']
    ElMessage.success(
      fingerprint ? `下载开始，指纹 ${fingerprint}` : '下载开始'
    )
  } catch (error) {
    let message = '下载失败，请确认授权仍然有效'
    const data = error.response?.data
    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text())
        message = parsed.message || message
      } catch {
        // 保留默认提示
      }
    } else if (data?.message) {
      message = data.message
    }
    ElMessage.error(message)
  } finally {
    downloadingId.value = null
  }
}

function getLicenseType(type) {
  const map = {
    personal: '个人使用',
    non_commercial: '非商业使用',
    academic: '学术研究',
    commercial: '商业使用',
    commercial_ad: '商业-广告',
    commercial_product: '商业-产品',
    commercial_publish: '商业-出版',
    display: '展览展示',
    derivative: '衍生创作',
    exclusive: '独家授权'
  }
  return map[type] || type || '-'
}

function formatScope(detail) {
  if (Array.isArray(detail.scope) && detail.scope.length > 0) {
    return detail.scope.join('、')
  }
  return detail.usage_scope || '-'
}

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(() => {
  applyTabFromQuery()
  loadLicenses()
})

watch(() => route.query.tab, () => {
  applyTabFromQuery()
  page.value = 1
  loadLicenses()
})

function applyTabFromQuery() {
  if (route.query.tab === 'pending') {
    viewMode.value = 'applications'
    filterStatus.value = 'pending'
  } else if (route.query.tab === 'rejected') {
    viewMode.value = 'applications'
    filterStatus.value = 'rejected'
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-my {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-3xl;
  min-height: 100vh;
  background: $bg-primary;
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

.license-card {
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
  flex-wrap: wrap;
  gap: $spacing-sm $spacing-md;
}

.header-filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-sm $spacing-md;
}

.load-error {
  margin-bottom: $spacing-md;
}

.license-mobile-list {
  display: none;
}

.license-mobile-card {
  padding: 14px;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  background: $bg-card;
  cursor: pointer;

  & + .license-mobile-card {
    margin-top: 10px;
  }

  .mobile-card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 11px;
    color: $text-placeholder;
  }

  h3 {
    font-size: 15px;
    font-weight: 500;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .mobile-asset-code {
    font-size: 11px;
    color: $text-placeholder;
    margin-bottom: 8px;
  }

  .mobile-card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    font-size: 12px;
    color: $text-secondary;
    padding-top: 8px;
    border-top: 1px solid $border-light;
  }

  .mobile-card-actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;

    :deep(.el-button) {
      margin-left: 0;
    }
  }
}

.contract-content {
  max-height: 56vh;
  overflow: auto;
  margin: 0;
  padding: $spacing-xl;
  background: $bg-secondary;
  border: 1px solid $border-light;
  border-radius: $radius-sm;
  font-family: $font-family;
  font-size: 13px;
  line-height: 1.9;
  color: $text-primary;
  white-space: pre-wrap;
  word-break: break-word;
}

.card-title {
  font-family: $font-display;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.license-pagination {
  margin-top: $spacing-xl;
  justify-content: center;
}

.mono {
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.02em;
  word-break: break-all;
}

@media (max-width: $breakpoint-md) {
  .license-my {
    padding: $spacing-lg;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .license-card :deep(.el-radio-group) {
    flex-wrap: wrap;
    row-gap: $spacing-xs;
  }

  .license-table {
    display: none;
  }

  .license-mobile-list {
    display: block;
  }
}
</style>
