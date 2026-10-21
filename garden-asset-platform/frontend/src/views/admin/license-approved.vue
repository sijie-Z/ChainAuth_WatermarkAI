<template>
  <div class="license-approved">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">已审批申请</h1>
        <p class="page-subtitle">已审批授权的归档查询与合同下载</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="loadLicenses">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <div class="content-card">
      <div class="filter-bar">
        <el-radio-group v-model="filterStatus" @change="handleFilterChange">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">审批中</el-radio-button>
          <el-radio-button value="active">生效中</el-radio-button>
          <el-radio-button value="expired">已过期</el-radio-button>
          <el-radio-button value="revoked">已撤销</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="licenses" v-loading="loading" stripe>
        <el-table-column prop="license_code" label="授权编码" width="180" class-name="cell-code">
          <template #default="{ row }">
            {{ row.license_code || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.asset_title || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="license_type" label="授权类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="licensee_name" label="被授权方" width="100">
          <template #default="{ row }">
            {{ row.licensee_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="有效期" width="140">
          <template #default="{ row }">
            {{ row.end_time ? formatDate(row.end_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="approver_name" label="审批人" width="100">
          <template #default="{ row }">
            {{ row.approver_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="approved_at" label="审批时间" width="140">
          <template #default="{ row }">
            {{ row.approved_at ? formatDate(row.approved_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="downloadContract(row)" :disabled="row.status !== 'active'">
              合同
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLicenses"
        @current-change="loadLicenses"
      />
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="授权详情" width="min(600px, 92vw)">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="授权编码">{{ detailDialog.license_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailDialog.status)">
            {{ getStatusName(detailDialog.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产标题">{{ detailDialog.asset_title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="授权类型">{{ getLicenseType(detailDialog.license_type) }}</el-descriptions-item>
        <el-descriptions-item label="被授权方">{{ detailDialog.licensee_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请方">{{ detailDialog.applicant_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="有效期">{{ detailDialog.end_time ? formatDate(detailDialog.end_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ detailDialog.approver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请用途" :span="2">{{ detailDialog.purpose || detailDialog.usage_scope || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ detailDialog.approve_comment || '-' }}</el-descriptions-item>
        <el-descriptions-item label="区块链存证">
          <span class="hash-text">{{ detailDialog.tx_hash || '未上链' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { parseBackendDate } from '@/utils'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { licenseApi } from '@/api/modules'

const loading = ref(false)
const licenses = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const filterStatus = ref('')

const detailDialog = ref({
  visible: false
})

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
      params.status = filterStatus.value
    }
    const response = await licenseApi.getApproved(params)
    if (response.data?.code === 200) {
      licenses.value = response.data.data?.items || []
      total.value = response.data.data?.total || 0
    }
  } catch (error) {
    console.error('加载授权记录失败:', error)
  } finally {
    loading.value = false
  }
}

function viewDetail(row) {
  detailDialog.value = {
    visible: true,
    ...row
  }
}

// 合同按服务端生成的正文下载为文本，不再回退到资产文件
async function downloadContract(row) {
  if (!row?.id) {
    ElMessage.warning('授权记录不存在')
    return
  }

  try {
    const response = await licenseApi.getContract(row.id)
    if (response.data?.code !== 200) {
      ElMessage.warning(response.data?.message || '合同暂不可用')
      return
    }
    const content = response.data.data?.contract_content || ''
    if (!content) {
      ElMessage.warning('合同内容为空')
      return
    }
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const objectUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = `${row.license_code || row.asset_code || 'license'}-contract.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(objectUrl)
    ElMessage.success('合同下载开始')
  } catch (error) {
    console.error('下载合同失败:', error)
    ElMessage.error(error.response?.data?.message || '合同下载失败，请稍后重试')
  }
}

function getLicenseType(type) {
  const map = {
    personal: '个人使用',
    non_commercial: '非商业使用',
    commercial: '商业使用',
    commercial_ad: '商业-广告',
    commercial_product: '商业-产品',
    commercial_publish: '商业-出版',
    academic: '学术研究',
    display: '展览展示',
    derivative: '衍生创作',
    exclusive: '独家授权'
  }
  return map[type] || type || '-'
}

function getStatusName(status) {
  const map = {
    pending: '审批中',
    active: '生效',
    expired: '过期',
    rejected: '拒绝',
    revoked: '撤销'
  }
  return map[status] || status || '-'
}

function getStatusType(status) {
  const map = {
    active: 'success',
    pending: 'warning',
    expired: 'info',
    rejected: 'danger',
    revoked: 'danger'
  }
  return map[status] || 'info'
}

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(() => {
  loadLicenses()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-approved {
  min-height: 100%;
  padding: 24px 28px 32px;
}

// ========== 页面头部 ==========
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    font-family: $font-display;
    font-size: 22px;
    font-weight: $font-weight-semibold;
    line-height: $line-height-tight;
    color: $text-primary;
    letter-spacing: 0.01em;
  }

  .page-subtitle {
    margin-top: 6px;
    font-size: 13px;
    color: $text-secondary;
  }
}

.page-actions {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  flex-shrink: 0;
}

// ========== 内容卡片 ==========
.content-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-xl;
}

// ========== 状态筛选 ==========
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

// 按钮内图标与文字间距
:deep(.el-button > span) {
  gap: 6px;
  align-items: center;
}

// 台账编码使用等宽字体
:deep(.cell-code) {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

.hash-text {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  word-break: break-all;
}

:deep(.el-pagination) {
  margin-top: $spacing-xl;
  justify-content: center;
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .license-approved {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .content-card {
    padding: 16px;
  }

  .filter-bar {
    overflow-x: auto;

    :deep(.el-radio-group) {
      flex-shrink: 0;
    }
  }

  :deep(.el-pagination) {
    flex-wrap: wrap;
    row-gap: $spacing-sm;
  }
}
</style>
