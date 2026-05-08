<template>
  <div class="license-approved">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>已审批申请</span>
          <el-radio-group v-model="filterStatus" @change="loadLicenses">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="approved">已通过</el-radio-button>
            <el-radio-button label="rejected">已拒绝</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="licenses" v-loading="loading" stripe>
        <el-table-column prop="license_code" label="授权编码" width="180" />
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="license_type" label="授权类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="licensee_name" label="授权方" width="100" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'rejected' ? 'danger' : 'info'" size="small">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="valid_until" label="有效期" width="140">
          <template #default="{ row }">
            {{ row.valid_until ? formatDate(row.valid_until) : '永久' }}
          </template>
        </el-table-column>
        <el-table-column prop="approver_name" label="审批人" width="100" />
        <el-table-column prop="approved_at" label="审批时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.approved_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
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
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="授权详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="授权编码">{{ detailDialog.license_code }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailDialog.status === 'active' ? 'success' : 'danger'">
            {{ getStatusName(detailDialog.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产标题">{{ detailDialog.asset_title }}</el-descriptions-item>
        <el-descriptions-item label="授权类型">{{ getLicenseType(detailDialog.license_type) }}</el-descriptions-item>
        <el-descriptions-item label="授权方">{{ detailDialog.licensee_name }}</el-descriptions-item>
        <el-descriptions-item label="申请方">{{ detailDialog.applicant_name }}</el-descriptions-item>
        <el-descriptions-item label="有效期">{{ detailDialog.valid_until ? formatDate(detailDialog.valid_until) : '永久' }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ detailDialog.approver_name }}</el-descriptions-item>
        <el-descriptions-item label="申请用途" :span="2">{{ detailDialog.purpose }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ detailDialog.approve_comment }}</el-descriptions-item>
        <el-descriptions-item label="区块链存证">
          {{ detailDialog.tx_hash || '未上链' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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

async function loadLicenses() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
      status: filterStatus.value
    }
    const response = await licenseApi.getApproved(params)
    if (response.data.code === 200) {
      licenses.value = response.data.data.items
      total.value = response.data.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
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

function downloadContract(row) {
  if (row.contract_file) {
    window.open(row.contract_file, '_blank')
  } else if (row.asset_id) {
    window.open(`/api/assets/${row.asset_id}/download`, '_blank')
  } else {
    ElMessage.warning('暂无合同文件')
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

function getStatusName(status) {
  const map = {
    active: '生效',
    expired: '过期',
    rejected: '拒绝',
    revoked: '撤销'
  }
  return map[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadLicenses()
})
</script>

<style scoped>
.license-approved {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>