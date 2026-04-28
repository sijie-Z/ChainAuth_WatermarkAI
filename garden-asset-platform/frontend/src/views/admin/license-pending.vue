<template>
  <div class="license-pending">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>待审批申请</span>
          <el-tag type="warning">{{ applications.length }} 条待处理</el-tag>
        </div>
      </template>

      <el-table :data="applications" v-loading="loading" stripe>
        <el-table-column prop="application_code" label="申请编码" width="180" />
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="license_type" label="授权类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" label="申请人" width="100" />
        <el-table-column prop="purpose" label="用途" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="申请时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="审批操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="openApproveDialog(row, 'approve')">
              通过
            </el-button>
            <el-button size="small" type="danger" @click="openApproveDialog(row, 'reject')">
              拒绝
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 审批对话框 -->
    <el-dialog v-model="approveDialog.visible" :title="approveDialog.title" width="500px">
      <el-form :model="approveDialog.form" label-width="80px">
        <el-form-item label="申请信息">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="资产">{{ approveDialog.assetTitle }}</el-descriptions-item>
            <el-descriptions-item label="申请人">{{ approveDialog.applicantName }}</el-descriptions-item>
            <el-descriptions-item label="授权类型">{{ getLicenseType(approveDialog.licenseType) }}</el-descriptions-item>
            <el-descriptions-item label="用途">{{ approveDialog.purpose }}</el-descriptions-item>
          </el-descriptions>
        </el-form-item>

        <el-form-item label="审批意见" required>
          <el-input
            v-model="approveDialog.form.comment"
            type="textarea"
            :rows="3"
            placeholder="请输入审批意见"
          />
        </el-form-item>

        <el-form-item v-if="approveDialog.action === 'approve'" label="有效期">
          <el-date-picker
            v-model="approveDialog.form.valid_until"
            type="date"
            placeholder="选择有效期"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="approveDialog.visible = false">取消</el-button>
        <el-button :type="approveDialog.action === 'approve' ? 'success' : 'danger'" @click="doApprove">
          {{ approveDialog.action === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { licenseApi } from '@/api/modules'

const loading = ref(false)
const applications = ref([])

const approveDialog = ref({
  visible: false,
  title: '',
  action: '',
  applicationId: null,
  assetTitle: '',
  applicantName: '',
  licenseType: '',
  purpose: '',
  form: {
    comment: '',
    valid_until: null
  }
})

async function loadApplications() {
  loading.value = true
  try {
    const response = await licenseApi.getPending()
    if (response.data.code === 200) {
      applications.value = response.data.data
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
    title: action === 'approve' ? '审批通过' : '审批拒绝',
    action,
    applicationId: row.id,
    assetTitle: row.asset_title,
    applicantName: row.applicant_name,
    licenseType: row.license_type,
    purpose: row.purpose,
    form: {
      comment: '',
      valid_until: null
    }
  }
}

async function doApprove() {
  if (!approveDialog.value.form.comment) {
    ElMessage.warning('请输入审批意见')
    return
  }

  try {
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
    }
  } catch (error) {
    ElMessage.error('审批失败')
  }
}

function getLicenseType(type) {
  const map = {
    personal: '个人使用',
    commercial: '商业使用',
    academic: '学术研究',
    display: '展览展示',
    derivative: '衍生创作'
  }
  return map[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadApplications()
})
</script>

<style scoped>
.license-pending {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>