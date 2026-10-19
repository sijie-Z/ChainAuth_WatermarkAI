<template>
  <div class="admin-blockchain">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">区块链存证管理</h1>
        <p class="page-subtitle">链上存证记录与完整性验证</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <!-- 区块链状态 -->
    <div class="chain-stats">
      <div class="stat-tile">
        <div class="stat-value">{{ chainStatus.totalCertificates }}</div>
        <div class="stat-label">存证总数</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value">{{ chainStatus.pendingAssets }}</div>
        <div class="stat-label">待上链资产</div>
      </div>
      <div class="stat-tile">
        <div class="stat-value is-text" :class="{ 'is-ok': chainStatus.nodeStatus === '正常' }">
          {{ chainStatus.nodeStatus }}
        </div>
        <div class="stat-label">节点状态</div>
      </div>
    </div>

    <!-- 批量上链 -->
    <div class="content-card">
      <div class="card-head">
        <h2 class="card-title">批量上链存证</h2>
      </div>
      <el-form inline class="filter-form">
        <el-form-item label="待上链资产">
          <el-select v-model="batchRegister.assets" multiple placeholder="选择资产" filterable>
            <el-option
              v-for="a in pendingAssets"
              :key="a.id"
              :label="`${a.asset_code} - ${a.title}`"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="batchRegister.loading" @click="doBatchRegister">
            批量上链
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 存证记录 -->
    <div class="content-card">
      <div class="card-head">
        <h2 class="card-title">存证记录</h2>
      </div>
      <el-table :data="certificates" v-loading="logsLoading" stripe>
        <el-table-column prop="certificate_id" label="证书ID" width="180" class-name="cell-code" />
        <el-table-column prop="asset_code" label="资产编码" width="180" class-name="cell-code" />
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="tx_hash" label="交易哈希" width="200">
          <template #default="{ row }">
            <span class="hash">{{ row.tx_hash }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="block_number" label="区块号" width="100" />
        <el-table-column prop="confirmed_at" label="存证时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.confirmed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewCertificate(row)">查看</el-button>
            <el-button size="small" type="primary" @click="verifyAsset(row)">验证</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { blockchainApi, assetApi } from '@/api/modules'

const router = useRouter()

const chainStatus = ref({
  totalCertificates: 0,
  pendingAssets: 0,
  nodeStatus: '正常'
})

const pendingAssets = ref([])
const certificates = ref([])
const logsLoading = ref(false)

const batchRegister = ref({
  assets: [],
  loading: false
})

async function loadStatus() {
  try {
    const response = await blockchainApi.getStatus()
    if (response.data.code === 200) {
      chainStatus.value = response.data.data
    }
  } catch (error) {
    console.error('加载状态失败:', error)
  }
}

async function loadPendingAssets() {
  try {
    const response = await assetApi.getList({
      watermark_status: 'embedded',
      chain_status: 'pending',
      per_page: 100
    })
    if (response.data.code === 200) {
      pendingAssets.value = response.data.data.items
      chainStatus.value.pendingAssets = pendingAssets.value.length
    }
  } catch (error) {
    console.error('加载待上链资产失败:', error)
  }
}

async function loadCertificates() {
  logsLoading.value = true
  try {
    const response = await blockchainApi.getHistory()
    if (response.data.code === 200) {
      certificates.value = response.data.data
      chainStatus.value.totalCertificates = certificates.value.length
    }
  } catch (error) {
    console.error('加载证书失败:', error)
  } finally {
    logsLoading.value = false
  }
}

function refreshAll() {
  loadStatus()
  loadPendingAssets()
  loadCertificates()
}

async function doBatchRegister() {
  if (batchRegister.value.assets.length === 0) {
    ElMessage.warning('请选择资产')
    return
  }

  batchRegister.value.loading = true
  let successCount = 0
  let failCount = 0

  for (const assetId of batchRegister.value.assets) {
    try {
      await blockchainApi.register(assetId)
      successCount++
    } catch {
      failCount++
    }
  }

  batchRegister.value.loading = false
  ElMessage.success(`批量上链完成，成功${successCount}个，失败${failCount}个`)
  batchRegister.value.assets = []
  loadPendingAssets()
  loadCertificates()
  loadStatus()
}

function viewCertificate(row) {
  router.push(`/certificate/${row.certificate_id}`)
}

async function verifyAsset(row) {
  try {
    const response = await blockchainApi.verify(row.asset_id)
    if (response.data.code === 200) {
      const verified = response.data.data.verified
      ElMessage.success(verified ? '验证通过，数据完整' : '验证失败，数据可能被篡改')
    }
  } catch (error) {
    ElMessage.error('验证失败')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadStatus()
  loadPendingAssets()
  loadCertificates()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-blockchain {
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

// ========== 状态台账 ==========
.chain-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-xl;
  margin-bottom: $spacing-xl;
}

.stat-tile {
  position: relative;
  padding: $spacing-xl;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;

  &::before {
    content: '';
    position: absolute;
    top: $spacing-xl;
    bottom: $spacing-xl;
    left: 0;
    width: 3px;
    background: $primary-color;
  }

  .stat-value {
    font-family: $font-display;
    font-size: 28px;
    font-weight: $font-weight-semibold;
    line-height: 1.15;
    color: $text-primary;
    font-variant-numeric: tabular-nums;

    &.is-text {
      font-size: 20px;
      line-height: 1.6;
    }

    &.is-ok {
      color: $success-color;
    }
  }

  .stat-label {
    margin-top: $spacing-xs;
    font-size: 13px;
    color: $text-secondary;
  }
}

// ========== 内容卡片 ==========
.content-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-xl;

  & + & {
    margin-top: $spacing-xl;
  }
}

.card-title {
  font-family: $font-display;
  font-size: 16px;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

// ========== 筛选行 ==========
.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-md;

  :deep(.el-form-item) {
    margin: 0;
  }

  :deep(.el-select) {
    width: 320px;
  }
}

// 按钮内图标与文字间距
:deep(.el-button > span) {
  gap: 6px;
  align-items: center;
}

// 台账编码与哈希使用等宽字体
:deep(.cell-code) {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

.hash {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  word-break: break-all;
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .admin-blockchain {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .chain-stats {
    grid-template-columns: 1fr;
    gap: $spacing-md;
  }

  .content-card {
    padding: 16px;
  }

  .filter-form {
    :deep(.el-form-item) {
      width: 100%;
    }

    :deep(.el-select) {
      width: 100%;
    }

    :deep(.el-button) {
      width: 100%;
    }
  }
}
</style>
