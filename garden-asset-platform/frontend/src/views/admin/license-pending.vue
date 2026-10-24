<template>
  <div class="license-pending">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">待审批申请</h1>
        <p class="page-subtitle">审核资产授权申请，归档审批意见</p>
      </div>
      <div class="page-actions">
        <el-tag type="warning">{{ applications.length }} 条待处理</el-tag>
        <el-button type="primary" @click="loadApplications">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <div class="content-card">
      <el-table :data="applications" v-loading="loading" stripe>
        <el-table-column prop="application_code" label="申请编码" width="180" class-name="cell-code" />
        <el-table-column prop="asset_code" label="资产编码" width="180" class-name="cell-code">
          <template #default="{ row }">
            {{ row.asset_code || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.asset_title || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="license_type" label="授权类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" label="申请人" width="100">
          <template #default="{ row }">
            {{ row.applicant_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="当前阶段" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'adm1_approved' ? 'warning' : 'info'">
              {{ stageLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审批操作" width="190">
          <template #default="{ row }">
            <template v-if="canAct(row)">
              <el-button size="small" type="success" @click="openApproveDialog(row, 'approve')">
                通过
              </el-button>
              <el-button size="small" type="danger" @click="openApproveDialog(row, 'reject')">
                拒绝
              </el-button>
            </template>
            <span v-else class="stage-hint">{{ stageHint(row) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && applications.length === 0"
        description="当前阶段没有待审批申请"
        :image-size="72"
      />
    </div>

    <!-- 审批对话框 -->
    <el-dialog v-model="approveDialog.visible" :title="approveDialog.title" width="min(500px, 92vw)">
      <el-form :model="approveDialog.form" label-width="80px">
        <el-form-item label="申请信息">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="申请编号">{{ approveDialog.applicationCode }}</el-descriptions-item>
            <el-descriptions-item label="资产">{{ approveDialog.assetTitle }}</el-descriptions-item>
            <el-descriptions-item label="申请人">{{ approveDialog.applicantName }}</el-descriptions-item>
            <el-descriptions-item label="授权类型">{{ getLicenseType(approveDialog.licenseType) }}</el-descriptions-item>
            <el-descriptions-item label="用途">{{ approveDialog.purpose }}</el-descriptions-item>
            <el-descriptions-item label="申请时长">
              {{ approveDialog.durationMonths ? `${approveDialog.durationMonths} 个月` : '未指定' }}
            </el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ approveDialog.createdAt }}</el-descriptions-item>
          </el-descriptions>
        </el-form-item>

        <el-form-item label="审批意见" required>
          <div class="comment-presets">
            <button
              v-for="preset in commentPresets"
              :key="preset"
              type="button"
              class="comment-preset"
              @click="approveDialog.form.comment = preset"
            >
              {{ preset }}
            </button>
          </div>
          <el-input
            v-model="approveDialog.form.comment"
            type="textarea"
            :rows="3"
            placeholder="请输入审批意见，审批结果会写入申请记录"
          />
        </el-form-item>

        <el-form-item v-if="approveDialog.action === 'approve'" label="有效期">
          <el-date-picker
            v-model="approveDialog.form.valid_until"
            type="date"
            placeholder="留空则按申请时长计算"
            :disabled-date="disabledApproveDate"
          />
          <span class="field-hint">留空时按申请时长自动计算；可选日期必须晚于今天。</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button :disabled="approveDialog.loading" @click="approveDialog.visible = false">取消</el-button>
        <el-button
          :type="approveDialog.action === 'approve' ? 'success' : 'danger'"
          :loading="approveDialog.loading"
          @click="doApprove"
        >
          {{ approveDialog.action === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { parseBackendDate } from '@/utils'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { licenseApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const currentRole = computed(() => userStore.userRole)

function stageLabel(row) {
  return row.status === 'adm1_approved' ? '待二级复核' : '待一级审批'
}

function canAct(row) {
  const role = currentRole.value
  if (role === 'admin') return true
  if (['adm1', 'asset_admin'].includes(role)) return row.status === 'pending'
  if (['adm2', 'license_admin'].includes(role)) return row.status === 'adm1_approved'
  return false
}

function stageHint(row) {
  return row.status === 'pending' ? '由一级审批员处理' : '由二级审批员复核'
}

const loading = ref(false)
const applications = ref([])

const approveDialog = ref({
  visible: false,
  loading: false,
  title: '',
  action: '',
  applicationId: null,
  applicationCode: '',
  assetTitle: '',
  applicantName: '',
  licenseType: '',
  purpose: '',
  durationMonths: null,
  createdAt: '',
  form: {
    comment: '',
    valid_until: null
  }
})

const COMMENT_PRESETS = {
  approve: [
    '材料齐全，同意授权',
    '使用范围明确，准予通过',
    '授权范围与用途匹配，同意'
  ],
  reject: [
    '请补充用途说明后重新提交',
    '使用范围与授权类型不匹配',
    '申请材料不完整，暂不通过'
  ]
}

const commentPresets = computed(
  () => COMMENT_PRESETS[approveDialog.value.action] || []
)

function defaultValidUntil(durationMonths) {
  if (!durationMonths) return null
  const date = new Date()
  date.setDate(date.getDate() + durationMonths * 30)
  return date
}

function disabledApproveDate(date) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() <= today.getTime()
}

async function loadApplications() {
  loading.value = true
  try {
    const response = await licenseApi.getPending()
    if (response.data?.code === 200) {
      const data = response.data.data
      applications.value = Array.isArray(data) ? data : (data?.items || [])
    }
  } catch (error) {
    ElMessage.error('加载申请失败')
  } finally {
    loading.value = false
  }
}

function openApproveDialog(row, action) {
  approveDialog.value = {
    visible: true,
    loading: false,
    title: action === 'approve' ? '审批通过' : '审批拒绝',
    action,
    applicationId: row.id,
    applicationCode: row.application_code || `#${row.id}`,
    assetTitle: row.asset_title || '-',
    applicantName: row.applicant_name || '-',
    licenseType: row.license_type,
    purpose: row.purpose || row.usage_scope || '-',
    durationMonths: row.duration_months,
    createdAt: formatDate(row.created_at),
    form: {
      comment: '',
      valid_until: action === 'approve' ? defaultValidUntil(row.duration_months) : null
    }
  }
}

async function doApprove() {
  if (!approveDialog.value.form.comment) {
    ElMessage.warning('请输入审批意见')
    return
  }

  try {
    approveDialog.value.loading = true
    const data = {
      action: approveDialog.value.action,
      comment: approveDialog.value.form.comment,
      valid_until: approveDialog.value.form.valid_until
    }

    const response = await licenseApi.approve(approveDialog.value.applicationId, data)
    if (response.data.code === 200) {
      ElMessage.success('审批成功')
      approveDialog.value.visible = false
      loadApplications()
    } else {
      ElMessage.error(response.data.message || '审批失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '审批失败')
  } finally {
    approveDialog.value.loading = false
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

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(() => {
  loadApplications()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-pending {
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

.stage-hint {
  font-size: 11px;
  color: $text-placeholder;
}

.field-hint {
  display: block;
  width: 100%;
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.6;
  color: $text-placeholder;
}

// 常用审批意见
.comment-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.comment-preset {
  padding: 3px 9px;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  background: $bg-secondary;
  font-size: 12px;
  color: $text-secondary;
  cursor: pointer;

  &:hover {
    border-color: $primary-color;
    color: $primary-dark;
  }
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .license-pending {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .page-actions {
    width: 100%;
    justify-content: space-between;
  }

  .content-card {
    padding: 16px;
  }
}
</style>
