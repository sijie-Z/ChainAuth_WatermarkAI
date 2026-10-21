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
          <span class="card-title">授权记录</span>
          <el-radio-group v-model="filterStatus" @change="handleFilterChange">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">审批中</el-radio-button>
            <el-radio-button value="active">已生效</el-radio-button>
            <el-radio-button value="rejected">已拒绝</el-radio-button>
            <el-radio-button value="expired">已过期</el-radio-button>
            <el-radio-button value="revoked">已撤销</el-radio-button>
          </el-radio-group>
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
          <el-table :data="licenses" stripe>
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
            <el-table-column prop="end_time" label="有效期" width="110">
              <template #default="{ row }">
                {{ row.end_time ? formatDate(row.end_time) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="申请时间" width="110">
              <template #default="{ row }">
                {{ formatDate(row.created_at) || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button size="small" @click="viewDetail(row)">详情</el-button>
                <el-button
                  size="small"
                  type="primary"
                  @click="downloadAsset(row)"
                  :disabled="row.status !== 'active' || !row.asset_id"
                >
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <EmptyState
            v-if="!loading && licenses.length === 0"
            :description="emptyDescription"
            :show-action="true"
            action-text="申请授权"
            @action="$router.push('/license/apply')"
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
    <el-dialog v-model="detailVisible" title="授权详情" width="min(600px, 92vw)">
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
        <el-descriptions-item label="使用期限">{{ detail.end_time ? formatDate(detail.end_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="使用范围">{{ formatScope(detail) }}</el-descriptions-item>
        <el-descriptions-item label="使用目的" :span="2">{{ detail.purpose || detail.usage_purpose || detail.usage_scope || '-' }}</el-descriptions-item>
        <el-descriptions-item label="区块链存证" :span="2">
          <span v-if="detail.tx_hash" class="mono">{{ detail.tx_hash }}</span>
          <span v-else>未上链</span>
        </el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">
          {{ detail.approve_comment || detail.adm2_review_comment || detail.adm1_review_comment || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { licenseApi, assetApi } from '@/api/modules'

const loading = ref(false)
const licenses = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const filterStatus = ref('')

const detailVisible = ref(false)
const detail = ref({})

// 审批中/已拒绝查询的是“我的申请”，其余状态查询的是“我的授权”
const APPLICATION_STATUSES = ['pending', 'rejected']
const isApplicationView = computed(() => APPLICATION_STATUSES.includes(filterStatus.value))
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

function handleFilterChange() {
  page.value = 1
  loadLicenses()
}

async function loadLicenses() {
  loading.value = true
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
      licenses.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('加载授权记录失败:', error)
    licenses.value = []
    total.value = 0
  } finally {
    loading.value = false
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
  try {
    const response = await assetApi.download(row.asset_id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.asset_code || 'asset')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载开始')
  } catch {
    ElMessage.error('下载失败，请确认已获得授权')
  }
}

function getLicenseType(type) {
  const map = {
    personal: '个人使用',
    academic: '学术研究',
    commercial: '商业使用',
    display: '展览展示',
    derivative: '衍生创作'
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
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadLicenses()
})
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
}
</style>
