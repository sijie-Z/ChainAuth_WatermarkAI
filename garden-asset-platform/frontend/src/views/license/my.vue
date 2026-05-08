<template>
  <div class="license-my">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>我的授权</span>
          <el-radio-group v-model="filterStatus" @change="loadLicenses">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="pending">审批中</el-radio-button>
            <el-radio-button label="active">已生效</el-radio-button>
            <el-radio-button label="rejected">已拒绝</el-radio-button>
            <el-radio-button label="expired">已过期</el-radio-button>
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
            <el-table-column prop="license_code" label="授权编码" width="180" />
            <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="license_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getLicenseType(row.license_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <StatusTag :status="row.status" />
              </template>
            </el-table-column>
            <el-table-column prop="valid_until" label="有效期" width="140">
              <template #default="{ row }">
                {{ row.valid_until ? formatDate(row.valid_until) : '永久' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="申请时间" width="140">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="viewDetail(row)">详情</el-button>
                <el-button size="small" type="primary" @click="downloadAsset(row)" :disabled="row.status !== 'active'">
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <EmptyState
            v-if="!loading && licenses.length === 0"
            description="暂无授权记录"
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
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="授权详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="授权编码">{{ detail.license_code }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <StatusTag :status="detail.status" />
        </el-descriptions-item>
        <el-descriptions-item label="资产标题" :span="2">{{ detail.asset_title }}</el-descriptions-item>
        <el-descriptions-item label="授权类型">{{ getLicenseType(detail.license_type) }}</el-descriptions-item>
        <el-descriptions-item label="使用期限">{{ detail.valid_until ? formatDate(detail.valid_until) : '永久' }}</el-descriptions-item>
        <el-descriptions-item label="使用范围" :span="2">{{ detail.scope?.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="使用目的" :span="2">{{ detail.purpose }}</el-descriptions-item>
        <el-descriptions-item label="区块链存证" :span="2">
          <span v-if="detail.tx_hash" class="mono">{{ detail.tx_hash }}</span>
          <span v-else>未上链</span>
        </el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ detail.approve_comment || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { licenseApi, assetApi } from '@/api/modules'

const loading = ref(false)
const licenses = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const filterStatus = ref('')

const detailVisible = ref(false)
const detail = ref({})

async function loadLicenses() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
      status: filterStatus.value
    }
    const response = await licenseApi.getMyLicenses(params)
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
  return map[type] || type
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
  padding: $spacing-lg;
  min-height: 100vh;
  background: $bg-primary;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mono {
  font-family: 'Courier New', monospace;
  font-size: $font-size-xs;
  word-break: break-all;
}
</style>
